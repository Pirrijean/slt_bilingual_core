"""Dataset Release Manager screen building immutable release manifests."""

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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import ConsentPurpose
from slt_corpus.release import DatasetReleaseManager, ReleaseError


class ReleaseScreen(QWidget):
    """Screen for building, gating, and reviewing immutable dataset releases."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Dataset Release Manager & Governance Gating")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        desc = QLabel(
            "Constructs immutable release manifests (dataset_release.json). Enforces strict governance: "
            "releases with commercial scope are rejected if any participant lacks commercial training authorization."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # Form
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #1a2332; border: 1px solid #23354d; border-radius: 8px; padding: 16px; }"
        )
        flayout = QVBoxLayout(frame)
        flayout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Dataset ID:"))
        self.input_dataset_id = QLineEdit("lsc-continuous")
        self.input_dataset_id.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row1.addWidget(self.input_dataset_id)

        row1.addWidget(QLabel("Version:"))
        self.input_version = QLineEdit("0.1.0")
        self.input_version.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row1.addWidget(self.input_version)

        row1.addWidget(QLabel("Usage Scope:"))
        self.combo_scope = QComboBox()
        self.combo_scope.addItems([
            ConsentPurpose.INTERNAL_RESEARCH.value,
            ConsentPurpose.NONCOMMERCIAL_TRAINING.value,
            ConsentPurpose.COMMERCIAL_TRAINING.value,
        ])
        self.combo_scope.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row1.addWidget(self.combo_scope)
        flayout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Splits JSON:"))
        self.input_splits_json = QLineEdit("data/releases/splits_draft.json")
        self.input_splits_json.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row2.addWidget(self.input_splits_json)

        row2.addWidget(QLabel("Output Directory:"))
        self.input_out_dir = QLineEdit("data/releases/lsc_continuous_0_1_0")
        self.input_out_dir.setStyleSheet("background-color: #131c28; color: #fff; padding: 6px;")
        row2.addWidget(self.input_out_dir)
        flayout.addLayout(row2)

        layout.addWidget(frame)

        btn_build = QPushButton("Build & Gate Dataset Release")
        btn_build.setStyleSheet("background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 10px 16px;")
        btn_build.clicked.connect(self._build_release)
        layout.addWidget(btn_build)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(
            "QTextEdit { background-color: #131c28; border: 1px solid #23354d; border-radius: 6px; color: #e2e8f0; font-family: monospace; padding: 12px; }"
        )
        layout.addWidget(self.console)

    def _build_release(self) -> None:
        splits_path = Path(self.input_splits_json.text().strip())
        out_dir = Path(self.input_out_dir.text().strip())

        if not splits_path.is_file():
            QMessageBox.warning(self, "Missing Splits", f"Splits file not found: {splits_path}")
            return

        try:
            splits_data = json.loads(splits_path.read_text(encoding="utf-8"))
            split_members = splits_data.get("splits", splits_data)
            scope = ConsentPurpose(self.combo_scope.currentText())

            manager = DatasetReleaseManager(self.catalog, storage_root="data/private")
            release = manager.build_release(
                dataset_id=self.input_dataset_id.text().strip(),
                dataset_version=self.input_version.text().strip(),
                profile_id="lsc",
                task="continuous_sign_recognition",
                corpus_version="0.1.0",
                annotation_schema_version="1.0.0",
                usage_scope=scope,
                split_members=split_members,
                output_dir=out_dir,
            )

            msg = (
                f"=== DATASET RELEASE CREATED ===\n"
                f"Release ID: {release.release_id}\n"
                f"Scope: {release.usage_scope.value}\n"
                f"License Review: {release.license_review_status}\n"
                f"Recordings Included: {len(release.source_recording_ids)}\n"
                f"Manifest Path: {out_dir / 'dataset_release.json'}\n"
            )
            self.console.setText(msg)
            QMessageBox.information(self, "Release Created", f"Successfully built release {release.release_id}")
        except ReleaseError as re:
            err = f"=== RELEASE GATING FAILED ===\n{re}"
            self.console.setText(err)
            QMessageBox.critical(self, "Release Blocked", str(re))
        except Exception as exc:
            self.console.setText(f"Error: {exc}")
            QMessageBox.critical(self, "Error", str(exc))
