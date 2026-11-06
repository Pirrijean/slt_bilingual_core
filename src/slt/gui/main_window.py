"""Main application window for SLT Bilingual Core."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter
)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt, Slot

from slt.gui.video_widget import VideoWidget
from slt.gui.translation_widget import TranslationWidget
from slt.gui.controls_widget import ControlsWidget
from slt.gui.guide_widget import GuideWidget
from slt.camera.camera_worker import CameraWorker
from slt.language.translator import BilingualTranslator
from slt.audio.speech_worker import SpeechWorker
from slt.utils.paths import LEXICON_PATH

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLT Bilingual Core — Sign Language Translator (ES / EN)")
        self.resize(1360, 840)
        self.setMinimumSize(1080, 680)

        # Core logic workers
        self.translator = BilingualTranslator(LEXICON_PATH)
        self.speech_worker = SpeechWorker(rate=0)
        self.audio_mode = "both"  # "es", "en", or "both"

        self.camera_worker = CameraWorker(camera_index=0, width=1280, height=720)
        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

        # Start camera worker thread
        self.camera_worker.start()

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(12)

        # 1. Header bar
        header_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("SLT BILINGUAL CORE")
        title.setObjectName("headerTitle")
        title_box.addWidget(title)

        subtitle = QLabel("TRADUCTOR DE SEÑAS EN TIEMPO REAL • RECONOCIMIENTO ANATÓMICO 3D • SÍNTESIS BILINGÜE")
        subtitle.setObjectName("headerSubtitle")
        title_box.addWidget(subtitle)

        header_bar.addLayout(title_box)
        header_bar.addStretch()

        status_badge = QLabel("SISTEMA LISTO")
        status_badge.setObjectName("liveBadge")
        header_bar.addWidget(status_badge)

        root_layout.addLayout(header_bar)

        # 2. Main content splitter (Video on left, Subtitles & Guide on right)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # Video pane
        self.video_widget = VideoWidget()
        self.splitter.addWidget(self.video_widget)

        # Right side pane: Translation widget + Collapsible Guide
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.translation_widget = TranslationWidget()
        right_layout.addWidget(self.translation_widget, stretch=1)

        self.guide_widget = GuideWidget()
        self.guide_widget.setVisible(False)  # Hidden by default
        right_layout.addWidget(self.guide_widget, stretch=1)

        self.splitter.addWidget(right_container)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)

        root_layout.addWidget(self.splitter, stretch=1)

        # 3. Bottom controls bar
        self.controls_widget = ControlsWidget()
        root_layout.addWidget(self.controls_widget)

    def _connect_signals(self):
        # Camera signals
        self.camera_worker.frame_ready.connect(self.video_widget.update_frame)
        self.camera_worker.sign_confirmed.connect(self.on_sign_confirmed)

        # Translation controls
        self.translation_widget.speak_requested.connect(self.speak_current_sentence)
        self.translation_widget.undo_requested.connect(self.undo_last_sign)
        self.translation_widget.clear_requested.connect(self.clear_sentence)

        # Controls bar signals
        self.controls_widget.camera_toggle_requested.connect(self.toggle_camera)
        self.controls_widget.pause_toggle_requested.connect(self.toggle_pause)
        self.controls_widget.language_changed.connect(self.set_audio_language)
        self.controls_widget.guide_toggle_requested.connect(self.toggle_guide)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F1"), self, self.toggle_guide)
        QShortcut(QKeySequence("F2"), self, self.toggle_camera)
        QShortcut(QKeySequence("F3"), self, self.toggle_pause)
        QShortcut(QKeySequence("F4"), self, self.clear_sentence)
        QShortcut(QKeySequence("F5"), self, lambda: self.speak_current_sentence("es"))
        QShortcut(QKeySequence("F6"), self, lambda: self.speak_current_sentence("en"))
        QShortcut(QKeySequence("F7"), self, lambda: self.speak_current_sentence("both"))
        QShortcut(QKeySequence(Qt.Key_Space), self, lambda: self.speak_current_sentence())
        QShortcut(QKeySequence(Qt.Key_Backspace), self, self.undo_last_sign)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_sentence)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    @Slot(str)
    def on_sign_confirmed(self, sign: str):
        res = self.translator.add_gloss(sign)
        self.translation_widget.update_translation(res["glosses"], res["es"], res["en"])

    @Slot()
    def speak_current_sentence(self, override_mode: str | None = None):
        res = self.translator.get_translation()
        mode = override_mode or self.audio_mode
        self.speech_worker.speak_bilingual(res["es"], res["en"], mode=mode)

    @Slot()
    def undo_last_sign(self):
        res = self.translator.remove_last_gloss()
        self.translation_widget.update_translation(res["glosses"], res["es"], res["en"])

    @Slot()
    def clear_sentence(self):
        res = self.translator.clear_sentence()
        self.translation_widget.update_translation(res["glosses"], res["es"], res["en"])

    @Slot()
    def toggle_camera(self):
        if self.camera_worker.isRunning():
            self.camera_worker.stop()
            self.controls_widget.set_camera_active(False)
        else:
            self.camera_worker = CameraWorker(camera_index=0)
            self.camera_worker.frame_ready.connect(self.video_widget.update_frame)
            self.camera_worker.sign_confirmed.connect(self.on_sign_confirmed)
            self.camera_worker.start()
            self.controls_widget.set_camera_active(True)

    @Slot()
    def toggle_pause(self):
        new_paused = not self.camera_worker.paused
        self.camera_worker.set_paused(new_paused)
        self.controls_widget.set_detection_paused(new_paused)
        self.video_widget.set_paused_status(new_paused)

    @Slot(str)
    def set_audio_language(self, lang_mode: str):
        self.audio_mode = lang_mode

    @Slot()
    def toggle_guide(self):
        is_visible = self.guide_widget.isVisible()
        self.guide_widget.setVisible(not is_visible)
        self.controls_widget.btn_guide.setText("Ocultar Guía" if not is_visible else "Guía de Señas (F1)")

    def closeEvent(self, event):
        self.camera_worker.stop()
        self.speech_worker.close()
        event.accept()
