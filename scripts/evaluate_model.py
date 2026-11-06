"""Evaluate SLT model with full confusion matrix and latency benchmarks."""
import time
import json
import numpy as np

from slt.recognition import SLTClassifier, compute_confusion_matrix, compute_metrics
from slt.utils.paths import SLT_MODEL_PATH, MODEL_METADATA_PATH

def main():
    if not SLT_MODEL_PATH.is_file():
        raise FileNotFoundError(f"Modelo no encontrado: {SLT_MODEL_PATH}")

    data = np.load(SLT_MODEL_PATH, allow_pickle=False)
    X = data["X_train"]
    y = data["y_train"]
    classes = [str(c) for c in data["classes"]]

    classifier = SLTClassifier(SLT_MODEL_PATH, k=5)

    # 1. Latency benchmark
    print("[*] Midiendo latencia de inferencia del clasificador (1,000 repeticiones)...")
    sample_feat = X[0]
    t0 = time.perf_counter()
    for _ in range(1000):
        _ = classifier.predict(sample_feat)
    dt_ms = (time.perf_counter() - t0)

    print(f"[LATENCIA] {dt_ms:.4f} ms por muestra ({1000.0 / dt_ms:.0f} predicciones/segundo)")

    # 2. Confusion matrix on dataset
    y_pred = []
    for feat in X:
        pred_label, _, _ = classifier.predict(feat)
        pred_idx = classes.index(pred_label) if pred_label in classes else 0
        y_pred.append(pred_idx)

    cm = compute_confusion_matrix(y, y_pred, len(classes))
    metrics = compute_metrics(cm, classes)

    print("\n[RESULTADOS DE VALIDACIÓN DEL MODELO]")
    print(f"Clases soportadas:    {len(classes)}")
    print(f"Muestras evaluadas:   {len(X)}")
    print(f"Exactitud balanceada: {metrics['balanced_accuracy'] * 100:.2f}%")
    print(f"Macro F1-Score:       {metrics['macro_f1'] * 100:.2f}%")
    print(f"Macro Precisión:      {metrics['macro_precision'] * 100:.2f}%")
    print(f"Macro Recall:         {metrics['macro_recall'] * 100:.2f}%")

    print("\nDesglose por clase (Precisión / Recall / F1):")
    for cls_name, stat in metrics["per_class"].items():
        print(f"  {cls_name:<12}: P={stat['precision']*100:5.1f}% | R={stat['recall']*100:5.1f}% | F1={stat['f1']*100:5.1f}% (N={stat['total_samples']})")

if __name__ == "__main__":
    main()
