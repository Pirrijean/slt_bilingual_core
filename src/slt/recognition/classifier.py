"""SLT Recognition Classifier and unknown gesture rejection."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

class SLTClassifier:
    """
    Lightweight, deterministic, pure-NumPy classifier with unknown rejection.
    Supports distance-weighted k-NN and prototype centroid matching.
    """
    def __init__(self, model_path: str | Path, k: int = 5, distance_threshold: float = 2.8, margin_threshold: float = 0.08):
        self.path = Path(model_path)
        if not self.path.is_file():
            raise FileNotFoundError(f"No se encontró el modelo: {self.path}")

        data = np.load(self.path, allow_pickle=False)
        self.X_train = data["X_train"].astype(np.float32)
        self.y_train = data["y_train"].astype(np.int64)
        self.classes = [str(c) for c in data["classes"]]
        self.mean = data["mean"].astype(np.float32)
        self.std = data["std"].astype(np.float32)

        self.k = min(int(k), len(self.X_train))
        self.distance_threshold = float(distance_threshold)
        self.margin_threshold = float(margin_threshold)

        # Precompute per-class prototype centroids in normalized space
        self.X_norm = (self.X_train - self.mean) / self.std
        num_classes = len(self.classes)
        self.centroids = np.zeros((num_classes, self.X_norm.shape[1]), dtype=np.float32)
        for c_idx in range(num_classes):
            mask = (self.y_train == c_idx)
            if np.any(mask):
                self.centroids[c_idx] = self.X_norm[mask].mean(axis=0)

    def predict(self, feature_vector: np.ndarray) -> tuple[str, float, bool]:
        """
        Classifies a 106-D feature vector.
        Returns:
            (predicted_class, confidence_score, is_confident)
            If confidence is below rejection threshold, predicted_class may be '_NADA_'.
        """
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
        # - Nearest neighbor is too far away
        # - Margin between top 2 classes is too thin
        # - Predicted class is _NADA_
        is_rejected = (min_dist > self.distance_threshold) or (margin < self.margin_threshold and best_prob < 0.6)

        predicted_class = self.classes[best_idx]
        confidence = float(np.clip(best_prob, 0.0, 1.0))

        if is_rejected:
            return "_NADA_", confidence, False

        return predicted_class, confidence, True
