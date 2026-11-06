#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Communication Workspace Window.
The primary desktop application window bringing together perception, timeline,
bilingual translation, discreet diagnostics, video analysis, and audio synthesis.
"""
import sys
import logging
import cv2
import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QComboBox, QTabWidget,
    QStackedLayout
)
from PySide6.QtGui import QKeySequence, QImage, QShortcut
from PySide6.QtCore import Qt

from slt.capture import CameraWorker, VideoFileWorker
from slt.perception import HandDetector, draw_hand_skeleton
from slt.recognition import extract_features, SLTClassifier
from slt.interaction import SLTInteractionEngine, SignEvent, InteractionState
from slt.language import BilingualTranslator, Lexicon
from slt.speech import SpeechWorker
from slt.ui.components import (
    PerceptionStage, SignTimelineWidget, LanguageOutputCard,
    DiagnosticsBar, SignGuideDrawer, VideoAnalysisWidget
)
from slt.ui.theme import COMMUNICATION_THEME, TEAL, MIST, MUTED, GRAPHITE, SLATE, SLATE_LIGHT

logger = logging.getLogger("slt.ui.main_window")

class MainWindow(QMainWindow):
    """
    SLT Bilingual Core · Communication Workspace
    Integrates the 4 pillars:
    1. Real-time visual interaction & recognition (Clean screen by default, optional demo overlays).
    2. Bilingual translation & subtitles (Live subtitles & Video file analysis with SRT export).
    3. Speech synthesis communication controls (Spanish, English, Both, Auto-speak).
    4. Discreet Cleanmeter performance telemetry.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLT Bilingual Core · Traductor Bilingüe de Lengua de Señas")
        self.setMinimumSize(1150, 750)
        self.setStyleSheet(COMMUNICATION_THEME)

        # 1. Initialize Subsystems (Single Unified Engine)
        self.lexicon = Lexicon()
        self.detector = HandDetector(num_hands=2)
        self.classifier = SLTClassifier()
        self.interaction = SLTInteractionEngine()
        self.translator = BilingualTranslator(self.lexicon)
        self.speech = SpeechWorker(mode="both", auto_speak=False)

        # Interaction / Mode state
        self._current_es = ""
        self._current_en = ""
        self._fps = 30.0
        self._latency = 0.0
        self._num_hands = 0
        self._is_video_mode = False

        # 2. Build Interface Layout
        self._build_ui()

        # 3. Connect Signals
        self._connect_signals()

        # 4. Setup Shortcuts
        self._setup_shortcuts()

        # 5. Start Live Camera by default
        self.camera_worker = CameraWorker(camera_index=0, width=640, height=480, fps=30)
        self.camera_worker.frame_ready.connect(self._on_camera_frame)
        self.camera_worker.metrics_updated.connect(self._on_camera_metrics)
        self.camera_worker.start()

        # Video worker placeholder
        self.video_worker: Optional[VideoFileWorker] = None

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # Header Toolbar
        # -------------------------------------------------------------
        header = QHBoxLayout()
        header.setSpacing(12)

        # Branding
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_title = QLabel("SLT BILINGUAL")
        app_title.setObjectName("headerTitle")
        app_sub = QLabel("REAL-TIME SIGN LANGUAGE TRANSLATOR")
        app_sub.setObjectName("headerSubtitle")
        title_box.addWidget(app_title)
        title_box.addWidget(app_sub)
        header.addLayout(title_box)

        header.addStretch()

        # Source Switcher (Live Camera vs Video File)
        self.source_tabs = QTabWidget()
        self.source_tabs.setFixedHeight(34)
        self.source_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar::tab {{
                background: {SLATE_LIGHT};
                color: {MIST};
                padding: 6px 14px;
                border-radius: 4px;
                margin-right: 4px;
                font-weight: bold;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background: {TEAL};
                color: {GRAPHITE};
            }}
        """)
        self.source_tabs.addTab(QWidget(), "📹 Cámara en Vivo")
        self.source_tabs.addTab(QWidget(), "📁 Analizar Video Local")
        self.source_tabs.currentChanged.connect(self._on_source_tab_changed)
        header.addWidget(self.source_tabs)

        # Pillar 1 Switch: Visualización de Reconocimiento (Clean screen vs Demo overlays)
        vis_box = QHBoxLayout()
        vis_box.setSpacing(6)
        vis_lbl = QLabel("Visualización:")
        vis_lbl.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: bold;")
        vis_box.addWidget(vis_lbl)

        self.vis_toggle_btn = QPushButton("DESACTIVADA (Pantalla limpia)")
        self.vis_toggle_btn.setCheckable(True)
        self.vis_toggle_btn.setChecked(False)
        self.vis_toggle_btn.setToolTip(
            "Modifica exclusivamente la representación visual.\n"
            "El motor de reconocimiento permanece activo en ambos modos."
        )
        self.vis_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SLATE_LIGHT};
                color: {MUTED};
                border: 1px solid #335366;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:checked {{
                background-color: rgba(66, 191, 176, 0.2);
                color: {TEAL};
                border-color: {TEAL};
            }}
        """)
        self.vis_toggle_btn.clicked.connect(self._toggle_visualization)
        vis_box.addWidget(self.vis_toggle_btn)
        header.addLayout(vis_box)

        # Pillar 3: Selector de Voz
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["Voz: Ambos (ES + EN)", "Voz: Sólo Español", "Voz: Only English"])
        self.voice_combo.currentIndexChanged.connect(self._on_voice_mode_changed)
        header.addWidget(self.voice_combo)

        # Guide Drawer toggle
        self.guide_btn = QPushButton("Catálogo (F1)")
        self.guide_btn.setCheckable(True)
        self.guide_btn.setChecked(False)
        self.guide_btn.clicked.connect(self._toggle_guide)
        header.addWidget(self.guide_btn)

        main_layout.addLayout(header)

        # -------------------------------------------------------------
        # Central Horizontal Workspace
        # -------------------------------------------------------------
        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        # Left Column: Perception Stage (Clean or Demo) + Sign Timeline
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        self.stage = PerceptionStage()
        left_col.addWidget(self.stage, stretch=5)

        self.timeline = SignTimelineWidget()
        left_col.addWidget(self.timeline, stretch=1)

        body_layout.addLayout(left_col, stretch=6)

        # Right Column: Subtitles (Live Mode) OR Video Analysis (File Mode)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        self.live_subtitles = LanguageOutputCard()
        self.video_analysis = VideoAnalysisWidget()
        self.video_analysis.setVisible(False)

        right_col.addWidget(self.live_subtitles, stretch=1)
        right_col.addWidget(self.video_analysis, stretch=1)

        body_layout.addLayout(right_col, stretch=4)

        # Optional Contextual Sign Catalog Drawer
        self.drawer = SignGuideDrawer(self.lexicon.words)
        self.drawer.setVisible(False)
        body_layout.addWidget(self.drawer)

        main_layout.addLayout(body_layout, stretch=1)

        # -------------------------------------------------------------
        # Pillar 4: Footer Cleanmeter Diagnostics Bar
        # -------------------------------------------------------------
        self.diagnostics = DiagnosticsBar()
        main_layout.addWidget(self.diagnostics)

    def _connect_signals(self):
        # Interaction Engine events
        self.interaction.sign_confirmed.connect(self._on_sign_confirmed)
        self.interaction.candidate_progress.connect(self.stage.set_candidate_progress)
        self.interaction.timeline_updated.connect(self.timeline.set_events)
        self.timeline.event_deleted.connect(self._on_timeline_event_deleted)

        # Subtitles Card signals
        self.live_subtitles.speak_requested.connect(self.speak_current_sentence)
        self.live_subtitles.auto_speak_toggled.connect(self.speech.set_auto_speak)

        # Video Analysis Widget signals
        self.video_analysis.start_analysis_requested.connect(self._start_video_analysis)
        self.video_analysis.stop_analysis_requested.connect(self._stop_video_analysis)
        self.video_analysis.speak_requested.connect(lambda es, en: self.speech.speak(es, en))

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Space), self, self.speak_current_sentence)
        QShortcut(QKeySequence(Qt.Key_Backspace), self, self.undo_last_sign)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_sentence)
        QShortcut(QKeySequence(Qt.Key_F1), self, self._toggle_guide)
        QShortcut(QKeySequence(Qt.Key_F2), self, self._toggle_visualization_shortcut)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    # -----------------------------------------------------------------
    # Unified Recognition Processing (Single Engine, Two Sources)
    # -----------------------------------------------------------------
    def _process_frame_through_engine(
        self,
        frame_bgr: np.ndarray,
        qimg_clean: QImage,
        timestamp_sec: float,
        source_name: str
    ):
        """
        Feeds any video source (live camera or local video file)
        through the exact same MediaPipe -> 106-D -> Classifier -> Interaction pipeline.
        """
        # 1. Perception
        perception = self.detector.detect(frame_bgr)
        self._num_hands = perception.num_hands
        self._latency = perception.inference_time_ms

        raw_pred = "_NADA_"
        confidence = 0.0
        is_valid = False
        handedness = "Right"
        qimg_annotated = None

        # 2. Recognition
        if perception.hands:
            primary_hand = perception.hands[0]
            handedness = primary_hand.handedness
            features = extract_features(primary_hand.landmarks_norm)
            raw_pred, confidence, is_valid = self.classifier.predict(features)

            # Generate overlay only if needed for display
            annotated_bgr = draw_hand_skeleton(frame_bgr.copy(), primary_hand.landmarks_norm)
            if len(perception.hands) > 1:
                annotated_bgr = draw_hand_skeleton(annotated_bgr, perception.hands[1].landmarks_norm)

            rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg_annotated = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()

        # Update viewport
        self.stage.set_frames(qimg_clean, qimg_annotated)

        # 3. Temporal Interaction State Machine
        state = self.interaction.process_frame(
            has_hands=bool(perception.hands),
            raw_prediction=raw_pred,
            confidence=confidence,
            is_valid=is_valid,
            handedness=handedness,
            custom_timestamp_sec=timestamp_sec
        )

        self.stage.update_interaction_state(
            state=state,
            gloss=raw_pred,
            conf=confidence,
            num_hands=self._num_hands,
            source_name=source_name
        )

    # -----------------------------------------------------------------
    # Live Camera Handlers
    # -----------------------------------------------------------------
    def _on_camera_frame(self, frame_bgr: np.ndarray, qimg: QImage, timestamp_ms: float):
        if not self._is_video_mode:
            self._process_frame_through_engine(
                frame_bgr=frame_bgr,
                qimg_clean=qimg,
                timestamp_sec=timestamp_ms / 1000.0,
                source_name="Cámara"
            )
            self.diagnostics.update_camera_metrics(self._fps, self._latency, self._num_hands)

    def _on_camera_metrics(self, fps: float, latency_ms: float):
        self._fps = fps

    # -----------------------------------------------------------------
    # Video File Handlers
    # -----------------------------------------------------------------
    def _start_video_analysis(self, file_path: str):
        self._stop_video_analysis()
        self.clear_sentence()

        logger.info(f"Starting offline analysis of {file_path}")
        self.video_worker = VideoFileWorker(file_path, realtime_speed=True, flip_horizontal=False)
        self.video_worker.frame_ready.connect(self._on_video_file_frame)
        self.video_worker.progress_updated.connect(self._on_video_file_progress)
        self.video_worker.analysis_finished.connect(self._on_video_file_finished)
        self.video_worker.start()

    def _on_video_file_frame(self, frame_bgr: np.ndarray, qimg: QImage, video_time_sec: float):
        if self._is_video_mode:
            self._process_frame_through_engine(
                frame_bgr=frame_bgr,
                qimg_clean=qimg,
                timestamp_sec=video_time_sec,
                source_name="Video local"
            )

    def _on_video_file_progress(self, frame_idx: int, total: int, pct: float, elapsed: float, fps: float):
        if self._is_video_mode:
            self.video_analysis.update_progress(frame_idx, total, pct, elapsed, fps)
            self.diagnostics.update_video_metrics(pct, fps, self._num_hands)

    def _on_video_file_finished(self, total_frames: int, total_elapsed: float):
        logger.info("Video file analysis finished.")
        events = self.interaction.get_timeline()
        self.video_analysis.set_results(events, self._current_es, self._current_en)

    def _stop_video_analysis(self):
        if self.video_worker and self.video_worker.isRunning():
            self.video_worker.stop()
            self.video_worker = None

    # -----------------------------------------------------------------
    # Interaction & Translation Handlers
    # -----------------------------------------------------------------
    def _on_sign_confirmed(self, event: SignEvent):
        es_text, en_text = self.translator.add_gloss(event.label)
        self._current_es = es_text
        self._current_en = en_text
        self.live_subtitles.set_translations(es_text, en_text)

        # Pillar 3: Auto-speak if enabled
        if self.speech.auto_speak and (es_text or en_text):
            self.speech.speak(es_text, en_text)

        if self._is_video_mode:
            self.video_analysis.set_results(
                self.interaction.get_timeline(),
                self._current_es,
                self._current_en
            )

    def _on_timeline_event_deleted(self, event_id: str):
        self.interaction.remove_event(event_id)
        remaining_glosses = [ev.label for ev in self.interaction.get_timeline()]
        self.translator.gloss_buffer = list(remaining_glosses)
        es_text, en_text = self.translator.translate()
        self._current_es = es_text
        self._current_en = en_text
        self.live_subtitles.set_translations(es_text, en_text)
        if self._is_video_mode:
            self.video_analysis.set_results(
                self.interaction.get_timeline(),
                self._current_es,
                self._current_en
            )

    def speak_current_sentence(self):
        if self._current_es or self._current_en:
            self.speech.speak(self._current_es, self._current_en)

    def undo_last_sign(self):
        self.interaction.remove_last_event()
        es_text, en_text = self.translator.remove_last_gloss()
        self._current_es = es_text
        self._current_en = en_text
        self.live_subtitles.set_translations(es_text, en_text)

    def clear_sentence(self):
        self.interaction.clear_timeline()
        self.translator.clear()
        self._current_es = ""
        self._current_en = ""
        self.live_subtitles.set_translations("", "")

    # -----------------------------------------------------------------
    # Mode & Setting Toggles
    # -----------------------------------------------------------------
    def _toggle_visualization(self):
        enabled = self.vis_toggle_btn.isChecked()
        self.stage.set_visualization_enabled(enabled)
        if enabled:
            self.vis_toggle_btn.setText("ACTIVADA (Modo Demo)")
        else:
            self.vis_toggle_btn.setText("DESACTIVADA (Pantalla limpia)")

    def _toggle_visualization_shortcut(self):
        self.vis_toggle_btn.setChecked(not self.vis_toggle_btn.isChecked())
        self._toggle_visualization()

    def _on_source_tab_changed(self, index: int):
        self._is_video_mode = (index == 1)
        self.clear_sentence()

        if self._is_video_mode:
            # Switch to local video file mode
            self.live_subtitles.setVisible(False)
            self.video_analysis.setVisible(True)
        else:
            # Switch back to live camera mode
            self._stop_video_analysis()
            self.video_analysis.setVisible(False)
            self.live_subtitles.setVisible(True)

    def _toggle_guide(self):
        visible = not self.drawer.isVisible()
        self.drawer.setVisible(visible)
        self.guide_btn.setChecked(visible)

    def _on_voice_mode_changed(self, index: int):
        modes = ["both", "es", "en"]
        if index < len(modes):
            self.speech.set_mode(modes[index])

    def closeEvent(self, event):
        self._stop_video_analysis()
        if hasattr(self, "camera_worker"):
            self.camera_worker.stop()
        if hasattr(self, "speech"):
            self.speech.stop()
        if hasattr(self, "detector"):
            self.detector.close()
        event.accept()
