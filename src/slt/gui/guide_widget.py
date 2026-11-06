"""Sign guide drawer widget."""
from __future__ import annotations
import json
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
from slt.utils.paths import LEXICON_PATH, CLASSES_PATH

class GuideWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QLabel("VOCABULARIO Y GUÍA DE SEÑAS DISPONIBLES")
        header.setObjectName("headerSubtitle")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        self.grid = QVBoxLayout(content)
        self.grid.setSpacing(10)
        self.grid.setContentsMargins(4, 4, 4, 4)

        self._populate_signs()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _populate_signs(self):
        try:
            with open(LEXICON_PATH, "r", encoding="utf-8") as f:
                lex_data = json.load(f)
            words = lex_data.get("words", {})
        except Exception:
            words = {}

        # Group by category
        categories: dict[str, list[tuple[str, dict]]] = {}
        for sign_name, info in words.items():
            cat = info.get("category", "General")
            categories.setdefault(cat, []).append((sign_name, info))

        for cat_name, sign_list in categories.items():
            cat_header = QLabel(cat_name.upper())
            cat_header.setObjectName("sectionTitle")
            cat_header.setStyleSheet("color: #38d9a9; font-weight: 700; margin-top: 6px;")
            self.grid.addWidget(cat_header)

            for sign_name, info in sign_list:
                item_card = QFrame()
                item_card.setObjectName("cardSubPanel")
                card_lay = QVBoxLayout(item_card)
                card_lay.setContentsMargins(10, 8, 10, 8)
                card_lay.setSpacing(4)

                top_row = QHBoxLayout()
                lbl_name = QLabel(sign_name)
                lbl_name.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 14px;")
                top_row.addWidget(lbl_name)

                es_text = info.get("solo_es") or (info["es"]["1"] if isinstance(info.get("es"), dict) else info.get("es", ""))
                en_text = info.get("solo_en") or (info["en"]["1"] if isinstance(info.get("en"), dict) else info.get("en", ""))
                lbl_trans = QLabel(f"{es_text}  /  {en_text}")
                lbl_trans.setStyleSheet("color: #94a3b8; font-size: 12px;")
                top_row.addWidget(lbl_trans)
                top_row.addStretch()
                card_lay.addLayout(top_row)

                guide_text = info.get("guide", "Realiza la configuración manual correspondiente.")
                lbl_guide = QLabel(guide_text)
                lbl_guide.setStyleSheet("color: #cbd5e1; font-size: 12px;")
                lbl_guide.setWordWrap(True)
                card_lay.addWidget(lbl_guide)

                self.grid.addWidget(item_card)

        self.grid.addStretch()
