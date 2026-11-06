"""Evaluation metrics: confusion matrix, balanced accuracy, macro F1."""
from __future__ import annotations
import numpy as np

def compute_confusion_matrix(y_true: list[int] | np.ndarray, y_pred: list[int] | np.ndarray, num_classes: int) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1
    return cm

def compute_metrics(cm: np.ndarray, classes: list[str]) -> dict:
    """Computes balanced accuracy, macro precision, recall and F1 from a confusion matrix."""
    num_classes = len(classes)
    precisions = []
    recalls = []
    f1s = []

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

    balanced_acc = float(np.mean(recalls))
    macro_prec = float(np.mean(precisions))
    macro_rec = float(np.mean(recalls))
    macro_f1 = float(np.mean(f1s))

    return {
        "balanced_accuracy": balanced_acc,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "macro_f1": macro_f1,
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
