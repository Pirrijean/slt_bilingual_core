"""Model trainer and exporter for SLT."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

def train_slt_model(
    X: np.ndarray,
    y: np.ndarray,
    classes: list[str],
    output_path: str | Path,
    metadata_path: str | Path | None = None,
    groups: np.ndarray | None = None
) -> dict:
    """
    Trains and packages the SLT recognition model to slt_model.npz.
    Saves mean, std, X_train, y_train, classes (U32 for allow_pickle=False compatibility), and metadata.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    X_arr = np.asarray(X, dtype=np.float32)
    y_arr = np.asarray(y, dtype=np.int64)

    if X_arr.ndim != 2 or X_arr.shape[1] != 106:
        raise ValueError(f"X debe tener dimensiones (N, 106), se recibió {X_arr.shape}")
    if len(X_arr) != len(y_arr):
        raise ValueError("X e y deben tener la misma cantidad de muestras.")

    mean = X_arr.mean(axis=0, keepdims=True).astype(np.float32)
    std = np.maximum(X_arr.std(axis=0, keepdims=True), 1e-4).astype(np.float32)

    # Use fixed-width Unicode string array so allow_pickle=False works smoothly
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
