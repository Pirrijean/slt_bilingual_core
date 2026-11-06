#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Application Orchestrator.
Encapsulates high-level lifecycle coordination, signal wiring, and GUI invocation.
"""
import sys
import logging
from PySide6.QtWidgets import QApplication

from slt.ui.main_window import MainWindow
from slt.ui.theme import COMMUNICATION_THEME
from slt.utils.logging_config import setup_logging

def run_application():
    """Main application launcher."""
    setup_logging()
    logger = logging.getLogger("slt.application")
    logger.info("Starting SLT Bilingual Core Communication Workspace...")

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("SLT Bilingual Core")
    app.setOrganizationName("SLT AI Lab")
    app.setStyleSheet(COMMUNICATION_THEME)

    window = MainWindow()
    window.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(run_application())
