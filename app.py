#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Desktop Application Entry Point.
Runs the minimalist, professional PySide6 graphical interface.
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from slt.gui.main_window import MainWindow
from slt.gui.styles import DARK_THEME

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SLT Bilingual Core")
    app.setOrganizationName("SLT AI Lab")
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
