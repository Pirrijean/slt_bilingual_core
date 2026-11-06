"""Bilingual subtitle and gloss accumulation widget."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QProgressBar
)
from PySide6.QtCore import Signal, Qt

class TranslationWidget(QFrame):
    speak_requested = Signal()
    undo_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header with action buttons
        header_bar = QHBoxLayout()
        title = QLabel("TRADUCCIÓN BILINGÜE / TRANSLATION")
        title.setObjectName("sectionTitle")
        header_bar.addWidget(title)
        header_bar.addStretch()

        self.btn_undo = QPushButton("Deshacer")
        self.btn_undo.setToolTip("Eliminar última seña (Retroceso)")
        self.btn_undo.clicked.connect(self.undo_requested.emit)
        header_bar.addWidget(self.btn_undo)

        self.btn_clear = QPushButton("Limpiar")
        self.btn_clear.setObjectName("dangerButton")
        self.btn_clear.setToolTip("Vaciar frase actual (F4 o Ctrl+L)")
        self.btn_clear.clicked.connect(self.clear_requested.emit)
        header_bar.addWidget(self.btn_clear)

        layout.addLayout(header_bar)

        # Glosas acumuladas
        gloss_box = QFrame()
        gloss_box.setObjectName("cardSubPanel")
        gb_layout = QVBoxLayout(gloss_box)
        gb_layout.setContentsMargins(12, 10, 12, 10)
        gb_layout.setSpacing(4)

        g_title = QLabel("SEÑAS CONFIRMADAS (GLOSAS)")
        g_title.setObjectName("sectionTitle")
        gb_layout.addWidget(g_title)

        self.glosses_label = QLabel("(Esperando señas...)")
        self.glosses_label.setObjectName("glossDisplay")
        self.glosses_label.setWordWrap(True)
        gb_layout.addWidget(self.glosses_label)

        layout.addWidget(gloss_box)

        # Spanish card
        card_es = QFrame()
        card_es.setObjectName("cardSubPanel")
        es_layout = QVBoxLayout(card_es)
        es_layout.setContentsMargins(12, 10, 12, 10)
        es_layout.setSpacing(4)

        lbl_es_head = QLabel("ESPAÑOL")
        lbl_es_head.setObjectName("sectionTitle")
        lbl_es_head.setStyleSheet("color: #38d9a9;")
        es_layout.addWidget(lbl_es_head)

        self.text_es = QLabel("Realiza una seña frente a la cámara...")
        self.text_es.setObjectName("subtitleLabelES")
        self.text_es.setWordWrap(True)
        es_layout.addWidget(self.text_es)

        layout.addWidget(card_es)

        # English card
        card_en = QFrame()
        card_en.setObjectName("cardSubPanel")
        en_layout = QVBoxLayout(card_en)
        en_layout.setContentsMargins(12, 10, 12, 10)
        en_layout.setSpacing(4)

        lbl_en_head = QLabel("ENGLISH")
        lbl_en_head.setObjectName("sectionTitle")
        lbl_en_head.setStyleSheet("color: #7dd3fc;")
        en_layout.addWidget(lbl_en_head)

        self.text_en = QLabel("Perform a sign in front of the camera...")
        self.text_en.setObjectName("subtitleLabelEN")
        self.text_en.setWordWrap(True)
        en_layout.addWidget(self.text_en)

        layout.addWidget(card_en)

        # Speak primary action button
        self.btn_speak = QPushButton("Pronunciar / Speak (Espacio)")
        self.btn_speak.setObjectName("primaryButton")
        self.btn_speak.setFixedHeight(40)
        self.btn_speak.clicked.connect(self.speak_requested.emit)
        layout.addWidget(self.btn_speak)

    def update_translation(self, glosses: list[str], text_es: str, text_en: str):
        if glosses:
            self.glosses_label.setText("  →  ".join(glosses))
        else:
            self.glosses_label.setText("(Esperando señas...)")

        self.text_es.setText(text_es if text_es else "Realiza una seña frente a la cámara...")
        self.text_en.setText(text_en if text_en else "Perform a sign in front of the camera...")
