#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: UI Components Module.
Implements the Perception Stage, Sign Timeline, Bilingual Subtitles, Cleanmeter Diagnostics, and Guide Drawer.
"""
from typing import List, Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QSizePolicy, QProgressBar
)
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PySide6.QtCore import Qt, Signal, QSize

from slt.interaction import SignEvent, InteractionState
from slt.ui.theme import GRAPHITE, SLATE, SLATE_LIGHT, TEAL, MIST, MUTED, AMBER, EMERALD, CRIMSON

class PerceptionStage(QFrame):
    """
    Primary video viewport displaying mirrored camera frames,
    anatomical landmarks overlay, and real-time interaction HUD.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("stageContainer")
        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._pixmap: Optional[QPixmap] = None
        self._status_text = "READY"
        self._status_color = TEAL
        self._current_gloss = ""
        self._confidence = 0.0
        self._candidate_gloss = ""
        self._candidate_progress = 0.0

    def set_frame(self, qimg: QImage):
        """Update viewport pixmap with new frame."""
        self._pixmap = QPixmap.fromImage(qimg)
        self.update()

    def update_interaction_state(self, state: InteractionState, gloss: str = "", conf: float = 0.0):
        self._current_gloss = gloss
        self._confidence = conf
        if state == InteractionState.IDLE:
            self._status_text = "IDLE · NO HAND DETECTED"
            self._status_color = MUTED
        elif state == InteractionState.TRACKING:
            self._status_text = "TRACKING · READY FOR SIGN"
            self._status_color = TEAL
        elif state == InteractionState.CANDIDATE:
            self._status_text = f"ANALYZING · {gloss}"
            self._status_color = AMBER
        elif state == InteractionState.CONFIRMED:
            self._status_text = f"CONFIRMED · {gloss}"
            self._status_color = EMERALD
        elif state == InteractionState.WAITING_RELEASE:
            self._status_text = "HOLD COMPLETED · RELEASE SIGN"
            self._status_color = TEAL
        self.update()

    def set_candidate_progress(self, gloss: str, progress: float):
        self._candidate_gloss = gloss
        self._candidate_progress = progress
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(GRAPHITE))

        # Scaled video frame
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.setPen(QColor(MUTED))
            painter.drawText(self.rect(), Qt.AlignCenter, "Iniciando cámara / Initializing camera...")

        # HUD Top-Left Pill: Live Status
        pill_rect = QFrame()
        painter.setBrush(QColor(16, 24, 32, 210))
        painter.setPen(QColor(self._status_color))
        painter.drawRoundedRect(16, 16, 210, 32, 6, 6)

        painter.setBrush(QColor(self._status_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(28, 28, 8, 8)

        painter.setPen(QColor(MIST))
        font = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(44, 36, self._status_text)

        # HUD Top-Right Pill: Active Sign & Confidence
        if self._current_gloss and self._current_gloss != "_NADA_":
            sign_text = f"{self._current_gloss} ({int(self._confidence * 100)}%)"
            painter.setBrush(QColor(16, 24, 32, 220))
            painter.setPen(QColor(TEAL))
            painter.drawRoundedRect(self.width() - 200, 16, 184, 32, 6, 6)

            painter.setPen(QColor(TEAL))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(self.width() - 190, 37, sign_text)

        # Bottom Candidate Progress Bar (Quorum Accumulation)
        if self._candidate_progress > 0.05:
            bar_w = int((self.width() - 64) * self._candidate_progress)
            painter.setBrush(QColor(16, 24, 32, 180))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(32, self.height() - 24, self.width() - 64, 8, 4, 4)

            painter.setBrush(QColor(TEAL))
            painter.drawRoundedRect(32, self.height() - 24, bar_w, 8, 4, 4)


class SignTimelineWidget(QFrame):
    """
    Interactive horizontal ribbon displaying the sequence of confirmed SignEvents.
    Users can inspect duration, timestamps, and click chips to remove false detections.
    """
    event_deleted = Signal(str)  # event_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timelineContainer")
        self.setFixedHeight(72)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(10)

        # Label title
        self._title = QLabel("SIGN TIMELINE")
        self._title.setObjectName("sectionTitle")
        self._title.setFixedWidth(100)
        self._layout.addWidget(self._title)

        # Scroll Area for chips
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background: transparent; border: none;")

        self._chips_container = QWidget()
        self._chips_container.setStyleSheet("background: transparent;")
        self._chips_layout = QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(8)
        self._chips_layout.addStretch()

        self._scroll.setWidget(self._chips_container)
        self._layout.addWidget(self._scroll)

    def set_events(self, events: List[SignEvent]):
        """Re-render timeline chips."""
        # Clear existing chips except stretch
        while self._chips_layout.count() > 1:
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx, ev in enumerate(events):
            chip_btn = QPushButton(f"{ev.label}  ·  {ev.duration_seconds:.1f}s  ✕")
            chip_btn.setObjectName("timelineChip")
            chip_btn.setToolTip(f"Reconocido a las {ev.formatted_time}. Clic para eliminar.")
            # Closure capture
            chip_btn.clicked.connect(lambda _, eid=ev.event_id: self.event_deleted.emit(eid))
            self._chips_layout.insertWidget(self._chips_layout.count() - 1, chip_btn)


class LanguageOutputCard(QFrame):
    """
    High-contrast bilingual presentation card displaying
    real-time Spanish and English translations.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Spanish section
        es_header = QHBoxLayout()
        es_tag = QLabel("ESPAÑOL")
        es_tag.setObjectName("subtitleLangTag")
        es_header.addWidget(es_tag)
        es_header.addStretch()
        layout.addLayout(es_header)

        self.es_label = QLabel("Realiza señas frente a la cámara para comenzar...")
        self.es_label.setObjectName("subtitleText")
        self.es_label.setWordWrap(True)
        layout.addWidget(self.es_label)

        # Subtle divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background-color: {SLATE_LIGHT}; max-height: 1px;")
        layout.addWidget(divider)

        # English section
        en_header = QHBoxLayout()
        en_tag = QLabel("ENGLISH")
        en_tag.setObjectName("subtitleLangTag")
        en_header.addWidget(en_tag)
        en_header.addStretch()
        layout.addLayout(en_header)

        self.en_label = QLabel("Perform signs in front of camera to begin...")
        self.en_label.setObjectName("subtitleText")
        self.en_label.setWordWrap(True)
        layout.addWidget(self.en_label)

    def set_translations(self, es_text: str, en_text: str):
        self.es_label.setText(es_text.strip() or "...")
        self.en_label.setText(en_text.strip() or "...")


class DiagnosticsBar(QFrame):
    """
    Discreet single-line system monitor inspired by Cleanmeter.
    Presents performance metrics without visual clutter.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("diagnosticsBar")
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        self.cam_label = QLabel("CAM 01")
        self.cam_label.setObjectName("telemetryText")
        layout.addWidget(self.cam_label)

        self.fps_label = QLabel("30.0 FPS")
        self.fps_label.setObjectName("telemetryText")
        layout.addWidget(self.fps_label)

        self.latency_label = QLabel("0.0 ms")
        self.latency_label.setObjectName("telemetryText")
        layout.addWidget(self.latency_label)

        self.hands_label = QLabel("0 HANDS")
        self.hands_label.setObjectName("telemetryText")
        layout.addWidget(self.hands_label)

        layout.addStretch()

        self.model_label = QLabel("MODEL: SLT-v1.0.0 (92.5%)")
        self.model_label.setObjectName("telemetryText")
        layout.addWidget(self.model_label)

        self.status_label = QLabel("ENGINE: READY")
        self.status_label.setObjectName("telemetryText")
        self.status_label.setStyleSheet(f"color: {TEAL}; font-weight: bold;")
        layout.addWidget(self.status_label)

    def update_metrics(self, fps: float, latency_ms: float, num_hands: int):
        self.fps_label.setText(f"{fps:.1f} FPS")
        self.latency_label.setText(f"{latency_ms:.1f} ms")
        self.hands_label.setText(f"{num_hands} {'HAND' if num_hands == 1 else 'HANDS'}")


class SignGuideDrawer(QFrame):
    """
    Collapsible contextual drawer showing visual sign catalog (Level 2 Assistance).
    """
    def __init__(self, words_dict: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("drawerContainer")
        self.setFixedWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("VOCABULARIO / VOCABULARY")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(8)

        for gloss, entry in words_dict.items():
            card = QFrame()
            card.setStyleSheet(f"background-color: {SLATE_LIGHT}; border-radius: 6px; padding: 6px;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 6, 8, 6)
            card_layout.setSpacing(2)

            g_lbl = QLabel(f"<b>{gloss}</b> <span style='color:{TEAL};'>({entry.get('category', 'Seña')})</span>")
            guide_lbl = QLabel(entry.get("guide", ""))
            guide_lbl.setWordWrap(True)
            guide_lbl.setStyleSheet(f"color: {MUTED}; font-size: 11px;")

            card_layout.addWidget(g_lbl)
            card_layout.addWidget(guide_lbl)
            c_layout.addWidget(card)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
