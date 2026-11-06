"""Dataset Builder screen configuring machine learning task datasets."""

from __future__ import annotations

import json
from pathlib import Path

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

from slt_corpus.catalog import CorpusCatalog


class DatasetBuilderScreen(QWidget):
    """Screen for configuring task-specific dataset partitions."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Dataset Builder & Task Configuration")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        desc = QLabel(
            "Derives a dedicated machine learning dataset from cataloged recordings and verified annotations. "
            "Partitions must strictly follow Signer-Independent guidelines."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # Configuration frame
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #1a2332; border: 1px solid #23354d; border-radius: 8px; padding: 16px; }"
        )
        flayout = QVBoxLayout(frame)
        flayout.setSpacing(12)

        # Task selection
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Target ML Task:"))
        self.combo_task = QComboBox()
        self.combo_task.addItems([
            "continuous_sign_recognition",
            "isolated_sign_recognition",
            "handshape_classification",
            "sign_language_translation",
        ])
        self.combo_task.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row1.addWidget(self.combo_task)
        flayout.addLayout(row1)

        # Dataset ID & Version
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Dataset ID:"))
        self.input_dataset_id = QLineEdit("lsc-continuous")
        self.input_dataset_id.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row2.addWidget(self.input_dataset_id)

        row2.addWidget(QLabel("Version:"))
        self.input_version = QLineEdit("0.1.0")
        self.input_version.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row2.addWidget(self.input_version)
        flayout.addLayout(row2)

        # Output split file
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Export Splits Path:"))
        self.input_splits_path = QLineEdit("data/releases/splits_draft.json")
        self.input_splits_path.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row3.addWidget(self.input_splits_path)
        flayout.addLayout(row3)

        layout.addWidget(frame)

        btn_build_splits = QPushButton("Partition Signer-Independent Splits Draft")
        btn_build_splits.setStyleSheet("background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 10px 16px;")
        btn_build_splits.clicked.connect(self._generate_splits_draft)
        layout.addWidget(btn_build_splits)

        layout.addStretch()

    def _generate_splits_draft(self) -> None:
        recs = self.catalog.list_recordings()
        if not recs:
            QMessageBox.warning(self, "No Recordings", "Catalog has no recordings to partition.")
            return

        # Group recordings by signer
        signers = sorted({r.signer_id for r in recs})
        if len(signers) == 1:
            # Single signer: put all in train or warning
            splits = {"train": [r.recording_id for r in recs], "validation": [], "test": []}
        else:
            # Partition signers: ~70% train, ~15% val, ~15% test
            n_train = max(1, int(len(signers) * 0.7))
            train_signers = set(signers[:n_train])
            val_signers = set(signers[n_train : n_train + 1])

            splits = {"train": [], "validation": [], "test": []}
            for r in recs:
                if r.signer_id in train_signers:
                    splits["train"].append(r.recording_id)
                elif r.signer_id in val_signers:
                    splits["validation"].append(r.recording_id)
                else:
                    splits["test"].append(r.recording_id)

        target_file = Path(self.input_splits_path.text().strip())
        target_file.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": "1.0.0",
            "dataset_id": self.input_dataset_id.text().strip(),
            "dataset_version": self.input_version.text().strip(),
            "splits": splits,
        }
        target_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Splits Generated", f"Saved Signer-Independent partition draft to {target_file}")
