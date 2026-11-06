"""Background camera and vision processing QThread worker."""
from __future__ import annotations
import time
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, Slot

from slt.vision.hand_detector import HandDetector
from slt.vision.drawing import draw_hand_landmarks
from slt.vision.landmark_extractor import extract_features
from slt.recognition.classifier import SLTClassifier
from slt.recognition.prediction_filter import PredictionFilter, FilterEvent
from slt.utils.paths import HAND_LANDMARKER_TASK, SLT_MODEL_PATH

class CameraWorker(QThread):
    # Signals emitted to UI
    frame_ready = Signal(object, object, str, float, float, float, float) # (frame, detections, sign, conf, stability, fps, latency)
    sign_confirmed = Signal(str)
    sign_released = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 1280,
        height: int = 720,
        confidence_threshold: float = 0.65
    ):
        super().__init__()
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.confidence_threshold = confidence_threshold

        self.running = True
        self.paused = False

    def run(self):
        backend = cv2.CAP_DSHOW
        cap = cv2.VideoCapture(self.camera_index, backend)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            self.error_occurred.emit(f"No se pudo acceder a la cámara {self.camera_index}.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        # Initialize detector and classifier inside the worker thread
        try:
            detector = HandDetector(HAND_LANDMARKER_TASK)
        except Exception as e:
            self.error_occurred.emit(f"Error al inicializar HandDetector: {e}")
            cap.release()
            return

        classifier = None
        if SLT_MODEL_PATH.is_file():
            try:
                classifier = SLTClassifier(SLT_MODEL_PATH, k=5)
            except Exception as e:
                print(f"[!] Warning: error al cargar SLTClassifier ({e})")

        pred_filter = PredictionFilter(window_size=8, minimum_votes=5, min_hold_frames=4, cooldown_sec=0.35)

        fps_frame_count = 0
        fps_start = time.perf_counter()
        current_fps = 0.0

        try:
            while self.running:
                t_frame_start = time.perf_counter()
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                frame = cv2.flip(frame, 1)

                current_sign = "_NADA_"
                confidence = 0.0
                stability = 0.0

                if not self.paused:
                    # 1. Detect hand landmarks
                    detections = detector.detect(frame)

                    # 2. Render skeleton overlays
                    for det in detections:
                        draw_hand_landmarks(frame, det.landmarks_image, det.handedness)

                    # 3. Classify dominant hand
                    if detections and classifier is not None:
                        # Prefer Right hand as dominant, or first hand
                        dom_det = next((d for d in detections if d.handedness == "Right"), detections[0])
                        feats = extract_features(dom_det.landmarks_world, handedness=dom_det.handedness, mirror_left=True)

                        pred_label, conf, is_conf = classifier.predict(feats)
                        confidence = conf
                        current_sign = pred_label if is_conf else "_NADA_"

                        event, confirmed_label, stab = pred_filter.update(current_sign, is_conf)
                        stability = stab

                        if event == FilterEvent.SIGN_CONFIRMED and confirmed_label:
                            self.sign_confirmed.emit(confirmed_label)
                        elif event == FilterEvent.SIGN_RELEASED:
                            self.sign_released.emit()
                    else:
                        event, _, stab = pred_filter.update(None, False)
                        stability = stab
                        if event == FilterEvent.SIGN_RELEASED:
                            self.sign_released.emit()
                else:
                    detections = []

                # Latency & FPS calculation
                t_frame_end = time.perf_counter()
                latency_ms = (t_frame_end - t_frame_start) * 1000.0

                fps_frame_count += 1
                if (t_frame_end - fps_start) >= 0.5:
                    current_fps = fps_frame_count / (t_frame_end - fps_start)
                    fps_frame_count = 0
                    fps_start = t_frame_end

                self.frame_ready.emit(
                    frame, detections, current_sign, confidence, stability, current_fps, latency_ms
                )

        finally:
            cap.release()
            detector.close()

    def set_paused(self, paused: bool):
        self.paused = paused

    def stop(self):
        self.running = False
        self.wait(3000)
