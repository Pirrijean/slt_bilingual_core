#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Communication Workspace Window.
The primary desktop application window bringing together perception, timeline,
bilingual translation, discreet diagnostics, and audio synthesis.
"""
import sys
import logging
import cv2
import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QComboBox
)
from PySide6.QtGui import QKeySequence, QImage, QShortcut
from PySide6.QtCore import Qt

from slt.capture import CameraWorker
from slt.perception import HandDetector, draw_hand_skeleton
from slt.recognition import extract_features, SLTClassifier
from slt.interaction import SLTInteractionEngine, SignEvent, InteractionState
from slt.language import BilingualTranslator, Lexicon
from slt.speech import SpeechWorker
from slt.ui.components import (
    PerceptionStage, SignTimelineWidget, LanguageOutputCard,
    DiagnosticsBar, SignGuideDrawer
)
from slt.ui.theme import COMMUNICATION_THEME

logger = logging.getLogger("slt.ui.main_window")

class MainWindow(QMainWindow):
    """
    SLT Bilingual Core · Communication Workspace
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLT Bilingual Core · Communication Workspace")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(COMMUNICATION_THEME)

        # 1. Initialize Subsystems
        self.lexicon = Lexicon()
        self.detector = HandDetector(num_hands=2)
        self.classifier = SLTClassifier()
        self.interaction = SLTInteractionEngine()
        self.translator = BilingualTranslator(self.lexicon)
        self.speech = SpeechWorker(mode="both")

        # 2. Build Interface Layout
        self._build_ui()

        # 3. Connect Signals
        self._connect_signals()

        # 4. Setup Shortcuts
        self._setup_shortcuts()

        # 5. Start Camera Capture
        self.camera_worker = CameraWorker(camera_index=0, width=640, height=480, fps=30)
        self.camera_worker.frame_ready.connect(self._on_frame_ready)
        self.camera_worker.metrics_updated.connect(self._on_camera_metrics)
        self.camera_worker.start()

        self._current_es = ""
        self._current_en = ""
        self._fps = 30.0
        self._latency = 0.0
        self._num_hands = 0

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # Header bar
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_title = QLabel("SLT BILINGUAL CORE")
        app_title.setObjectName("headerTitle")
        app_sub = QLabel("COMMUNICATION WORKSPACE · ES / EN")
        app_sub.setObjectName("headerSubtitle")
        title_box.addWidget(app_title)
        title_box.addWidget(app_sub)
        header.addLayout(title_box)
        header.addStretch()

        # Top voice selector
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["Voz: Español + English", "Voz: Sólo Español", "Voz: Only English"])
        self.voice_combo.currentIndexChanged.connect(self._on_voice_mode_changed)
        header.addWidget(self.voice_combo)

        # Toggle Guide Button
        self.guide_btn = QPushButton("Guía de Señas (F1)")
        self.guide_btn.setCheckable(True)
        self.guide_btn.setChecked(False)
        self.guide_btn.clicked.connect(self._toggle_guide)
        header.addWidget(self.guide_btn)

        main_layout.addLayout(header)

        # Body Horizontal Layout (Workspace + Optional Drawer)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        # Left Column: Perception Stage (Camera) + Sign Timeline
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        self.stage = PerceptionStage()
        left_col.addWidget(self.stage, stretch=4)

        self.timeline = SignTimelineWidget()
        left_col.addWidget(self.timeline, stretch=1)

        body_layout.addLayout(left_col, stretch=6)

        # Right Column: Subtitles Card + Interaction Action Buttons
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        self.subtitles = LanguageOutputCard()
        right_col.addWidget(self.subtitles, stretch=4)

        # Controls Toolbar
        controls_frame = QFrame()
        controls_frame.setObjectName("cardContainer")
        ctrl_layout = QVBoxLayout(controls_frame)
        ctrl_layout.setContentsMargins(14, 14, 14, 14)
        ctrl_layout.setSpacing(10)

        ctrl_title = QLabel("ACCIONES DE COMUNICACIÓN")
        ctrl_title.setObjectName("sectionTitle")
        ctrl_layout.addWidget(ctrl_title)

        self.speak_btn = QPushButton("Pronunciar Frase (Espacio)")
        self.speak_btn.setObjectName("primaryActionBtn")
        self.speak_btn.clicked.connect(self.speak_current_sentence)
        ctrl_layout.addWidget(self.speak_btn)

        row_actions = QHBoxLayout()
        self.undo_btn = QPushButton("Borrar Última Seña (Backspace)")
        self.undo_btn.clicked.connect(self.undo_last_sign)
        row_actions.addWidget(self.undo_btn)

        self.clear_btn = QPushButton("Limpiar Frase (Ctrl+L)")
        self.clear_btn.setObjectName("dangerActionBtn")
        self.clear_btn.clicked.connect(self.clear_sentence)
        row_actions.addWidget(self.clear_btn)
        ctrl_layout.addLayout(row_actions)

        right_col.addWidget(controls_frame, stretch=1)
        body_layout.addLayout(right_col, stretch=4)

        # Contextual Guide Drawer
        self.drawer = SignGuideDrawer(self.lexicon.words)
        self.drawer.setVisible(False)
        body_layout.addWidget(self.drawer)

        main_layout.addLayout(body_layout, stretch=1)

        # Footer: Cleanmeter-style Diagnostics Bar
        self.diagnostics = DiagnosticsBar()
        main_layout.addWidget(self.diagnostics)

    def _connect_signals(self):
        # Interaction Engine events
        self.interaction.sign_confirmed.connect(self._on_sign_confirmed)
        self.interaction.state_changed.connect(self._on_interaction_state_changed)
        self.interaction.candidate_progress.connect(self.stage.set_candidate_progress)
        self.interaction.timeline_updated.connect(self.timeline.set_events)
        self.timeline.event_deleted.connect(self._on_event_deleted)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Space), self, self.speak_current_sentence)
        QShortcut(QKeySequence(Qt.Key_Backspace), self, self.undo_last_sign)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_sentence)
        QShortcut(QKeySequence(Qt.Key_F1), self, self._toggle_guide)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    def _on_frame_ready(self, frame_bgr: np.ndarray, qimg: QImage, timestamp_ms: float):
        # 1. Perception
        perception = self.detector.detect(frame_bgr)
        self._num_hands = perception.num_hands
        self._latency = perception.inference_time_ms

        raw_pred = "_NADA_"
        confidence = 0.0
        is_valid = False
        handedness = "Right"

        # 2. Recognition on Primary Hand
        if perception.hands:
            primary_hand = perception.hands[0]
            handedness = primary_hand.handedness
            features = extract_features(primary_hand.landmarks_norm)
            raw_pred, confidence, is_valid = self.classifier.predict(features)

            # Draw visual landmarks on frame for perception stage
            annotated = draw_hand_skeleton(frame_bgr.copy(), primary_hand.landmarks_norm)
            if len(perception.hands) > 1:
                annotated = draw_hand_skeleton(annotated, perception.hands[1].landmarks_norm)

            # Convert annotated frame to QImage for stage
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            stage_qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            self.stage.set_frame(stage_qimg)
        else:
            self.stage.set_frame(qimg)

        # 3. Interaction Engine State Machine
        state = self.interaction.process_frame(
            has_hands=bool(perception.hands),
            raw_prediction=raw_pred,
            confidence=confidence,
            is_valid=is_valid,
            handedness=handedness
        )

        self.stage.update_interaction_state(state, raw_pred, confidence)
        self.diagnostics.update_metrics(self._fps, self._latency, self._num_hands)

    def _on_camera_metrics(self, fps: float, latency_ms: float):
        self._fps = fps

    def _on_sign_confirmed(self, event: SignEvent):
        # Update Language Engine
        es_text, en_text = self.translator.add_gloss(event.label)
        self._current_es = es_text
        self._current_en = en_text
        self.subtitles.set_translations(es_text, en_text)

    def _on_interaction_state_changed(self, state: InteractionState):
        logger.debug(f"Interaction state: {state.value}")

    def _on_event_deleted(self, event_id: str):
        self.interaction.remove_event(event_id)
        # Rebuild translation from remaining timeline events
        remaining_glosses = [ev.label for ev in self.interaction.get_timeline()]
        self.translator.gloss_buffer = list(remaining_glosses)
        es_text, en_text = self.translator.translate()
        self._current_es = es_text
        self._current_en = en_text
        self.subtitles.set_translations(es_text, en_text)

    def speak_current_sentence(self):
        if self._current_es or self._current_en:
            self.speech.speak(self._current_es, self._current_en)

    def undo_last_sign(self):
        self.interaction.remove_last_event()
        es_text, en_text = self.translator.remove_last_gloss()
        self._current_es = es_text
        self._current_en = en_text
        self.subtitles.set_translations(es_text, en_text)

    def clear_sentence(self):
        self.interaction.clear_timeline()
        self.translator.clear()
        self._current_es = ""
        self._current_en = ""
        self.subtitles.set_translations("", "")

    def _toggle_guide(self):
        is_visible = self.drawer.isVisible()
        self.drawer.setVisible(not is_visible)
        self.guide_btn.setChecked(not is_visible)

    def _on_voice_mode_changed(self, index: int):
        modes = ["both", "es", "en"]
        if index < len(modes):
            self.speech.set_mode(modes[index])

    def closeEvent(self, event):
        if hasattr(self, "camera_worker"):
            self.camera_worker.stop()
        if hasattr(self, "speech"):
            self.speech.stop()
        if hasattr(self, "detector"):
            self.detector.close()
        event.accept()
