"""Adjudication screen for resolving linguistic annotation disputes and consensus review."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
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
from slt_corpus.domain import AnnotationStatus
from slt_studio.services.adjudication_service import AdjudicationService


class AdjudicationScreen(QWidget):
    """Linguistic adjudication workspace for resolving conflicting or pending annotations."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self.service = AdjudicationService(catalog)
        self._selected_ann_id: str | None = None
        self._selected_rec_id: str | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Linguistic Adjudication & Consensus Review")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        desc = QLabel(
            "Resolves annotation discrepancies between independent reviewers. "
            "Adjudicated annotations establish the authoritative ground truth for LSC recognition models."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(desc)
        header.addLayout(title_box)

        btn_refresh = QPushButton("Refresh Table")
        btn_refresh.setStyleSheet(
            "background-color: #1a2332; border: 1px solid #23354d; color: #e2e8f0; padding: 6px 14px; border-radius: 4px;"
        )
        btn_refresh.clicked.connect(self.refresh)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # Main Table of pending adjudications
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Annotation ID", "Recording ID", "Tier ID", "Current Value", "Status", "Rev"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #1a2332; border: 1px solid #23354d; border-radius: 6px; color: #e2e8f0; }"
            "QHeaderView::section { background-color: #131c28; color: #94a3b8; padding: 6px; border: none; }"
        )
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        layout.addWidget(self.table)

        # Adjudication Control Panel
        panel = QFrame()
        panel.setStyleSheet("background-color: #131c28; border: 1px solid #1a2332; border-radius: 6px; padding: 12px;")
        p_layout = QVBoxLayout(panel)
        p_layout.setSpacing(10)

        p_title = QLabel("Adjudication Decision")
        p_title.setStyleSheet("font-weight: bold; color: #00e5ff; font-size: 14px;")
        p_layout.addWidget(p_title)

        form = QHBoxLayout()
        self.lbl_target = QLabel("Select an annotation from above")
        self.lbl_target.setStyleSheet("color: #cbd5e1; font-weight: bold; min-width: 240px;")
        form.addWidget(self.lbl_target)

        self.input_value = QLineEdit()
        self.input_value.setPlaceholderText("Enter authoritative adjudicated gloss / value")
        self.input_value.setStyleSheet(
            "background-color: #1a2332; border: 1px solid #23354d; color: #fff; padding: 6px; border-radius: 4px;"
        )
        form.addWidget(self.input_value)

        self.combo_status = QComboBox()
        self.combo_status.addItems(["adjudicated", "approved", "rejected"])
        self.combo_status.setStyleSheet(
            "background-color: #1a2332; border: 1px solid #23354d; color: #fff; padding: 6px;"
        )
        form.addWidget(self.combo_status)

        btn_apply = QPushButton("Apply Decision")
        btn_apply.setStyleSheet(
            "background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 6px 16px; border-radius: 4px;"
        )
        btn_apply.clicked.connect(self._apply_decision)
        form.addWidget(btn_apply)

        btn_approve_take = QPushButton("Approve Entire Recording")
        btn_approve_take.setStyleSheet(
            "background-color: #10b981; color: #0f141c; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
        )
        btn_approve_take.clicked.connect(self._approve_entire_recording)
        form.addWidget(btn_approve_take)

        p_layout.addLayout(form)
        layout.addWidget(panel)

    def refresh(self) -> None:
        """Reload annotations currently awaiting review or adjudication."""
        pending = self.service.get_pending_adjudications()
        self.table.setRowCount(len(pending))
        for row, ann in enumerate(pending):
            self.table.setItem(row, 0, QTableWidgetItem(ann.annotation_id))
            self.table.setItem(row, 1, QTableWidgetItem(ann.recording_id))
            self.table.setItem(row, 2, QTableWidgetItem(ann.tier_id))
            self.table.setItem(row, 3, QTableWidgetItem(ann.value))
            self.table.setItem(row, 4, QTableWidgetItem(ann.status.value))
            self.table.setItem(row, 5, QTableWidgetItem(str(ann.revision)))

    def _on_table_selection(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        ann_id_item = self.table.item(row, 0)
        rec_id_item = self.table.item(row, 1)
        val_item = self.table.item(row, 3)

        if ann_id_item and rec_id_item and val_item:
            self._selected_ann_id = ann_id_item.text()
            self._selected_rec_id = rec_id_item.text()
            self.lbl_target.setText(f"Target: {self._selected_ann_id[:16]}... (Take: {self._selected_rec_id})")
            self.input_value.setText(val_item.text())

    def _apply_decision(self) -> None:
        if not self._selected_ann_id:
            QMessageBox.warning(self, "No Selection", "Please select an annotation to adjudicate.")
            return

        new_val = self.input_value.text().strip()
        if not new_val:
            QMessageBox.warning(self, "Empty Value", "Adjudicated value cannot be empty.")
            return

        status_str = self.combo_status.currentText()
        status_enum = AnnotationStatus(status_str)

        try:
            self.service.adjudicate_annotation(
                annotation_id=self._selected_ann_id,
                adjudicated_value=new_val,
                new_status=status_enum,
            )
            QMessageBox.information(self, "Success", f"Annotation {self._selected_ann_id} adjudicated as {status_str}.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to adjudicate annotation: {exc}")

    def _approve_entire_recording(self) -> None:
        if not self._selected_rec_id:
            QMessageBox.warning(self, "No Recording", "Please select an annotation to identify the target recording.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Batch Approval",
            f"Are you sure you want to approve all annotations for recording {self._selected_rec_id!r}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.service.approve_recording_annotations(self._selected_rec_id)
                QMessageBox.information(
                    self, "Approved", f"All annotations for {self._selected_rec_id} approved successfully."
                )
                self.refresh()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to approve recording: {exc}")
