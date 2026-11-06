#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Recognition Module.
Defines the SignRecognizer protocol, invariant 106-D geometric feature extraction,
weighted k-NN classifier with unknown gesture rejection, and evaluation metrics.
"""
from typing import Protocol, Tuple, Optional, List, Dict, Any
from pathlib import Path
import json
import logging
import numpy as np

from slt.utils.paths import DEFAULT_MODEL_PATH

logger = logging.getLogger("slt.recognition")

class SignRecognizer(Protocol):
    """Protocol for SLT gesture and sign classifiers."""
    def predict(self, features: np.ndarray) -> Tuple[str, float, bool]:
        """Classify a 106-D feature vector -> (gloss, confidence, is_valid)."""
        ...
        
    def load(self, model_path: str) -> None:
        """Load weights and configuration."""
        ...

# 5 finger kinematic chains: [Wrist, CMC/MCP, PIP, DIP, TIP]
FINGER_CHAINS = [
    [0, 1, 2, 3, 4],     # Thumb
    [0, 5, 6, 7, 8],     # Index
    [0, 9, 10, 11, 12],  # Middle
    [0, 13, 14, 15, 16], # Ring
    [0, 17, 18, 19, 20]  # Pinky
]

FINGERTIP_INDICES = [4, 8, 12, 16, 20]
MCP_INDICES = [1, 5, 9, 13, 17]

def compute_angle(v1: np.ndarray, v2: np.ndarray) -> float:
    """Compute the angle in radians [0, pi] between two 3D vectors."""
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-7 or n2 < 1e-7:
        return 0.0
    cosine = np.dot(v1, v2) / (n1 * n2)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.arccos(cosine))

def extract_features(landmarks: np.ndarray) -> np.ndarray:
    """
    Extract exact 106-dimensional normalized geometric feature vector from 21 3D landmarks.
    
    Structure:
    - 63: Centered and scale-normalized 3D coordinates (21 x 3)
    - 15: Joint flexion angles (5 fingers x 3 joints)
    - 10: Pairwise Euclidean distances between all 5 finger tips (5 choose 2)
    -  5: Tip-to-wrist Euclidean distances
    -  3: Unit normal vector of the palm plane (wrist, index MCP, pinky MCP)
    - 10: Digital apertures (5 tips to MCP base, 5 tips to middle MCP landmark 9)
    Total: exactly 106 features. Invariant to translation, scale, and perspective.
    """
    pts = np.asarray(landmarks, dtype=np.float32)
    if pts.shape != (21, 3):
        raise ValueError(f"Expected landmarks of shape (21, 3), got {pts.shape}")

    # 1. Translation normalization: wrist at origin (0, 0, 0) in float64 for numerical precision
    pts_64 = pts.astype(np.float64)
    wrist = pts_64[0].copy()
    pts_centered = pts_64 - wrist

    # 2. Scale normalization: palm scale S = distance from wrist (0) to middle MCP (9)
    palm_scale = float(np.linalg.norm(pts_centered[9]))
    if palm_scale < 1e-5:
        palm_scale = 1.0

    pts_norm = (pts_centered / palm_scale).astype(np.float32)

    # Flattened coordinates: 21 * 3 = 63
    coords_flat = pts_norm.flatten()

    # 3. Joint Flexion Angles (15 angles)
    angles = []
    for chain in FINGER_CHAINS:
        for i in range(1, 4):
            p_prev = pts_norm[chain[i - 1]]
            p_curr = pts_norm[chain[i]]
            p_next = pts_norm[chain[i + 1]]
            v_in = p_curr - p_prev
            v_out = p_next - p_curr
            angles.append(compute_angle(v_in, v_out))

    # 4. Pairwise Fingertip Distances (10 distances)
    tip_pts = [pts_norm[i] for i in FINGERTIP_INDICES]
    inter_tip_dists = []
    for i in range(5):
        for j in range(i + 1, 5):
            inter_tip_dists.append(float(np.linalg.norm(tip_pts[i] - tip_pts[j])))

    # 5. Tip to Wrist Distances (5 distances)
    tip_wrist_dists = [float(np.linalg.norm(tp)) for tp in tip_pts]

    # 6. Palm Plane Unit Normal Vector (3 coordinates)
    v_idx = pts_norm[5]   # Wrist -> Index MCP
    v_pnk = pts_norm[17]  # Wrist -> Pinky MCP
    normal = np.cross(v_idx, v_pnk)
    norm_len = np.linalg.norm(normal)
    if norm_len > 1e-6:
        normal = normal / norm_len
    else:
        normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    # 7. Digital Apertures (10 distances)
    apertures = []
    for tip_idx, mcp_idx in zip(FINGERTIP_INDICES, MCP_INDICES):
        apertures.append(float(np.linalg.norm(pts_norm[tip_idx] - pts_norm[mcp_idx])))
    for tip_idx in FINGERTIP_INDICES:
        apertures.append(float(np.linalg.norm(pts_norm[tip_idx] - pts_norm[9])))

    # Concatenate all components
    feat_vector = np.concatenate([
        coords_flat,                 # 63
        np.array(angles, np.float32),            # 15
        np.array(inter_tip_dists, np.float32),   # 10
        np.array(tip_wrist_dists, np.float32),   #  5
        normal.astype(np.float32),               #  3
        np.array(apertures, np.float32)          # 10
    ])

    # Guard against NaN/Inf
    feat_vector = np.nan_to_num(feat_vector, nan=0.0, posinf=1.0, neginf=-1.0)
    return feat_vector.astype(np.float32)


class SLTClassifier:
    """
    Lightweight, deterministic, pure-NumPy classifier with unknown rejection.
    Supports distance-weighted k-NN matching.
    """
    def __init__(
        self,
        model_path: Optional[str] = None,
        k: int = 5,
        distance_threshold: float = 2.8,
        margin_threshold: float = 0.08
    ):
        self.model_path = Path(model_path or DEFAULT_MODEL_PATH)
        self.k = int(k)
        self.distance_threshold = float(distance_threshold)
        self.margin_threshold = float(margin_threshold)

        self.classes: List[str] = []
        self.X_train: np.ndarray = np.empty((0, 106), dtype=np.float32)
        self.y_train: np.ndarray = np.empty((0,), dtype=np.int64)
        self.mean: np.ndarray = np.zeros(106, dtype=np.float32)
        self.std: np.ndarray = np.ones(106, dtype=np.float32)
        self.X_norm: np.ndarray = np.empty((0, 106), dtype=np.float32)

        if self.model_path.is_file():
            self.load(str(self.model_path))
        else:
            logger.warning(f"Model path {self.model_path} not found.")

    def load(self, model_path: str):
        self.model_path = Path(model_path)
        data = np.load(self.model_path, allow_pickle=False)
        self.X_train = data["X_train"].astype(np.float32)
        self.y_train = data["y_train"].astype(np.int64)
        self.classes = [str(c) for c in data["classes"]]
        self.mean = data["mean"].astype(np.float32)
        self.std = data["std"].astype(np.float32)

        self.k = min(self.k, len(self.X_train))
        self.X_norm = (self.X_train - self.mean) / self.std
        logger.info(f"Loaded SLT model with {len(self.classes)} classes and {len(self.X_train)} training prototypes.")

    @property
    def feature_mean(self) -> np.ndarray:
        return self.mean.flatten()

    def predict(self, feature_vector: np.ndarray) -> Tuple[str, float, bool]:
        """
        Classifies a 106-D feature vector.
        Returns:
            (predicted_class, confidence_score, is_confident)
        """
        if len(self.classes) == 0 or len(self.X_norm) == 0:
            return "_NADA_", 0.0, False

        feats = np.asarray(feature_vector, dtype=np.float32).reshape(1, -1)
        feats_norm = (feats - self.mean) / self.std

        # 1. Compute Euclidean distances to all training points
        dists = np.linalg.norm(self.X_norm - feats_norm, axis=1)

        # 2. Get top-k nearest neighbors
        k_indices = np.argpartition(dists, self.k)[:self.k]
        k_dists = dists[k_indices]
        k_labels = self.y_train[k_indices]

        # 3. Distance-weighted voting (inverse distance weighting)
        weights = 1.0 / (k_dists + 1e-5)
        class_votes = np.zeros(len(self.classes), dtype=np.float32)
        for label, w in zip(k_labels, weights):
            class_votes[label] += w

        total_weight = np.sum(class_votes)
        if total_weight > 0:
            probs = class_votes / total_weight
        else:
            probs = np.zeros(len(self.classes), dtype=np.float32)
            probs[0] = 1.0

        top_indices = np.argsort(-probs)
        best_idx = int(top_indices[0])
        runner_up_idx = int(top_indices[1]) if len(top_indices) > 1 else best_idx

        best_prob = float(probs[best_idx])
        margin = float(best_prob - probs[runner_up_idx])
        min_dist = float(np.min(k_dists))

        # Rejection criteria:
        is_rejected = (min_dist > self.distance_threshold) or (margin < self.margin_threshold and best_prob < 0.6)

        predicted_class = self.classes[best_idx]
        confidence = float(np.clip(best_prob, 0.0, 1.0))

        if is_rejected or predicted_class == "_NADA_":
            return "_NADA_", confidence, False

        return predicted_class, confidence, True


def train_slt_model(
    X: np.ndarray,
    y: np.ndarray,
    classes: List[str],
    output_path: str,
    metadata_path: Optional[str] = None,
    groups: Optional[np.ndarray] = None
) -> dict:
    """Train and export SLT recognition model to slt_model.npz."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    X_arr = np.asarray(X, dtype=np.float32)
    y_arr = np.asarray(y, dtype=np.int64)

    mean = X_arr.mean(axis=0, keepdims=True).astype(np.float32)
    std = np.maximum(X_arr.std(axis=0, keepdims=True), 1e-4).astype(np.float32)
    classes_arr = np.array(classes, dtype="U32")

    np.savez_compressed(
        out_file,
        X_train=X_arr,
        y_train=y_arr,
        classes=classes_arr,
        mean=mean,
        std=std
    )

    metadata = {
        "model_name": "SLT Bilingual Core",
        "model_version": "1.0.0",
        "feature_extractor": "geometric_106",
        "feature_dimension": 106,
        "recognition_algorithm": "weighted_knn",
        "num_classes": len(classes),
        "supported_classes": list(classes),
        "training_samples": int(len(X_arr)),
        "groups_count": int(len(np.unique(groups))) if groups is not None else 1
    }

    if metadata_path is not None:
        meta_file = Path(metadata_path)
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        with meta_file.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata


def compute_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1
    return cm


def compute_metrics(cm: np.ndarray, classes: List[str]) -> dict:
    num_classes = len(classes)
    precisions, recalls, f1s = [], [], []

    for i in range(num_classes):
        tp = cm[i, i]
        fn = np.sum(cm[i, :]) - tp
        fp = np.sum(cm[:, i]) - tp

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

    return {
        "balanced_accuracy": float(np.mean(recalls)),
        "macro_precision": float(np.mean(precisions)),
        "macro_recall": float(np.mean(recalls)),
        "macro_f1": float(np.mean(f1s)),
        "per_class": {
            cls_name: {
                "precision": float(precisions[i]),
                "recall": float(recalls[i]),
                "f1": float(f1s[i]),
                "total_samples": int(np.sum(cm[i, :]))
            }
            for i, cls_name in enumerate(classes)
        }
    }
