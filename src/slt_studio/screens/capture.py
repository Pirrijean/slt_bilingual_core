"""Studio Capture screen integrating session controller and video recorder."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from slt_capture.protocol import load_protocol_from_file
from slt_capture.recorder import CaptureRecorder
from slt_capture.session import CaptureSessionController
from slt_corpus.catalog import CorpusCatalog


class CaptureScreen(QWidget):
    """Screen for initiating controlled acquisition takes."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self.active_recorder: CaptureRecorder | None = None
        self.active_session_ctrl: CaptureSessionController | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Controlled Capture Studio")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        desc = QLabel(
            "Acquisition requires a verified participant with active RECORD_AND_STORE consent. "
            "Master takes are automatically hashed and ingested into content-addressed storage."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # Configuration Box
        config_frame = QFrame()
        config_frame.setStyleSheet(
            "QFrame { background-color: #1a2332; border: 1px solid #23354d; border-radius: 8px; padding: 16px; }"
        )
        cfg_layout = QVBoxLayout(config_frame)
        cfg_layout.setSpacing(12)

        # Protocol selection
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Protocol:"))
        self.combo_protocol = QComboBox()
        self.combo_protocol.addItem("continuous_v1", "corpus/lsc/capture_protocols/continuous_v1.json")
        self.combo_protocol.addItem("controlled_v1", "corpus/lsc/capture_protocols/controlled_v1.json")
        self.combo_protocol.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row1.addWidget(self.combo_protocol)
        cfg_layout.addLayout(row1)

        # Participant and operator
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Signer ID:"))
        self.input_signer = QLineEdit()
        self.input_signer.setPlaceholderText("e.g. signer_lsc_001")
        self.input_signer.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row2.addWidget(self.input_signer)

        row2.addWidget(QLabel("Operator ID:"))
        self.input_operator = QLineEdit("operator_studio_01")
        self.input_operator.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row2.addWidget(self.input_operator)
        cfg_layout.addLayout(row2)

        layout.addWidget(config_frame)

        # Status & Control Banner
        self.lbl_status = QLabel("STATUS: IDLE — AWAITING SESSION PREPARATION")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(
            "background-color: #131c28; color: #94a3b8; font-weight: bold; font-size: 14px; "
            "padding: 12px; border: 1px solid #23354d; border-radius: 6px;"
        )
        layout.addWidget(self.lbl_status)

        # Actions
        btn_layout = QHBoxLayout()
        self.btn_prep = QPushButton("Prepare Session & Check Consent")
        self.btn_prep.setStyleSheet("background-color: #3b82f6; color: #fff; font-weight: bold; padding: 10px 16px;")
        self.btn_prep.clicked.connect(self._prepare_session)
        btn_layout.addWidget(self.btn_prep)

        self.btn_record = QPushButton("Record Simulated Take (30 frames)")
        self.btn_record.setEnabled(False)
        self.btn_record.setStyleSheet("background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 10px 16px;")
        self.btn_record.clicked.connect(self._record_take)
        btn_layout.addWidget(self.btn_record)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _prepare_session(self) -> None:
        signer_id = self.input_signer.text().strip()
        operator_id = self.input_operator.text().strip() or "operator_01"
        proto_path = self.combo_protocol.currentData()

        if not signer_id:
            QMessageBox.warning(self, "Missing Signer", "Please specify a Signer ID.")
            return

        try:
            protocol = load_protocol_from_file(proto_path)
            sess_id = f"sess_{signer_id}_{int(time.time())}"
            self.active_session_ctrl = CaptureSessionController(
                catalog=self.catalog,
                session_id=sess_id,
                signer_id=signer_id,
                protocol=protocol,
                operator_id=operator_id,
            )
            self.lbl_status.setText(f"READY: Session {sess_id} prepared for {signer_id}. Consent VALID.")
            self.lbl_status.setStyleSheet(
                "background-color: #131c28; color: #10b981; font-weight: bold; font-size: 14px; "
                "padding: 12px; border: 1px solid #10b981; border-radius: 6px;"
            )
            self.btn_record.setEnabled(True)
        except Exception as exc:
            self.lbl_status.setText(f"BLOCKED: {exc}")
            self.lbl_status.setStyleSheet(
                "background-color: #131c28; color: #ef4444; font-weight: bold; font-size: 14px; "
                "padding: 12px; border: 1px solid #ef4444; border-radius: 6px;"
            )
            self.btn_record.setEnabled(False)
            QMessageBox.critical(self, "Consent / Session Gating Error", str(exc))

    def _record_take(self) -> None:
        if self.active_session_ctrl is None:
            return

        try:
            import numpy as np

            # Register session in catalog first
            self.active_session_ctrl.register_in_catalog()

            rec_id = f"rec_{self.active_session_ctrl.signer_id}_{int(time.time())}"
            recorder = CaptureRecorder(
                session_controller=self.active_session_ctrl,
                output_temp_dir="data/private/temp",
                storage_root="data/private",
            )
            recorder.start(recording_id=rec_id, width=1920, height=1080, fps=30.0)

            # Write 30 synthetic frames
            for _ in range(30):
                dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                recorder.write_frame(dummy_frame)

            recording = recorder.stop(recording_id=rec_id)
            self.lbl_status.setText(f"SUCCESS: Take {recording.recording_id} ingested into {recording.storage_relative_path}")
            self.lbl_status.setStyleSheet(
                "background-color: #131c28; color: #00e5ff; font-weight: bold; font-size: 14px; "
                "padding: 12px; border: 1px solid #00e5ff; border-radius: 6px;"
            )
            QMessageBox.information(self, "Take Ingested", f"Ingested {recording.recording_id} (SHA-256: {recording.source_video_sha256[:12]}...)")
        except Exception as exc:
            QMessageBox.critical(self, "Recording Failed", str(exc))
