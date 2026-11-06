"""Split Validation screen enforcing signer-independence and leakage protection."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.splits import (
    SplitValidationError,
    validate_group_disjoint,
    validate_no_augmentation_leakage,
)


class SplitValidationScreen(QWidget):
    """Screen for verifying that partitions have zero signer leakage or augmentation leakage."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog

        self._build_ui()

    def refresh(self) -> None:
        """Clear output console on refresh."""
        self.output_console.clear()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Split Integrity & Data Leakage Validator")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        desc = QLabel(
            "Verifies that no participant appears across multiple splits (Signer-Independent) "
            "and that every augmented variation resides strictly in the same split as its parent recording."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # File input
        row = QHBoxLayout()
        row.addWidget(QLabel("Splits JSON Path:"))
        self.input_splits = QLineEdit("data/releases/splits_draft.json")
        self.input_splits.setStyleSheet("background-color: #1a2332; border: 1px solid #23354d; color: #fff; padding: 6px;")
        row.addWidget(self.input_splits)

        btn_validate = QPushButton("Validate Splits")
        btn_validate.setStyleSheet("background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 6px 14px;")
        btn_validate.clicked.connect(self._validate_splits)
        row.addWidget(btn_validate)
        layout.addLayout(row)

        # Output console
        self.output_console = QTextEdit()
        self.output_console.setReadOnly(True)
        self.output_console.setStyleSheet(
            "QTextEdit { background-color: #131c28; border: 1px solid #23354d; border-radius: 6px; color: #e2e8f0; font-family: monospace; padding: 12px; }"
        )
        layout.addWidget(self.output_console)

    def _validate_splits(self) -> None:
        path = Path(self.input_splits.text().strip())
        if not path.is_file():
            QMessageBox.warning(self, "Not Found", f"Splits file not found: {path}")
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            splits = data.get("splits", data)

            # Build group mappings from catalog
            recs = self.catalog.list_recordings()
            signer_by_rec = {r.recording_id: r.signer_id for r in recs}
            parent_by_rec = {r.recording_id: r.parent_recording_id for r in recs}

            validate_group_disjoint(splits, signer_by_rec)
            validate_no_augmentation_leakage(splits, parent_by_rec)

            msg = (
                "=== SPLIT VALIDATION PASSED ===\n"
                "- Signer-Independent Disjointness: VERIFIED (Zero signer leakage)\n"
                "- Augmentation Lineage: VERIFIED (All derivatives co-located with parents)\n"
                f"- Splits examined: {list(splits.keys())}\n"
                f"- Total recordings partitioned: {sum(len(v) for v in splits.values())}\n"
            )
            self.output_console.setText(msg)
            QMessageBox.information(self, "Validation Passed", "Partitions are strictly disjoint and valid.")
        except SplitValidationError as sve:
            err_msg = f"=== SPLIT VALIDATION FAILED ===\nData Leakage Detected: {sve}"
            self.output_console.setText(err_msg)
            QMessageBox.critical(self, "Data Leakage Error", str(sve))
        except Exception as exc:
            self.output_console.setText(f"Error parsing splits: {exc}")
            QMessageBox.critical(self, "Error", str(exc))
