#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Vision Worker Thread.
Coordinates video capture (Camera / Video File), MediaPipe HandLandmarker,
visual overlay rendering (Mode A / Mode B), and recognition backend processing.
"""
from typing import Optional, List, Dict, Any
import time
import logging
import cv2
import numpy as np

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from slt_desktop.hand_landmarker import SLTHandLandmarker, HandObservation
from slt_desktop.drawing import draw_hand_landmarks
from slt_desktop.recognition_adapter import RecognitionBackend, build_recognition_backend

logger = logging.getLogger("slt_desktop.vision_worker")


class VisionWorker(QThread):
    """
    Asynchronous vision pipeline thread.
    Operates in two modes:
    - Camera Mode: Live streaming from webcam (cv2.VideoCapture(index)).
    - Video File Mode: Offline processing of video files with exact timecodes.
    """
    frame_ready = Signal(QImage)
    signs_confirmed = Signal(list)                   # List of sign event dicts
    metrics_updated = Signal(float, float, int)      # (fps, latency_ms, num_hands)
    video_progress = Signal(float, float, float, int) # (progress_ratio, proc_fps, eta_sec, hands)
    video_finished = Signal(list)                    # All events from video
    error_occurred = Signal(str)

    def __init__(
        self,
        camera_index: int = 0,
        video_path: Optional[str] = None,
        recognition_backend: Optional[RecognitionBackend] = None,
        show_landmarks: bool = False
    ):
        super().__init__()
        self.camera_index = camera_index
        self.video_path = video_path
        self.is_video_mode = bool(video_path)
        self.backend = recognition_backend or build_recognition_backend()
        self.show_landmarks = bool(show_landmarks)

        self._running = False
        self._cap: Optional[cv2.VideoCapture] = None
        self._landmarker: Optional[SLTHandLandmarker] = None
        self._all_video_events: List[Dict[str, Any]] = []

    def set_show_landmarks(self, enabled: bool):
        """Toggle anatomical overlay (Mode A: Clean vs Mode B: Demonstration)."""
        self.show_landmarks = bool(enabled)

    def stop(self):
        """Signal thread to stop execution and release capture device."""
        self._running = False
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass

    def run(self):
        self._running = True
        self._all_video_events.clear()
        self.backend.reset()

        try:
            self._landmarker = SLTHandLandmarker(num_hands=2, min_confidence=0.5)
        except Exception as e:
            logger.error(f"Failed to initialize SLTHandLandmarker: {e}")
            self.error_occurred.emit(f"No se pudo cargar el modelo de visión: {e}")
            return

        if self.is_video_mode:
            self._run_video_file()
        else:
            self._run_camera()

        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def _run_camera(self):
        """Live camera capture loop."""
        cap = cv2.VideoCapture(self.camera_index)
        self._cap = cap
        if not cap.isOpened():
            logger.error(f"Cannot open camera index {self.camera_index}")
            self.error_occurred.emit(f"No se pudo acceder a la cámara {self.camera_index}.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        fps_calc_time = time.perf_counter()
        frame_counter = 0
        current_fps = 30.0
        last_ts_ms = -1

        try:
            while self._running:
                ret, frame_bgr = cap.read()
                if not ret or frame_bgr is None:
                    time.sleep(0.01)
                    continue

                t0 = time.perf_counter()
                ts_ms = int(time.time() * 1000)
                if ts_ms <= last_ts_ms:
                    ts_ms = last_ts_ms + 1
                last_ts_ms = ts_ms

                # 1. Perception
                observations = self._landmarker.detect(frame_bgr, ts_ms)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                num_hands = len(observations)

                # 2. Recognition
                confirmed = self.backend.process(observations, ts_ms)
                if confirmed:
                    self.signs_confirmed.emit(confirmed)

                # 3. Visualization Mode
                # Mode A: Clean camera screen (default, show_landmarks=False)
                # Mode B: Demonstration mode with skeletons (show_landmarks=True)
                if self.show_landmarks and observations:
                    display_frame = draw_hand_landmarks(frame_bgr, observations)
                else:
                    display_frame = frame_bgr

                # 4. Render to QImage
                q_img = self._bgr_to_qimage(display_frame)
                self.frame_ready.emit(q_img)

                # 5. Metrics
                frame_counter += 1
                elapsed = time.perf_counter() - fps_calc_time
                if elapsed >= 0.5:
                    current_fps = frame_counter / elapsed
                    frame_counter = 0
                    fps_calc_time = time.perf_counter()
                    self.metrics_updated.emit(current_fps, latency_ms, num_hands)

        finally:
            cap.release()

    def _run_video_file(self):
        """Offline video file processing loop."""
        if not self.video_path:
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video file: {self.video_path}")
            self.error_occurred.emit(f"No se pudo abrir el archivo de video: {self.video_path}")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        native_fps = cap.get(cv2.CAP_PROP_FPS)
        if native_fps <= 0 or np.isnan(native_fps):
            native_fps = 30.0

        total_duration_sec = total_frames / native_fps if total_frames > 0 else 1.0

        frame_idx = 0
        proc_start_time = time.perf_counter()
        last_ts_ms = -1

        try:
            while self._running:
                ret, frame_bgr = cap.read()
                if not ret or frame_bgr is None:
                    break  # End of video

                t0 = time.perf_counter()
                ts_ms = int(round((frame_idx / native_fps) * 1000.0))
                if ts_ms <= last_ts_ms:
                    ts_ms = last_ts_ms + 1
                last_ts_ms = ts_ms

                # 1. Perception
                observations = self._landmarker.detect(frame_bgr, ts_ms)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                num_hands = len(observations)

                # 2. Recognition
                confirmed = self.backend.process(observations, ts_ms)
                if confirmed:
                    self._all_video_events.extend(confirmed)
                    self.signs_confirmed.emit(confirmed)

                # 3. Visualization
                if self.show_landmarks and observations:
                    display_frame = draw_hand_landmarks(frame_bgr, observations)
                else:
                    display_frame = frame_bgr

                q_img = self._bgr_to_qimage(display_frame)
                self.frame_ready.emit(q_img)

                # 4. Progress and ETA calculation
                frame_idx += 1
                proc_elapsed = time.perf_counter() - proc_start_time
                proc_fps = frame_idx / proc_elapsed if proc_elapsed > 0 else 30.0
                progress_ratio = min(1.0, frame_idx / float(max(1, total_frames)))
                remaining_frames = max(0, total_frames - frame_idx)
                eta_seconds = remaining_frames / proc_fps if proc_fps > 0 else 0.0

                self.video_progress.emit(progress_ratio, proc_fps, eta_seconds, num_hands)
                self.metrics_updated.emit(proc_fps, latency_ms, num_hands)

            # Emitted only if video finished completely without cancellation
            if self._running and frame_idx >= total_frames:
                self.video_finished.emit(list(self._all_video_events))

        finally:
            cap.release()

    @staticmethod
    def _bgr_to_qimage(frame_bgr: np.ndarray) -> QImage:
        """Convert BGR OpenCV image to RGB QImage."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        # QImage must copy the data buffer to avoid garbage collection issues
        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        return q_img
