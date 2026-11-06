#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Camera Capture Module.
Handles video stream acquisition, frame rate telemetry, and thread-safe QImage emission.
"""
import time
import logging
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

logger = logging.getLogger("slt.capture")

class CameraWorker(QThread):
    """
    Asynchronous camera worker running on a dedicated QThread.
    Emits raw frames for processing and QImage for GUI rendering.
    """
    frame_ready = Signal(np.ndarray, QImage, float)  # raw_bgr, qimage, timestamp_ms
    metrics_updated = Signal(float, float)            # fps, capture_latency_ms
    error_occurred = Signal(str)

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        super().__init__()
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.target_fps = fps
        self._running = False
        self._cap = None

    def run(self):
        self._running = True
        logger.info(f"Opening camera index {self.camera_index}...")
        
        # Use CAP_DSHOW on Windows for fast startup if available
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self.camera_index)

        if not self._cap.isOpened():
            err_msg = f"Cannot open video device {self.camera_index}"
            logger.error(err_msg)
            self.error_occurred.emit(err_msg)
            return

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        last_time = time.perf_counter()
        fps_smoothing = 0.9
        smoothed_fps = float(self.target_fps)

        while self._running:
            start_capture = time.perf_counter()
            ret, frame = self._cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            capture_latency = (time.perf_counter() - start_capture) * 1000.0
            now = time.perf_counter()
            dt = now - last_time
            last_time = now
            if dt > 0:
                current_fps = 1.0 / dt
                smoothed_fps = fps_smoothing * smoothed_fps + (1.0 - fps_smoothing) * current_fps

            # Horizontal mirror for natural user interaction
            frame = cv2.flip(frame, 1)

            # Convert to QImage for immediate display
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

            timestamp_ms = time.time() * 1000.0
            self.frame_ready.emit(frame, qimg, timestamp_ms)
            self.metrics_updated.emit(smoothed_fps, capture_latency)

            # Throttle if needed to match target framerate
            elapsed = time.perf_counter() - start_capture
            delay = (1.0 / self.target_fps) - elapsed
            if delay > 0.001:
                time.sleep(delay)

        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info("Camera capture stopped.")

    def stop(self):
        """Request the capture thread to stop and wait for it."""
        self._running = False
        self.wait(2000)
