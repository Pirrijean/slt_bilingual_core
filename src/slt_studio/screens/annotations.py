"""Annotation Manager screen integrating ELAN .eaf imports."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import AnnotationDocument, AnnotationStatus
from slt_corpus.elan import EAFImportError, import_eaf, to_slt_annotations


class AnnotationsScreen(QWidget):
    """Screen for managing linguistic annotation documents and ELAN synchronization."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Linguistic Annotation & ELAN Integration")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        desc = QLabel(
            "Imports and synchronizes ELAN (.eaf v3.0) documents. Converts millisecond slots into exact nanoseconds "
            "(t_ns = t_ms * 10^6) while maintaining hierarchical tier relationships."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # Import form
        form = QHBoxLayout()
        form.setSpacing(10)

        self.input_doc_id = QLineEdit()
        self.input_doc_id.setPlaceholderText("Document ID (e.g. doc_001)")
        self.input_doc_id.setStyleSheet("background-color: #1a2332; border: 1px solid #23354d; color: #fff; padding: 6px;")
        form.addWidget(self.input_doc_id)

        self.input_rec_id = QLineEdit()
        self.input_rec_id.setPlaceholderText("Target Recording ID")
        self.input_rec_id.setStyleSheet("background-color: #1a2332; border: 1px solid #23354d; color: #fff; padding: 6px;")
        form.addWidget(self.input_rec_id)

        btn_browse = QPushButton("Import ELAN .eaf...")
        btn_browse.setStyleSheet("background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 6px 14px;")
        btn_browse.clicked.connect(self._import_eaf_dialog)
        form.addWidget(btn_browse)

        layout.addLayout(form)

        # Annotations table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Annotation ID", "Tier ID", "Start (ms)", "End (ms)", "Value", "Quality"
        ])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #1a2332; border: 1px solid #23354d; border-radius: 6px; color: #e2e8f0; }"
            "QHeaderView::section { background-color: #131c28; color: #94a3b8; padding: 6px; border: none; }"
        )
        layout.addWidget(self.table)

    def _import_eaf_dialog(self) -> None:
        doc_id = self.input_doc_id.text().strip()
        rec_id = self.input_rec_id.text().strip()

        if not doc_id or not rec_id:
            QMessageBox.warning(self, "Missing Fields", "Please supply both Document ID and Recording ID.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ELAN EAF File", "", "ELAN Files (*.eaf);;XML Files (*.xml)"
        )
        if not file_path:
            return

        try:
            records = import_eaf(file_path)
            now_utc = datetime.now(UTC).isoformat()
            doc = AnnotationDocument(
                document_id=doc_id,
                recording_id=rec_id,
                schema_version="1.0.0",
                eaf_source_path=None,
                created_at_utc=now_utc,
                status=AnnotationStatus.DRAFT,
            )
            annotations = to_slt_annotations(records, document_id=doc_id, recording_id=rec_id)

            self.catalog.add_annotation_document(doc)
            self.catalog.add_annotations(annotations)

            # Display in table
            self.table.setRowCount(len(annotations))
            for row, ann in enumerate(annotations):
                self.table.setItem(row, 0, QTableWidgetItem(ann.annotation_id))
                self.table.setItem(row, 1, QTableWidgetItem(ann.tier_id))
                start_text = f"{ann.start_ns / 1_000_000:.1f}" if ann.start_ns is not None else "-"
                end_text = f"{ann.end_ns / 1_000_000:.1f}" if ann.end_ns is not None else "-"
                self.table.setItem(row, 2, QTableWidgetItem(start_text))
                self.table.setItem(row, 3, QTableWidgetItem(end_text))
                self.table.setItem(row, 4, QTableWidgetItem(ann.value))
                self.table.setItem(row, 5, QTableWidgetItem(ann.boundary_quality.value))

            QMessageBox.information(
                self, "Import Successful", f"Imported {len(annotations)} annotations into document {doc_id}."
            )
        except EAFImportError as eie:
            QMessageBox.critical(self, "EAF Import Error", str(eie))
        except Exception as exc:
            QMessageBox.critical(self, "Database / Ingestion Error", str(exc))
