#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: UI Components Module.
Implements the 4 pillars:
1. Real-time visual interaction & recognition (Clean screen by default, optional demo overlays).
2. Bilingual translation & subtitles (Live subtitles & Video file analysis with SRT export).
3. Speech synthesis communication controls (Spanish, English, Both, Auto-speak).
4. Discreet Cleanmeter performance telemetry.
"""
from typing import List, Optional, Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QSizePolicy, QProgressBar, QCheckBox,
    QFileDialog, QMessageBox, QApplication
)
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PySide6.QtCore import Qt, Signal, QSize

from slt.interaction import SignEvent, InteractionState
from slt.language import generate_srt, generate_transcription_txt
from slt.ui.theme import (
    GRAPHITE, SLATE, SLATE_LIGHT, TEAL, MIST, MUTED,
    AMBER, EMERALD, CRIMSON
)

class PerceptionStage(QFrame):
    """
    Primary video viewport.
    Modo A (Pantalla Limpia, Default): Clean video with subtle status badge.
    Modo B (Modo Demostración): Anatomical 21 landmarks, connections and sign pills.
    """
    visualization_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("stageContainer")
        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._pixmap_clean: Optional[QPixmap] = None
        self._pixmap_annotated: Optional[QPixmap] = None
        self.visualization_enabled: bool = False  # Modo A: Pantalla Limpia por defecto

        self._status_text = "Reconocimiento activo · Cámara funcionando"
        self._status_color = EMERALD
        self._current_gloss = ""
        self._confidence = 0.0
        self._candidate_progress = 0.0
        self._num_hands = 0
        self._source_name = "Cámara"

    def set_visualization_enabled(self, enabled: bool):
        """Toggle anatomical overlay on/off without interrupting recognition."""
        self.visualization_enabled = bool(enabled)
        self.visualization_toggled.emit(self.visualization_enabled)
        self.update()

    def set_frames(self, clean_qimg: QImage, annotated_qimg: Optional[QImage] = None):
        """Update viewport with clean and optionally annotated frame."""
        self._pixmap_clean = QPixmap.fromImage(clean_qimg)
        if annotated_qimg is not None:
            self._pixmap_annotated = QPixmap.fromImage(annotated_qimg)
        else:
            self._pixmap_annotated = self._pixmap_clean
        self.update()

    def update_interaction_state(
        self,
        state: InteractionState,
        gloss: str = "",
        conf: float = 0.0,
        num_hands: int = 0,
        source_name: str = "Cámara"
    ):
        self._current_gloss = gloss
        self._confidence = conf
        self._num_hands = num_hands
        self._source_name = source_name

        if state == InteractionState.IDLE:
            self._status_text = f"Reconocimiento activo · {self._source_name} en espera"
            self._status_color = MUTED
        elif state == InteractionState.TRACKING:
            self._status_text = f"Reconocimiento activo · {self._source_name} funcionando"
            self._status_color = EMERALD
        elif state == InteractionState.CANDIDATE:
            self._status_text = f"Analizando seña · {gloss}"
            self._status_color = AMBER
        elif state == InteractionState.CONFIRMED:
            self._status_text = f"Seña confirmada · {gloss}"
            self._status_color = TEAL
        elif state == InteractionState.WAITING_RELEASE:
            self._status_text = "Seña registrada · Esperando siguiente seña"
            self._status_color = EMERALD

        self.update()

    def set_candidate_progress(self, gloss: str, progress: float):
        self._candidate_progress = progress
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(GRAPHITE))

        # Select frame according to Mode A (Clean) vs Mode B (Demo)
        active_pixmap = self._pixmap_annotated if (self.visualization_enabled and self._pixmap_annotated) else self._pixmap_clean

        if active_pixmap and not active_pixmap.isNull():
            scaled = active_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.setPen(QColor(MUTED))
            painter.drawText(self.rect(), Qt.AlignCenter, "Iniciando señal de video...")

        # -------------------------------------------------------------
        # MODO A: PANTALLA LIMPIA (Default)
        # -------------------------------------------------------------
        if not self.visualization_enabled:
            # Subtle discreet status badge at the bottom-left
            painter.setBrush(QColor(16, 24, 32, 200))
            painter.setPen(QColor(27, 48, 59))
            badge_rect = (16, self.height() - 42, 280, 26)
            painter.drawRoundedRect(*badge_rect, 5, 5)

            # Pulsing green dot
            painter.setBrush(QColor(self._status_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(26, self.height() - 33, 8, 8)

            painter.setPen(QColor(MIST))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            painter.drawText(40, self.height() - 24, self._status_text)
            return

        # -------------------------------------------------------------
        # MODO B: VISUALIZACIÓN DE RECONOCIMIENTO (Modo Demostración)
        # -------------------------------------------------------------
        # Top-Left Pill: Live Telemetry
        painter.setBrush(QColor(16, 24, 32, 220))
        painter.setPen(QColor(TEAL))
        painter.drawRoundedRect(16, 16, 230, 32, 6, 6)

        painter.setBrush(QColor(TEAL))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(28, 28, 8, 8)

        painter.setPen(QColor(MIST))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(44, 36, "VISUALIZACIÓN ACTIVA · DEMO")

        # Top-Right Pill: Active Sign & Confidence
        if self._current_gloss and self._current_gloss != "_NADA_":
            sign_text = f"SEÑA: {self._current_gloss} ({int(self._confidence * 100)}%)"
            painter.setBrush(QColor(16, 24, 32, 230))
            painter.setPen(QColor(TEAL))
            painter.drawRoundedRect(self.width() - 216, 16, 200, 32, 6, 6)

            painter.setPen(QColor(TEAL))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(self.width() - 204, 37, sign_text)

        # Bottom-Left Pill: Tracking status
        painter.setBrush(QColor(16, 24, 32, 210))
        painter.setPen(QColor(SLATE_LIGHT))
        painter.drawRoundedRect(16, self.height() - 44, 250, 28, 5, 5)

        painter.setBrush(QColor(EMERALD if self._num_hands > 0 else MUTED))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(26, self.height() - 34, 8, 8)

        painter.setPen(QColor(MIST))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        tracking_lbl = f"Hand tracking · ● {'ACTIVE' if self._num_hands > 0 else 'IDLE'} ({self._num_hands} manos)"
        painter.drawText(40, self.height() - 25, tracking_lbl)

        # Candidate Quorum Progress Bar
        if self._candidate_progress > 0.05:
            bar_w = int((self.width() - 64) * self._candidate_progress)
            painter.setBrush(QColor(16, 24, 32, 180))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(32, self.height() - 14, self.width() - 64, 6, 3, 3)

            painter.setBrush(QColor(TEAL))
            painter.drawRoundedRect(32, self.height() - 14, bar_w, 6, 3, 3)


class SignTimelineWidget(QFrame):
    """
    Interactive horizontal ribbon displaying the sequence of confirmed SignEvents.
    Users can inspect duration, timestamps, and click chips to remove false detections.
    """
    event_deleted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timelineContainer")
        self.setFixedHeight(68)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 6, 12, 6)
        self._layout.setSpacing(10)

        self._title = QLabel("SECUENCIA")
        self._title.setObjectName("sectionTitle")
        self._title.setFixedWidth(85)
        self._layout.addWidget(self._title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background: transparent; border: none;")

        self._chips_container = QWidget()
        self._chips_container.setStyleSheet("background: transparent;")
        self._chips_layout = QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(8)
        self._chips_layout.addStretch()

        self._scroll.setWidget(self._chips_container)
        self._layout.addWidget(self._scroll)

    def set_events(self, events: List[SignEvent]):
        while self._chips_layout.count() > 1:
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for ev in events:
            chip_btn = QPushButton(f"{ev.label} · {ev.duration_seconds:.1f}s  ✕")
            chip_btn.setObjectName("timelineChip")
            chip_btn.setToolTip(f"Marca {ev.formatted_time}. Clic para descartar.")
            chip_btn.clicked.connect(lambda _, eid=ev.event_id: self.event_deleted.emit(eid))
            self._chips_layout.insertWidget(self._chips_layout.count() - 1, chip_btn)


class LanguageOutputCard(QFrame):
    """
    Protagonist bilingual subtitle display.
    Presents simultaneous Spanish and English translations,
    one-click clipboard copy, and speech playback options.
    """
    copy_requested = Signal()
    speak_requested = Signal()
    auto_speak_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header with actions
        header_row = QHBoxLayout()
        title = QLabel("SUBTÍTULOS BILINGÜES")
        title.setObjectName("sectionTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        self.copy_btn = QPushButton("📋 Copiar traducción")
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        header_row.addWidget(self.copy_btn)

        layout.addLayout(header_row)

        # Spanish section
        es_row = QHBoxLayout()
        es_tag = QLabel("ESPAÑOL")
        es_tag.setObjectName("subtitleLangTag")
        es_row.addWidget(es_tag)
        es_row.addStretch()
        layout.addLayout(es_row)

        self.es_label = QLabel("Realiza señas frente a la cámara...")
        self.es_label.setObjectName("subtitleText")
        self.es_label.setWordWrap(True)
        layout.addWidget(self.es_label)

        # Subtle divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background-color: {SLATE_LIGHT}; max-height: 1px;")
        layout.addWidget(divider)

        # English section
        en_row = QHBoxLayout()
        en_tag = QLabel("ENGLISH")
        en_tag.setObjectName("subtitleLangTag")
        en_row.addWidget(en_tag)
        en_row.addStretch()
        layout.addLayout(en_row)

        self.en_label = QLabel("Perform signs in front of the camera...")
        self.en_label.setObjectName("subtitleText")
        self.en_label.setWordWrap(True)
        layout.addWidget(self.en_label)

        layout.addStretch()

        # Communication & Speech Bar
        comm_bar = QHBoxLayout()
        self.auto_speak_cb = QCheckBox("Reproducción automática de voz")
        self.auto_speak_cb.setStyleSheet(f"color: {MIST}; font-size: 12px;")
        self.auto_speak_cb.toggled.connect(self.auto_speak_toggled.emit)
        comm_bar.addWidget(self.auto_speak_cb)
        comm_bar.addStretch()

        self.speak_btn = QPushButton("🗣️ Pronunciar ahora (Espacio)")
        self.speak_btn.setObjectName("primaryActionBtn")
        self.speak_btn.clicked.connect(self.speak_requested.emit)
        comm_bar.addWidget(self.speak_btn)

        layout.addLayout(comm_bar)

    def set_translations(self, es_text: str, en_text: str):
        self.es_label.setText(es_text.strip() or "...")
        self.en_label.setText(en_text.strip() or "...")

    def _on_copy_clicked(self):
        es = self.es_label.text().strip()
        en = self.en_label.text().strip()
        clip_text = f"Español: {es}\nEnglish: {en}"
        QApplication.clipboard().setText(clip_text)
        self.copy_btn.setText("✓ ¡Copiado!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 Copiar traducción"))
        self.copy_requested.emit()


class VideoAnalysisWidget(QFrame):
    """
    Dedicated video file analysis tool (Local Video Translation).
    Feeds local video files (MP4, AVI, MOV) through the exact same SLT recognition engine.
    Shows processing progress, timestamps, and exports transcripts and SRT subtitles.
    """
    file_selected = Signal(str)
    start_analysis_requested = Signal(str)
    stop_analysis_requested = Signal()
    speak_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header
        top_row = QHBoxLayout()
        title = QLabel("TRADUCCIÓN DE VIDEO LOCAL (MP4)")
        title.setObjectName("sectionTitle")
        top_row.addWidget(title)
        top_row.addStretch()
        layout.addLayout(top_row)

        # File picker row
        file_row = QHBoxLayout()
        self.select_file_btn = QPushButton("📁 Seleccionar archivo...")
        self.select_file_btn.clicked.connect(self._select_file)
        file_row.addWidget(self.select_file_btn)

        self.file_label = QLabel("Ningún archivo seleccionado (.mp4, .avi, .mov)")
        self.file_label.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        file_row.addWidget(self.file_label, stretch=1)

        self.run_btn = QPushButton("▶ Analizar Video")
        self.run_btn.setObjectName("primaryActionBtn")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._on_run_clicked)
        file_row.addWidget(self.run_btn)

        self.stop_btn = QPushButton("■ Detener")
        self.stop_btn.setObjectName("dangerActionBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_analysis_requested.emit)
        file_row.addWidget(self.stop_btn)

        layout.addLayout(file_row)

        # Progress Section
        prog_row = QVBoxLayout()
        prog_row.setSpacing(4)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: {GRAPHITE}; border-radius: 4px; border: 1px solid {SLATE_LIGHT}; text-align: center; }}
            QProgressBar::chunk {{ background: {TEAL}; border-radius: 3px; }}
        """)
        self.progress_bar.setValue(0)
        prog_row.addWidget(self.progress_bar)

        self.progress_text = QLabel("Listo para analizar video.")
        self.progress_text.setObjectName("telemetryText")
        prog_row.addWidget(self.progress_text)
        layout.addLayout(prog_row)

        # Results Container
        res_frame = QFrame()
        res_frame.setStyleSheet(f"background-color: {SLATE_LIGHT}; border-radius: 8px; padding: 10px;")
        res_layout = QVBoxLayout(res_frame)
        res_layout.setContentsMargins(10, 8, 10, 8)
        res_layout.setSpacing(8)

        res_title = QLabel("RESULTADO DEL ANÁLISIS")
        res_title.setObjectName("sectionTitle")
        res_layout.addWidget(res_title)

        # Timecoded signs sequence
        self.sequence_label = QLabel("Marcas de tiempo: Esperando inicio de procesamiento...")
        self.sequence_label.setWordWrap(True)
        self.sequence_label.setStyleSheet(f"color: {MIST}; font-family: monospace; font-size: 12px;")
        res_layout.addWidget(self.sequence_label)

        # Consolidated translations
        self.res_es = QLabel("Español: -")
        self.res_es.setWordWrap(True)
        self.res_es.setStyleSheet(f"color: {MIST}; font-weight: bold; font-size: 13px;")
        res_layout.addWidget(self.res_es)

        self.res_en = QLabel("English: -")
        self.res_en.setWordWrap(True)
        self.res_en.setStyleSheet(f"color: {TEAL}; font-weight: bold; font-size: 13px;")
        res_layout.addWidget(self.res_en)

        layout.addWidget(res_frame)

        # Export Actions Toolbar
        export_row = QHBoxLayout()
        self.export_srt_btn = QPushButton("💾 Exportar Subtítulos (.srt)")
        self.export_srt_btn.setEnabled(False)
        self.export_srt_btn.clicked.connect(self._export_srt)
        export_row.addWidget(self.export_srt_btn)

        self.export_txt_btn = QPushButton("📄 Exportar Transcripción (.txt)")
        self.export_txt_btn.setEnabled(False)
        self.export_txt_btn.clicked.connect(self._export_txt)
        export_row.addWidget(self.export_txt_btn)

        export_row.addStretch()

        self.speak_res_btn = QPushButton("🗣️ Pronunciar Resultado")
        self.speak_res_btn.setEnabled(False)
        self.speak_res_btn.clicked.connect(self._speak_result)
        export_row.addWidget(self.speak_res_btn)

        layout.addLayout(export_row)

        self._selected_path = ""
        self._last_events: List[SignEvent] = []
        self._last_es = ""
        self._last_en = ""

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar video para analizar",
            "",
            "Archivos de video (*.mp4 *.avi *.mov *.mkv);;Todos los archivos (*.*)"
        )
        if path:
            self._selected_path = path
            self.file_label.setText(Path(path).name)
            self.run_btn.setEnabled(True)
            self.file_selected.emit(path)

    def _on_run_clicked(self):
        if self._selected_path:
            self.run_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setValue(0)
            self.progress_text.setText("Iniciando análisis por archivo...")
            self.start_analysis_requested.emit(self._selected_path)

    def update_progress(self, frame_idx: int, total_frames: int, progress_pct: float, elapsed_sec: float, fps: float):
        self.progress_bar.setValue(int(progress_pct))
        remaining = max(0.0, (total_frames - frame_idx) / max(1e-3, fps))
        self.progress_text.setText(
            f"Procesando: {progress_pct:.1f}% ({frame_idx}/{total_frames} frames) · "
            f"Velocidad: {fps:.1f} fps · Restante: ~{remaining:.1f}s"
        )

    def set_results(self, events: List[SignEvent], es_text: str, en_text: str):
        self._last_events = list(events)
        self._last_es = es_text
        self._last_en = en_text

        if events:
            seq_strs = []
            for ev in events:
                ms = int(ev.timestamp_start // 60)
                ss = int(ev.timestamp_start % 60)
                me = int(ev.timestamp_end // 60)
                se = int(ev.timestamp_end % 60)
                seq_strs.append(f"{ms:02d}:{ss:02d} – {me:02d}:{se:02d} | {ev.label}")
            self.sequence_label.setText("  ▶  ".join(seq_strs))
        else:
            self.sequence_label.setText("No se identificaron señas concluyentes.")

        self.res_es.setText(f"Español: {es_text or '...'}")
        self.res_en.setText(f"English: {en_text or '...'}")

        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.export_srt_btn.setEnabled(bool(events))
        self.export_txt_btn.setEnabled(bool(events))
        self.speak_res_btn.setEnabled(bool(es_text or en_text))

    def _export_srt(self):
        if not self._last_events:
            return
        srts = generate_srt(self._last_events, self._last_es, self._last_en)
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar subtítulos SRT",
            "subtitulos_bilingues.srt",
            "Subtítulos (*.srt)"
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(srts["bilingual"])
            QMessageBox.information(self, "Exportación exitosa", f"Subtítulos SRT guardados en:\n{save_path}")

    def _export_txt(self):
        if not self._last_events:
            return
        txt = generate_transcription_txt(self._last_events, self._last_es, self._last_en, Path(self._selected_path).name)
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte de transcripción",
            "transcripcion_slt.txt",
            "Texto plano (*.txt)"
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(txt)
            QMessageBox.information(self, "Exportación exitosa", f"Transcripción guardada en:\n{save_path}")

    def _speak_result(self):
        if self._last_es or self._last_en:
            self.speak_requested.emit(self._last_es, self._last_en)


class DiagnosticsBar(QFrame):
    """
    Discreet single-line system monitor inspired by Cleanmeter.
    Displays hardware and engine telemetry without visual clutter.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("diagnosticsBar")
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        self.src_label = QLabel("CÁMARA")
        self.src_label.setObjectName("telemetryText")
        layout.addWidget(self.src_label)

        self.fps_label = QLabel("30.0 FPS")
        self.fps_label.setObjectName("telemetryText")
        layout.addWidget(self.fps_label)

        self.latency_label = QLabel("0.0 ms")
        self.latency_label.setObjectName("telemetryText")
        layout.addWidget(self.latency_label)

        self.hands_label = QLabel("0 MANOS")
        self.hands_label.setObjectName("telemetryText")
        layout.addWidget(self.hands_label)

        layout.addStretch()

        self.model_label = QLabel("MODELO: SLT-v1.1.0")
        self.model_label.setObjectName("telemetryText")
        layout.addWidget(self.model_label)

        self.status_label = QLabel("MOTOR: ACTIVO")
        self.status_label.setObjectName("telemetryText")
        self.status_label.setStyleSheet(f"color: {TEAL}; font-weight: bold;")
        layout.addWidget(self.status_label)

    def update_camera_metrics(self, fps: float, latency_ms: float, num_hands: int):
        self.src_label.setText("CÁMARA")
        self.fps_label.setText(f"{fps:.1f} FPS")
        self.latency_label.setText(f"{latency_ms:.1f} ms")
        self.hands_label.setText(f"{num_hands} {'MANO' if num_hands == 1 else 'MANOS'}")

    def update_video_metrics(self, progress_pct: float, fps: float, num_hands: int):
        self.src_label.setText("VIDEO LOCAL")
        self.fps_label.setText(f"{fps:.1f} FPS PROC")
        self.latency_label.setText(f"{progress_pct:.0f}%")
        self.hands_label.setText(f"{num_hands} {'MANO' if num_hands == 1 else 'MANOS'}")


class SignGuideDrawer(QFrame):
    """
    Collapsible contextual drawer showing visual sign catalog (Level 2 Assistance).
    """
    def __init__(self, words_dict: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("drawerContainer")
        self.setFixedWidth(290)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("CATÁLOGO DE SEÑAS (19)")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(8)

        for gloss, entry in words_dict.items():
            card = QFrame()
            card.setStyleSheet(f"background-color: {SLATE_LIGHT}; border-radius: 6px; padding: 6px;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 6, 8, 6)
            card_layout.setSpacing(2)

            g_lbl = QLabel(f"<b>{gloss}</b> <span style='color:{TEAL};'>({entry.get('category', 'Seña')})</span>")
            guide_lbl = QLabel(entry.get("guide", ""))
            guide_lbl.setWordWrap(True)
            guide_lbl.setStyleSheet(f"color: {MUTED}; font-size: 11px;")

            card_layout.addWidget(g_lbl)
            card_layout.addWidget(guide_lbl)
            c_layout.addWidget(card)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
