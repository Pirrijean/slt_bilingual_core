#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Desktop Application Entry Point.
Launches the SLT Communication Workspace (PySide6).
"""
import sys
from pathlib import Path

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from slt_desktop.main_window import main

if __name__ == "__main__":
    sys.exit(main())
