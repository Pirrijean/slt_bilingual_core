"""Corpus Dashboard screen presenting telemetry, coverage, and governance stats."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from slt_corpus.audit import CorpusAuditor
from slt_corpus.catalog import CorpusCatalog


class DashboardScreen(QWidget):
    """Corpus overview dashboard screen."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self.auditor = CorpusAuditor(catalog)

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Corpus Overview & Telemetry")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)

        header_layout.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(
            "background-color: #00e5ff; color: #0f141c; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px;"
        )
        refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)

        # KPI Metric Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_participants = self._create_card("Participants", "0")
        self.card_recordings = self._create_card("Total Takes", "0")
        self.card_duration = self._create_card("Duration", "0.00s")
        self.card_consents = self._create_card("Active Consents", "0")

        cards_layout.addWidget(self.card_participants)
        cards_layout.addWidget(self.card_recordings)
        cards_layout.addWidget(self.card_duration)
        cards_layout.addWidget(self.card_consents)
        layout.addLayout(cards_layout)

        # Quarantined External Datasets Section
        section_lbl = QLabel("Quarantined Research Datasets")
        section_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8; margin-top: 12px;")
        layout.addWidget(section_lbl)

        self.table_quarantine = QTableWidget(0, 4)
        self.table_quarantine.setHorizontalHeaderLabels(["Resource ID", "Name", "Commercial Status", "Decision"])
        self.table_quarantine.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_quarantine.setStyleSheet(
            "QTableWidget { background-color: #1a2332; border: 1px solid #23354d; border-radius: 6px; color: #e2e8f0; }"
            "QHeaderView::section { background-color: #131c28; color: #94a3b8; padding: 6px; border: none; }"
        )
        layout.addWidget(self.table_quarantine)

    def _create_card(self, title: str, initial_val: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #1a2332; border: 1px solid #23354d; border-radius: 8px; padding: 12px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 12px; text-transform: uppercase;")
        lbl_val = QLabel(initial_val)
        lbl_val.setObjectName("val")
        lbl_val.setStyleSheet("color: #00e5ff; font-size: 24px; font-weight: bold;")

        card_layout.addWidget(lbl_title)
        card_layout.addWidget(lbl_val)
        return card

    def refresh(self) -> None:
        """Fetch latest statistics and update view."""
        report = self.auditor.generate_audit_report("corpus/lsc/documentation/external_datasets.json")
        summary = report["summary"]
        gov = report["governance"]

        lbl = self.card_participants.findChild(QLabel, "val")
        if lbl:
            lbl.setText(str(summary["total_participants"]))

        lbl = self.card_recordings.findChild(QLabel, "val")
        if lbl:
            orig = summary["original_recordings"]
            aug = summary["augmented_recordings"]
            lbl.setText(f"{summary['total_recordings']} ({orig} orig / {aug} aug)")

        lbl = self.card_duration.findChild(QLabel, "val")
        if lbl:
            lbl.setText(f"{summary['total_duration_seconds']:.1f}s")

        lbl = self.card_consents.findChild(QLabel, "val")
        if lbl:
            lbl.setText(f"{gov['active_consents']} active ({gov['revoked_consents']} revoked)")

        # Populate quarantine table
        resources = report.get("external_datasets_quarantined", [])
        self.table_quarantine.setRowCount(len(resources))
        for row, r in enumerate(resources):
            self.table_quarantine.setItem(row, 0, QTableWidgetItem(r.get("resource_id", "")))
            self.table_quarantine.setItem(row, 1, QTableWidgetItem(r.get("name", "")))
            self.table_quarantine.setItem(row, 2, QTableWidgetItem(r.get("commercial_use_status", "")))
            item = QTableWidgetItem(r.get("decision", ""))
            item.setForeground(Qt.GlobalColor.yellow)
            self.table_quarantine.setItem(row, 3, item)
