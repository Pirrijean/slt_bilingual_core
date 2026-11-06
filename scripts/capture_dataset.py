"""Dataset capture tool for recording real labeled sign video clips."""
import time
import json
from pathlib import Path
import cv2

from slt.vision.hand_detector import HandDetector
from slt.vision.drawing import draw_hand_landmarks
from slt.vision.landmark_extractor import extract_features
from slt.utils.paths import HAND_LANDMARKER_TASK, DATA_DIR, CLASSES_PATH

def main():
    with open(CLASSES_PATH, "r", encoding="utf-8") as f:
        classes = json.load(f)["classes"]

    detector = HandDetector(HAND_LANDMARKER_TASK)
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera = cv2.VideoCapture(0)

    print("=== SLT DATASET RECORDER ===")
    print("Clases disponibles:", ", ".join(classes))
    target_class = input("Ingresa la seña a grabar (ej: HOLA): ").strip().upper()
    if target_class not in classes:
        print(f"[!] '{target_class}' no está en classes.json. Creando carpeta de todos modos...")

    participant = input("ID de participante (ej: P01): ").strip().upper() or "P01"
    save_dir = DATA_DIR / "raw" / participant / target_class
    save_dir.mkdir(parents=True, exist_ok=True)

    clip_count = len(list(save_dir.glob("*.npz")))
    print(f"[*] Guardando en: {save_dir} (Clips actuales: {clip_count})")
    print("Controles: [ESPACIO] Iniciar clip de 2 segundos | [Q] Salir")

    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            detections = detector.detect(frame)

            for det in detections:
                draw_hand_landmarks(frame, det.landmarks_image, det.handedness)

            cv2.putText(frame, f"Clase: {target_class} | Clips: {clip_count}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 240, 160), 2)
            cv2.putText(frame, "ESPACIO: Grabar | Q: Salir", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            cv2.imshow("SLT Capture Dataset", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 32:  # Spacebar -> record 2 seconds
                clip_landmarks = []
                t_start = time.time()
                while time.time() - t_start < 2.0:
                    r, f = camera.read()
                    if not r:
                        break
                    f = cv2.flip(f, 1)
                    dets = detector.detect(f)
                    if dets:
                        draw_hand_landmarks(f, dets[0].landmarks_image, dets[0].handedness)
                        clip_landmarks.append(dets[0].landmarks_world)

                    progress = (time.time() - t_start) / 2.0
                    bar_w = int(f.shape[1] * progress)
                    cv2.rectangle(f, (0, f.shape[0] - 15), (bar_w, f.shape[0]), (0, 0, 255), -1)
                    cv2.putText(f, f"GRABANDO {target_class}...", (20, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                    cv2.imshow("SLT Capture Dataset", f)
                    cv2.waitKey(1)

                if len(clip_landmarks) >= 10:
                    clip_count += 1
                    clip_file = save_dir / f"clip_{clip_count:03d}.npz"
                    import numpy as np
                    np.savez_compressed(clip_file, landmarks=np.array(clip_landmarks, dtype=np.float32), label=target_class, participant=participant)
                    print(f"[OK] Guardado {clip_file.name} ({len(clip_landmarks)} frames)")
                else:
                    print("[!] No se detectó la mano consistentemente. Clip descartado.")
    finally:
        camera.release()
        detector.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
