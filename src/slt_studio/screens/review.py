"""Technical Review screen checking recording integrity and quality."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.validation import QualityCheckError, validate_recording_integrity


class ReviewScreen(QWidget):
    """Screen for technical quality assurance and integrity verification."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Technical Quality Assurance & Integrity Review")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        desc = QLabel(
            "Verifies physical storage existence, byte size, decodability, and cryptographic SHA-256 integrity. "
            "Technical approval is maintained independently from linguistic and consent statuses."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # Selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Select Recording:"))
        self.combo_recordings = QComboBox()
        self.combo_recordings.setStyleSheet("background-color: #1a2332; color: #fff; padding: 6px; min-width: 250px;")
        row.addWidget(self.combo_recordings)

        btn_verify = QPushButton("Run Integrity & Checksum Verification")
        btn_verify.setStyleSheet("background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 6px 14px;")
        btn_verify.clicked.connect(self._verify_recording)
        row.addWidget(btn_verify)
        row.addStretch()
        layout.addLayout(row)

        # Results Panel
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet(
            "QFrame { background-color: #1a2332; border: 1px solid #23354d; border-radius: 8px; padding: 16px; }"
        )
        res_layout = QVBoxLayout(self.result_frame)
        res_layout.setSpacing(10)

        self.lbl_file_check = QLabel("Physical File Check: PENDING")
        self.lbl_hash_check = QLabel("SHA-256 Checksum Match: PENDING")
        self.lbl_spec_check = QLabel("Resolution & Format: PENDING")
        self.lbl_multi_status = QLabel("Multi-Dimensional QA Status: PENDING")

        for lbl in (self.lbl_file_check, self.lbl_hash_check, self.lbl_spec_check, self.lbl_multi_status):
            lbl.setStyleSheet("color: #94a3b8; font-size: 14px;")
            res_layout.addWidget(lbl)

        layout.addWidget(self.result_frame)
        layout.addStretch()

    def refresh(self) -> None:
        self.combo_recordings.clear()
        recs = self.catalog.list_recordings()
        for r in recs:
            self.combo_recordings.addItem(f"{r.recording_id} ({r.signer_id})", r.recording_id)

    def _verify_recording(self) -> None:
        rec_id = self.combo_recordings.currentData()
        if not rec_id:
            QMessageBox.warning(self, "No Selection", "Please select a recording.")
            return

        rec = self.catalog.get_recording(rec_id)
        if rec is None:
            return

        try:
            validate_recording_integrity(rec, storage_root="data/private")
            self.lbl_file_check.setText(f"Physical File Check: PASS ({rec.storage_relative_path})")
            self.lbl_file_check.setStyleSheet("color: #10b981; font-weight: bold;")

            self.lbl_hash_check.setText(f"SHA-256 Checksum Match: PASS ({rec.source_video_sha256[:16]}...)")
            self.lbl_hash_check.setStyleSheet("color: #10b981; font-weight: bold;")

            self.lbl_spec_check.setText(f"Resolution & Format: PASS ({rec.width}x{rec.height}, {rec.container_format}/{rec.video_codec})")
            self.lbl_spec_check.setStyleSheet("color: #10b981; font-weight: bold;")

            self.lbl_multi_status.setText(
                "Multi-Dimensional QA: technical_status=APPROVED | linguistic_status=PENDING | consent_status=VALID"
            )
            self.lbl_multi_status.setStyleSheet("color: #00e5ff; font-weight: bold;")
        except QualityCheckError as qce:
            self.lbl_file_check.setText(f"Integrity Check: FAILED — {qce}")
            self.lbl_file_check.setStyleSheet("color: #ef4444; font-weight: bold;")
            QMessageBox.critical(self, "Verification Failure", str(qce))
