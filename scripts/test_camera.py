"""Camera test script with MediaPipe HandLandmarker."""
import cv2
import time
from pathlib import Path
from slt.vision.hand_detector import HandDetector
from slt.vision.drawing import draw_hand_landmarks
from slt.vision.landmark_extractor import extract_features
from slt.utils.paths import HAND_LANDMARKER_TASK

def main():
    if not HAND_LANDMARKER_TASK.is_file():
        raise FileNotFoundError(f"No se encontró el modelo: {HAND_LANDMARKER_TASK}")

    detector = HandDetector(HAND_LANDMARKER_TASK)
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        raise RuntimeError("No se pudo abrir la cámara.")

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("[*] Cámara iniciada. Presiona 'q' para salir.")
    try:
        frame_count = 0
        start_time = time.time()
        while True:
            ret, frame = camera.read()
            if not ret:
                print("[!] No se pudo leer el fotograma.")
                break

            frame = cv2.flip(frame, 1)
            detections = detector.detect(frame)
            frame_count += 1

            for det in detections:
                draw_hand_landmarks(frame, det.landmarks_image, det.handedness)
                feats = extract_features(det.landmarks_world, det.handedness)

            fps = frame_count / max(time.time() - start_time, 1e-5)
            cv2.putText(frame, f"Manos: {len(detections)} | FPS: {fps:.1f}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 240, 160), 2)

            cv2.imshow("SLT Camera Test", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.release()
        detector.close()
        cv2.destroyAllWindows()
        print("[OK] Cámara y detector cerrados limpiamente.")

if __name__ == "__main__":
    main()
