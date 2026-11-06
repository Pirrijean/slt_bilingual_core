#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Desktop Application Entry Point.
Launches the SLT Communication Workspace (PySide6).
"""
from __future__ import annotations
import sys
from pathlib import Path

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
from slt_desktop.main_window import MainWindow
from slt_desktop.theme import DARK_THEME
from slt_desktop.recognition_adapter import build_recognition_backend
from slt_desktop.translation_adapter import TranslationAdapter


def main():
    root = Path(__file__).resolve().parent
    hand_model = root / "models" / "hand_landmarker.task"

    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)

    application.setApplicationName("SLT Bilingual Core")
    application.setApplicationVersion("1.0.0")
    application.setStyleSheet(DARK_THEME)

    recognition_backend = build_recognition_backend()
    translation_adapter = TranslationAdapter()

    window = MainWindow(
        hand_model_path=hand_model,
        recognizer_factory=lambda: recognition_backend,
        translation_service=translation_adapter
    )
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
