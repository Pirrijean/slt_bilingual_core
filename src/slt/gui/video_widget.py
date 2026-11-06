"""Video display widget with real-time HUD overlays."""
from __future__ import annotations
import cv2
import numpy as np
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt

class VideoWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardPanel")
        self.setMinimumSize(640, 420)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Top telemetry bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.live_badge = QLabel("● EN VIVO")
        self.live_badge.setObjectName("liveBadge")
        top_bar.addWidget(self.live_badge)

        self.fps_label = QLabel("FPS: --")
        self.fps_label.setObjectName("telemetryPill")
        top_bar.addWidget(self.fps_label)

        self.latency_label = QLabel("Latencia: -- ms")
        self.latency_label.setObjectName("telemetryPill")
        top_bar.addWidget(self.latency_label)

        self.hands_label = QLabel("Manos: 0")
        self.hands_label.setObjectName("telemetryPill")
        top_bar.addWidget(self.hands_label)

        top_bar.addStretch()

        self.sign_badge = QLabel("Seña: (esperando)")
        self.sign_badge.setObjectName("telemetryPill")
        self.sign_badge.setStyleSheet("color: #38d9a9; font-weight: 700;")
        top_bar.addWidget(self.sign_badge)

        main_layout.addLayout(top_bar)

        # Video canvas label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #0b1016; border-radius: 8px;")
        self.image_label.setMinimumSize(600, 360)
        main_layout.addWidget(self.image_label, stretch=1)

    def update_frame(
        self,
        frame_bgr: np.ndarray,
        detections: list,
        current_sign: str,
        confidence: float,
        stability: float,
        fps: float,
        latency_ms: float
    ):
        """Render new video frame with updated telemetry."""
        h, w, ch = frame_bgr.shape
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        bytes_per_line = ch * w

        q_img = QImage(
            rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
        )
        pixmap = QPixmap.fromImage(q_img)

        # Scale preserving aspect ratio smoothly
        target_size = self.image_label.size()
        scaled = pixmap.scaled(
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

        # Update telemetry pills
        self.fps_label.setText(f"FPS: {fps:4.1f}")
        self.latency_label.setText(f"Latencia: {latency_ms:4.1f} ms")
        self.hands_label.setText(f"Manos: {len(detections)}")

        if current_sign and current_sign != "_NADA_":
            self.sign_badge.setText(f"Seña: {current_sign} ({confidence * 100:.0f}%)")
        else:
            self.sign_badge.setText("Seña: reposo / _NADA_")

    def set_paused_status(self, is_paused: bool):
        if is_paused:
            self.live_badge.setText("⏸ PAUSADO")
            self.live_badge.setStyleSheet("background-color: rgba(251, 191, 36, 0.15); border: 1px solid #fbbf24; color: #fbbf24;")
        else:
            self.live_badge.setText("● EN VIVO")
            self.live_badge.setStyleSheet("")
