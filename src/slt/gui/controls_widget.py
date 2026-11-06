"""Bottom controls bar widget."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton, QComboBox, QFrame
)
from PySide6.QtCore import Signal

class ControlsWidget(QFrame):
    camera_toggle_requested = Signal()
    pause_toggle_requested = Signal()
    language_changed = Signal(str)
    guide_toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardPanel")
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        # Camera controls
        self.btn_camera = QPushButton("Detener Cámara")
        self.btn_camera.clicked.connect(self.camera_toggle_requested.emit)
        layout.addWidget(self.btn_camera)

        self.btn_pause = QPushButton("Pausar Detección")
        self.btn_pause.clicked.connect(self.pause_toggle_requested.emit)
        layout.addWidget(self.btn_pause)

        layout.addSpacing(16)

        # Voice language selection
        lbl_lang = QLabel("Modo de Voz:")
        lbl_lang.setObjectName("sectionTitle")
        layout.addWidget(lbl_lang)

        self.combo_lang = QComboBox()
        self.combo_lang.addItem("Bilingüe (ES + EN)", "both")
        self.combo_lang.addItem("Español (ES)", "es")
        self.combo_lang.addItem("English (EN)", "en")
        self.combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        layout.addWidget(self.combo_lang)

        layout.addStretch()

        # Guide toggle button
        self.btn_guide = QPushButton("Guía de Señas (F1)")
        self.btn_guide.setStyleSheet("background-color: #1e293b; border-color: #334155; color: #38d9a9;")
        self.btn_guide.clicked.connect(self.guide_toggle_requested.emit)
        layout.addWidget(self.btn_guide)

    def _on_lang_changed(self, index: int):
        data = self.combo_lang.currentData()
        self.language_changed.emit(data)

    def set_camera_active(self, is_active: bool):
        self.btn_camera.setText("Detener Cámara" if is_active else "Iniciar Cámara")

    def set_detection_paused(self, is_paused: bool):
        self.btn_pause.setText("Reanudar Detección" if is_paused else "Pausar Detección")
