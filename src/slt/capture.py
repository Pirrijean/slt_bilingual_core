#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Camera and Video File Capture Module.
Handles video stream acquisition (live camera and local video files),
frame rate telemetry, and thread-safe QImage emission.
"""
import time
import logging
from pathlib import Path
from typing import Optional
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
            err_msg = f"No se pudo abrir el dispositivo de video {self.camera_index}"
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


class VideoFileWorker(QThread):
    """
    Asynchronous video file processing worker.
    Feeds frames from a local video file (MP4, AVI, MOV) through the exact same
    SLT recognition engine while tracking progress, speed, and timecodes.
    """
    frame_ready = Signal(np.ndarray, QImage, float)   # raw_bgr, qimg, video_time_sec
    progress_updated = Signal(int, int, float, float, float)  # frame_idx, total_frames, progress_pct, elapsed_sec, fps
    analysis_finished = Signal(int, float)            # total_frames, total_elapsed_sec
    error_occurred = Signal(str)

    def __init__(self, video_path: str, realtime_speed: bool = False, flip_horizontal: bool = False):
        super().__init__()
        self.video_path = str(video_path)
        self.realtime_speed = realtime_speed
        self.flip_horizontal = flip_horizontal
        self._running = False
        self._paused = False

    def run(self):
        self._running = True
        logger.info(f"Opening video file for analysis: {self.video_path}")

        path_obj = Path(self.video_path)
        if not path_obj.is_file():
            self.error_occurred.emit(f"El archivo no existe: {self.video_path}")
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.error_occurred.emit(f"No se pudo decodificar el archivo de video: {self.video_path}")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0:
            video_fps = 30.0

        frame_interval = 1.0 / video_fps
        current_frame = 0
        t_start = time.perf_counter()
        last_metric_time = t_start
        frames_since_metric = 0

        while self._running and current_frame < total_frames:
            if self._paused:
                time.sleep(0.05)
                continue

            t_frame_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            current_frame += 1
            frames_since_metric += 1

            if self.flip_horizontal:
                frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()

            # Video timestamp in seconds
            video_timestamp_sec = current_frame / video_fps
            self.frame_ready.emit(frame, qimg, video_timestamp_sec)

            # Telemetry progress
            now = time.perf_counter()
            if (now - last_metric_time) >= 0.15 or current_frame == total_frames:
                elapsed = now - t_start
                proc_fps = frames_since_metric / max(1e-5, (now - last_metric_time))
                progress_pct = (current_frame / max(1, total_frames)) * 100.0
                self.progress_updated.emit(current_frame, total_frames, progress_pct, elapsed, proc_fps)
                last_metric_time = now
                frames_since_metric = 0

            # Throttle if real-time preview playback is requested
            if self.realtime_speed:
                frame_elapsed = time.perf_counter() - t_frame_start
                delay = frame_interval - frame_elapsed
                if delay > 0.002:
                    time.sleep(delay)

        cap.release()
        total_elapsed = time.perf_counter() - t_start
        logger.info(f"Video analysis completed: {current_frame}/{total_frames} frames in {total_elapsed:.2f}s")
        self.analysis_finished.emit(current_frame, total_elapsed)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._running = False
        self.wait(2000)
