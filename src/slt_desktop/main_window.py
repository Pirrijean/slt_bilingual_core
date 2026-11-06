#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Main Application Window.
Unified desktop GUI implementing the 4 Pillars of SLT Bilingual Core:
1. Real-time visual interaction & recognition (Clean screen Mode A by default, Demo Mode B toggle)
2. Simultaneous bilingual translation & subtitles (Live subtitles + SRT & TXT export)
3. Speech synthesis communication (Spanish, English, Both, Auto-speak)
4. Discreet Cleanmeter performance telemetry
"""
from typing import List, Dict, Any, Optional
import os
import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QComboBox, QCheckBox,
    QFileDialog, QProgressBar, QMessageBox, QApplication,
    QScrollArea
)
from PySide6.QtGui import QImage, QPixmap, QShortcut, QKeySequence, QFont
from PySide6.QtCore import Qt, Slot

from slt_desktop.theme import DARK_THEME, TEAL_ACCENT, MINT_ACCENT
from slt_desktop.vision_worker import VisionWorker
from slt_desktop.recognition_adapter import build_recognition_backend
from slt_desktop.translation_adapter import TranslationAdapter
from slt_desktop.subtitles import create_srt_content, export_srt, create_transcription_txt
from slt.speech import SpeechWorker

logger = logging.getLogger("slt_desktop.main_window")


class MainWindow(QMainWindow):
    """SLT Bilingual Core Desktop Workspace."""

    def __init__(self, auto_start_camera: bool = True):
        super().__init__()
        self.setWindowTitle("SLT Bilingual Core · Traductor Bilingüe de Lengua de Señas")
        self.setMinimumSize(1150, 780)
        self.setStyleSheet(DARK_THEME)

        # Core Engines
        self.backend = build_recognition_backend()
        self.translator = TranslationAdapter()
        self.speech = SpeechWorker(mode="both", auto_speak=False)

        # State Variables
        self.gloss_sequence: List[str] = []
        self.accumulated_events: List[Dict[str, Any]] = []
        self.current_es = ""
        self.current_en = ""
        self.is_video_mode = False
        self.current_video_filename = ""

        # Workers
        self.vision_worker: Optional[VisionWorker] = None

        # Build UI and Signal Connections
        self._build_ui()
        self._setup_shortcuts()

        # Start Camera by Default if requested
        if auto_start_camera:
            self._start_camera_session()

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. Header Toolbar
        # -------------------------------------------------------------
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(16)

        # Brand Title & Mode Badge
        brand_box = QHBoxLayout()
        brand_box.setSpacing(10)
        app_title = QLabel("SLT BILINGUAL")
        app_title.setObjectName("AppTitle")

        self.mode_badge = QLabel("EN VIVO")
        self.mode_badge.setObjectName("ModeBadgeLive")

        brand_box.addWidget(app_title)
        brand_box.addWidget(self.mode_badge)
        header_layout.addLayout(brand_box)

        header_layout.addStretch()

        # Anatomical Overlay Switch (Default: OFF / Mode A)
        self.demo_toggle = QCheckBox("Demostración anatómica")
        self.demo_toggle.setChecked(False)
        self.demo_toggle.setToolTip("Activar esqueletos anatómicos de manos (Modo B)")
        self.demo_toggle.toggled.connect(self._on_demo_toggle)
        header_layout.addWidget(self.demo_toggle)

        # Voice Selector
        voice_lbl = QLabel("Voz:")
        voice_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        header_layout.addWidget(voice_lbl)

        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["Ambos (ES/EN)", "Español", "English"])
        self.voice_combo.currentIndexChanged.connect(self._on_voice_combo_changed)
        header_layout.addWidget(self.voice_combo)

        # Auto-speak Toggle
        self.auto_speak_toggle = QCheckBox("Voz automática")
        self.auto_speak_toggle.setChecked(False)
        self.auto_speak_toggle.toggled.connect(self._on_auto_speak_toggled)
        header_layout.addWidget(self.auto_speak_toggle)

        # Video / Camera Switch Buttons
        self.btn_open_video = QPushButton("Abrir Video...")
        self.btn_open_video.clicked.connect(self._on_open_video_clicked)
        header_layout.addWidget(self.btn_open_video)

        self.btn_live_camera = QPushButton("Cámara en Vivo")
        self.btn_live_camera.setObjectName("PrimaryButton")
        self.btn_live_camera.clicked.connect(self._on_live_camera_clicked)
        header_layout.addWidget(self.btn_live_camera)

        main_layout.addWidget(header_card)

        # -------------------------------------------------------------
        # 2. Central Section (Video Canvas + Subtitle Banner)
        # -------------------------------------------------------------
        canvas_card = QFrame()
        canvas_card.setObjectName("VideoCard")
        canvas_layout = QVBoxLayout(canvas_card)
        canvas_layout.setContentsMargins(12, 12, 12, 12)
        canvas_layout.setSpacing(10)

        # Video Frame Display (Clean Aspect Ratio)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 380)
        self.video_label.setStyleSheet("background-color: #0A0D12; border-radius: 6px;")
        canvas_layout.addWidget(self.video_label, stretch=1)

        # Subtitle Display Card (High Contrast Legibility)
        sub_card = QFrame()
        sub_card.setObjectName("SubtitleCard")
        sub_card.setStyleSheet("background-color: #161C26; border: 1px solid #2D3748; border-radius: 8px;")
        sub_layout = QVBoxLayout(sub_card)
        sub_layout.setContentsMargins(18, 12, 18, 12)
        sub_layout.setSpacing(6)

        # Subtitle Controls Row
        sub_controls = QHBoxLayout()
        sub_title = QLabel("TRADUCCIÓN BILINGÜE SIMULTÁNEA")
        sub_title.setObjectName("SubtitleHeading")
        sub_controls.addWidget(sub_title)
        sub_controls.addStretch()

        self.btn_speak = QPushButton("Pronunciar")
        self.btn_speak.setObjectName("PrimaryButton")
        self.btn_speak.clicked.connect(self._on_speak_clicked)
        sub_controls.addWidget(self.btn_speak)

        self.btn_copy = QPushButton("Copiar traducción")
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        sub_controls.addWidget(self.btn_copy)

        sub_layout.addLayout(sub_controls)

        # Spanish Translation Output
        self.lbl_es = QLabel("Esperando señas...")
        self.lbl_es.setObjectName("SubtitleTextES")
        self.lbl_es.setWordWrap(True)
        sub_layout.addWidget(self.lbl_es)

        # English Translation Output
        self.lbl_en = QLabel("Waiting for signs...")
        self.lbl_en.setObjectName("SubtitleTextEN")
        self.lbl_en.setWordWrap(True)
        sub_layout.addWidget(self.lbl_en)

        canvas_layout.addWidget(sub_card)
        main_layout.addWidget(canvas_card, stretch=1)

        # -------------------------------------------------------------
        # 3. Timeline / Recognized Signs Strip
        # -------------------------------------------------------------
        timeline_card = QFrame()
        timeline_card.setObjectName("TimelineCard")
        timeline_layout = QHBoxLayout(timeline_card)
        timeline_layout.setContentsMargins(16, 8, 16, 8)
        timeline_layout.setSpacing(10)

        timeline_lbl = QLabel("Historial:")
        timeline_lbl.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 12px;")
        timeline_layout.addWidget(timeline_lbl)

        self.lbl_gloss_strip = QLabel("(Sin señas confirmadas)")
        self.lbl_gloss_strip.setStyleSheet(
            "color: #42BFB0; font-family: monospace; font-size: 13px; font-weight: 600;"
        )
        self.lbl_gloss_strip.setWordWrap(True)
        timeline_layout.addWidget(self.lbl_gloss_strip, stretch=1)

        self.btn_undo = QPushButton("Deshacer")
        self.btn_undo.setToolTip("Eliminar última seña confirmada (Ctrl+Z)")
        self.btn_undo.clicked.connect(self._on_undo_clicked)
        timeline_layout.addWidget(self.btn_undo)

        self.btn_clear = QPushButton("Limpiar")
        self.btn_clear.setObjectName("DangerButton")
        self.btn_clear.setToolTip("Limpiar historial y oraciones (Esc)")
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        timeline_layout.addWidget(self.btn_clear)

        # Video Export Buttons
        self.btn_export_srt = QPushButton("Exportar SRT")
        self.btn_export_srt.setEnabled(False)
        self.btn_export_srt.clicked.connect(self._on_export_srt_clicked)
        timeline_layout.addWidget(self.btn_export_srt)

        self.btn_export_txt = QPushButton("Exportar TXT")
        self.btn_export_txt.setEnabled(False)
        self.btn_export_txt.clicked.connect(self._on_export_txt_clicked)
        timeline_layout.addWidget(self.btn_export_txt)

        main_layout.addWidget(timeline_card)

        # -------------------------------------------------------------
        # 4. Cleanmeter Telemetry Bar
        # -------------------------------------------------------------
        cleanmeter_card = QFrame()
        cleanmeter_card.setObjectName("CleanmeterCard")
        cleanmeter_layout = QHBoxLayout(cleanmeter_card)
        cleanmeter_layout.setContentsMargins(16, 6, 16, 6)
        cleanmeter_layout.setSpacing(18)

        # Telemetry Labels
        self.lbl_fps = QLabel("FPS: --")
        self.lbl_fps.setObjectName("TelemetryItem")
        cleanmeter_layout.addWidget(self.lbl_fps)

        self.lbl_latency = QLabel("Latencia: -- ms")
        self.lbl_latency.setObjectName("TelemetryItem")
        cleanmeter_layout.addWidget(self.lbl_latency)

        self.lbl_hands = QLabel("Manos: 0")
        self.lbl_hands.setObjectName("TelemetryItem")
        cleanmeter_layout.addWidget(self.lbl_hands)

        # Video Progress Bar (Shown in Video File Mode)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        cleanmeter_layout.addWidget(self.progress_bar, stretch=1)

        self.lbl_eta = QLabel("")
        self.lbl_eta.setObjectName("TelemetryItem")
        self.lbl_eta.setVisible(False)
        cleanmeter_layout.addWidget(self.lbl_eta)

        cleanmeter_layout.addStretch()

        self.lbl_status = QLabel("● Motor activo")
        self.lbl_status.setStyleSheet("color: #2DD4BF; font-weight: 600; font-size: 11px;")
        cleanmeter_layout.addWidget(self.lbl_status)

        main_layout.addWidget(cleanmeter_card)

    def _setup_shortcuts(self):
        """Keyboard shortcuts for efficient accessibility and control."""
        QShortcut(QKeySequence("Space"), self, self._on_speak_clicked)
        QShortcut(QKeySequence("Ctrl+C"), self, self._on_copy_clicked)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._on_undo_clicked)
        QShortcut(QKeySequence("Escape"), self, self._on_clear_clicked)

    # -----------------------------------------------------------------
    # Session Management (Camera vs Video File)
    # -----------------------------------------------------------------
    def _start_camera_session(self):
        """Start or restart live camera stream."""
        self._stop_vision_worker()
        self.is_video_mode = False
        self.mode_badge.setText("EN VIVO")
        self.mode_badge.setObjectName("ModeBadgeLive")
        self.mode_badge.setStyle(self.mode_badge.style())
        self.progress_bar.setVisible(False)
        self.lbl_eta.setVisible(False)

        self.vision_worker = VisionWorker(
            camera_index=0,
            video_path=None,
            recognition_backend=self.backend,
            show_landmarks=self.demo_toggle.isChecked()
        )
        self._connect_vision_signals(self.vision_worker)
        self.vision_worker.start()
        logger.info("Live camera session started.")

    def _start_video_session(self, video_file_path: str):
        """Start offline video file analysis."""
        self._stop_vision_worker()
        self.is_video_mode = True
        self.current_video_filename = Path(video_file_path).name
        self.mode_badge.setText("ARCHIVO DE VIDEO")
        self.mode_badge.setObjectName("ModeBadgeVideo")
        self.mode_badge.setStyle(self.mode_badge.style())
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.lbl_eta.setText("ETA: calculando...")
        self.lbl_eta.setVisible(True)

        self._on_clear_clicked()

        self.vision_worker = VisionWorker(
            video_path=video_file_path,
            recognition_backend=self.backend,
            show_landmarks=self.demo_toggle.isChecked()
        )
        self._connect_vision_signals(self.vision_worker)
        self.vision_worker.video_progress.connect(self._on_video_progress)
        self.vision_worker.video_finished.connect(self._on_video_finished)
        self.vision_worker.start()
        logger.info(f"Video file session started: {video_file_path}")

    def _connect_vision_signals(self, worker: VisionWorker):
        worker.frame_ready.connect(self._on_frame_ready)
        worker.signs_confirmed.connect(self._on_signs_confirmed)
        worker.metrics_updated.connect(self._on_metrics_updated)
        worker.error_occurred.connect(self._on_vision_error)

    def _stop_vision_worker(self):
        if self.vision_worker is not None:
            self.vision_worker.stop()
            self.vision_worker.wait(2000)
            if self.vision_worker.isRunning():
                self.vision_worker.terminate()
                self.vision_worker.wait(500)
            self.vision_worker = None

    # -----------------------------------------------------------------
    # Slots & Signal Handlers
    # -----------------------------------------------------------------
    @Slot(QImage)
    def _on_frame_ready(self, q_img: QImage):
        """Render received frame preserving aspect ratio."""
        pixmap = QPixmap.fromImage(q_img)
        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled)

    @Slot(list)
    def _on_signs_confirmed(self, events: List[Dict[str, Any]]):
        """Handle newly confirmed signs from the recognition pipeline."""
        if not events:
            return

        for ev in events:
            label = ev.get("label", "")
            if label and label != "_NADA_":
                self.gloss_sequence.append(label)
                self.accumulated_events.append(ev)

        self._update_translation_and_ui()

        # Trigger auto-speak if enabled
        if self.auto_speak_toggle.isChecked():
            self._on_speak_clicked()

    def _update_translation_and_ui(self):
        """Refresh translation outputs and timeline badges."""
        if not self.gloss_sequence:
            self.lbl_es.setText("Esperando señas...")
            self.lbl_en.setText("Waiting for signs...")
            self.lbl_gloss_strip.setText("(Sin señas confirmadas)")
            self.current_es = ""
            self.current_en = ""
            self.btn_export_srt.setEnabled(False)
            self.btn_export_txt.setEnabled(False)
            return

        # Translate gloss sequence
        trans = self.translator.translate_glosses(self.gloss_sequence)
        self.current_es = trans.get("es", "")
        self.current_en = trans.get("en", "")

        self.lbl_es.setText(self.current_es)
        self.lbl_en.setText(self.current_en)

        # Update Timeline Strip
        strip_text = " → ".join(f"[{g}]" for g in self.gloss_sequence)
        self.lbl_gloss_strip.setText(strip_text)

        self.btn_export_srt.setEnabled(True)
        self.btn_export_txt.setEnabled(True)

    @Slot(float, float, int)
    def _on_metrics_updated(self, fps: float, latency_ms: float, num_hands: int):
        self.lbl_fps.setText(f"FPS: {fps:.1f}")
        self.lbl_latency.setText(f"Latencia: {latency_ms:.1f} ms")
        self.lbl_hands.setText(f"Manos: {num_hands}")

    @Slot(float, float, float, int)
    def _on_video_progress(self, progress: float, proc_fps: float, eta_sec: float, hands: int):
        pct = int(progress * 100)
        self.progress_bar.setValue(pct)
        mins = int(eta_sec // 60)
        secs = int(eta_sec % 60)
        self.lbl_eta.setText(f"Progreso: {pct}% | FPS: {proc_fps:.1f} | ETA: {mins:02d}:{secs:02d}")

    @Slot(list)
    def _on_video_finished(self, all_events: List[Dict[str, Any]]):
        self.lbl_status.setText("● Video completado")
        self.progress_bar.setValue(100)
        self.lbl_eta.setText("Análisis finalizado")
        QMessageBox.information(
            self,
            "Análisis de Video Finalizado",
            f"Se procesó el video con éxito.\nSe detectaron {len(all_events)} eventos de señas.\n"
            f"Traducción en Español:\n{self.current_es}\n\n"
            f"Traducción en Inglés:\n{self.current_en}"
        )

    @Slot(str)
    def _on_vision_error(self, err_msg: str):
        self.lbl_status.setText("⚠ Error de visión")
        self.lbl_status.setStyleSheet("color: #EF4444; font-weight: 600;")
        QMessageBox.warning(self, "Aviso de Visión", err_msg)

    # -----------------------------------------------------------------
    # User Action Buttons & Controls
    # -----------------------------------------------------------------
    def _on_demo_toggle(self, checked: bool):
        """Toggle anatomical overlay (Mode A / Mode B)."""
        if self.vision_worker is not None:
            self.vision_worker.set_show_landmarks(checked)

    def _on_voice_combo_changed(self, index: int):
        modes = ["both", "es", "en"]
        selected_mode = modes[index] if index < len(modes) else "both"
        self.speech.set_mode(selected_mode)

    def _on_auto_speak_toggled(self, checked: bool):
        self.speech.set_auto_speak(checked)

    def _on_speak_clicked(self):
        """Vocalize the current translations asynchronously."""
        if not self.current_es and not self.current_en:
            return
        self.speech.speak(self.current_es, self.current_en)

    def _on_copy_clicked(self):
        """Copy bilingual translations to system clipboard."""
        if not self.current_es and not self.current_en:
            return
        clip_text = f"ES: {self.current_es}\nEN: {self.current_en}"
        clipboard = QApplication.clipboard()
        clipboard.setText(clip_text)

    def _on_undo_clicked(self):
        """Undo last confirmed sign."""
        if self.gloss_sequence:
            self.gloss_sequence.pop()
        if self.accumulated_events:
            self.accumulated_events.pop()
        self._update_translation_and_ui()

    def _on_clear_clicked(self):
        """Clear all recognized signs and translations."""
        self.gloss_sequence.clear()
        self.accumulated_events.clear()
        self.backend.reset()
        self._update_translation_and_ui()

    def _on_open_video_clicked(self):
        """Open file dialog to select a video for translation."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar video para traducir",
            "",
            "Archivos de Video (*.mp4 *.avi *.mov *.mkv *.wmv);;Todos los archivos (*.*)"
        )
        if file_path:
            self._start_video_session(file_path)

    def _on_live_camera_clicked(self):
        """Switch back to live webcam mode."""
        self._start_camera_session()

    def _on_export_srt_clicked(self):
        """Export SRT subtitles to file."""
        if not self.accumulated_events and not self.current_es:
            return

        default_name = f"subtitulos_{Path(self.current_video_filename or 'sesion').stem}.srt"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar subtítulos SRT",
            default_name,
            "Archivos SubRip (*.srt)"
        )
        if save_path:
            content = create_srt_content(
                self.accumulated_events,
                self.current_es,
                self.current_en
            )
            export_srt(save_path, content)
            QMessageBox.information(self, "Exportación Exitosa", f"Subtítulos guardados en:\n{save_path}")

    def _on_export_txt_clicked(self):
        """Export structured TXT transcript to file."""
        if not self.accumulated_events and not self.current_es:
            return

        default_name = f"transcripcion_{Path(self.current_video_filename or 'sesion').stem}.txt"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar transcripción TXT",
            default_name,
            "Archivos de Texto (*.txt)"
        )
        if save_path:
            content = create_transcription_txt(
                self.accumulated_events,
                self.current_es,
                self.current_en,
                source_name=self.current_video_filename or "Cámara en Vivo"
            )
            Path(save_path).write_text(content, encoding="utf-8")
            QMessageBox.information(self, "Exportación Exitosa", f"Transcripción guardada en:\n{save_path}")

    def closeEvent(self, event):
        """Clean up threads and engines on application exit."""
        self._stop_vision_worker()
        self.speech.stop()
        event.accept()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SLT Bilingual Core")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
