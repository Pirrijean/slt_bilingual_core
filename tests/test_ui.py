#!/usr/bin/env python3
"""
Tests for slt_desktop.main_window module.
Verifies MainWindow lifecycle, component wiring, sign confirmation, and undo/clear in headless mode.
"""
import os
import sys

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from slt_desktop.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Ensure a singleton QApplication exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_main_window_initial_state(qapp):
    """Verify MainWindow initializes cleanly with correct default labels and controls."""
    win = MainWindow(auto_start_camera=False)
    assert win.windowTitle().startswith("SLT Bilingual Core")
    assert win.lbl_es.text() == "Esperando señas..."
    assert win.lbl_en.text() == "Waiting for signs..."
    assert win.demo_toggle.isChecked() is False  # Mode A clean screen by default
    assert win.btn_export_srt.isEnabled() is False
    assert win.btn_export_txt.isEnabled() is False
    win.close()


def test_main_window_sign_confirmation_flow(qapp):
    """Verify sign events update subtitles, timeline strip, and export buttons."""
    win = MainWindow(auto_start_camera=False)

    # Emit confirmed greeting event
    ev1 = {"label": "HOLA", "start_ms": 1000, "end_ms": 2000, "stability": 0.95}
    win._on_signs_confirmed([ev1])

    assert "¡Hola!" in win.lbl_es.text()
    assert "Hello!" in win.lbl_en.text()
    assert "[HOLA]" in win.lbl_gloss_strip.text()
    assert win.btn_export_srt.isEnabled() is True
    assert win.btn_export_txt.isEnabled() is True

    # Emit second sign
    ev2 = {"label": "AGUA", "start_ms": 2500, "end_ms": 3800, "stability": 0.92}
    win._on_signs_confirmed([ev2])

    assert "agua" in win.lbl_es.text().lower()
    assert "water" in win.lbl_en.text().lower()
    assert "[HOLA] → [AGUA]" in win.lbl_gloss_strip.text()

    # Test Undo
    win._on_undo_clicked()
    assert "[HOLA]" in win.lbl_gloss_strip.text()
    assert "¡Hola!" in win.lbl_es.text()

    # Test Clear
    win._on_clear_clicked()
    assert win.lbl_es.text() == "Esperando señas..."
    assert win.lbl_gloss_strip.text() == "(Sin señas confirmadas)"
    assert win.btn_export_srt.isEnabled() is False

    win.close()


def test_main_window_mode_and_telemetry(qapp):
    """Verify metrics update and mode toggle behavior."""
    win = MainWindow(auto_start_camera=False)

    win._on_metrics_updated(fps=29.8, latency_ms=14.2, num_hands=2)
    assert "29.8" in win.lbl_fps.text()
    assert "14.2" in win.lbl_latency.text()
    assert "Manos: 2" in win.lbl_hands.text()

    # Toggle demonstration mode (Mode B)
    win.demo_toggle.setChecked(True)
    assert win.demo_toggle.isChecked() is True

    win.close()
