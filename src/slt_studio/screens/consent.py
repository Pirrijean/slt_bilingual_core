"""Consent Status & Revocation screen."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from slt_corpus.domain import ConsentPurpose, ConsentRecord


class ConsentScreen(QWidget):
    """Screen for inspecting, registering, and revoking participant consent."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Informed Consent & Purpose Authorization")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        desc = QLabel(
            "Every recording must be backed by an active, unrevoked consent record authorizing "
            "specific purposes. If revoked, processing is immediately blocked."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # Actions toolbar
        toolbar = QHBoxLayout()
        self.input_consent_id = QLineEdit()
        self.input_consent_id.setPlaceholderText("Consent ID (e.g. c_001)")
        self.input_consent_id.setStyleSheet("background-color: #1a2332; border: 1px solid #23354d; color: #fff; padding: 6px;")
        toolbar.addWidget(self.input_consent_id)

        self.input_signer_id = QLineEdit()
        self.input_signer_id.setPlaceholderText("Signer ID")
        self.input_signer_id.setStyleSheet("background-color: #1a2332; border: 1px solid #23354d; color: #fff; padding: 6px;")
        toolbar.addWidget(self.input_signer_id)

        btn_add = QPushButton("Grant Storage + Research")
        btn_add.setStyleSheet("background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 6px 12px;")
        btn_add.clicked.connect(self._add_sample_consent)
        toolbar.addWidget(btn_add)

        toolbar.addSpacing(16)
        btn_revoke = QPushButton("Revoke Selected")
        btn_revoke.setStyleSheet("background-color: #ef4444; color: #ffffff; font-weight: bold; padding: 6px 12px;")
        btn_revoke.clicked.connect(self._revoke_selected)
        toolbar.addWidget(btn_revoke)

        layout.addLayout(toolbar)

        # Consents Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Consent ID", "Signer ID", "Form Version", "Granted Purposes", "Signed UTC", "Revoked UTC"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #1a2332; border: 1px solid #23354d; border-radius: 6px; color: #e2e8f0; }"
            "QHeaderView::section { background-color: #131c28; color: #94a3b8; padding: 6px; border: none; }"
        )
        layout.addWidget(self.table)

    def _add_sample_consent(self) -> None:
        c_id = self.input_consent_id.text().strip()
        s_id = self.input_signer_id.text().strip()
        if not c_id or not s_id:
            QMessageBox.warning(self, "Error", "Both Consent ID and Signer ID are required.")
            return

        now_utc = datetime.now(UTC).isoformat()
        try:
            consent = ConsentRecord(
                consent_id=c_id,
                signer_id=s_id,
                form_version="1.0.0",
                signed_at_utc=now_utc,
                granted_purposes=frozenset({
                    ConsentPurpose.RECORD_AND_STORE,
                    ConsentPurpose.DERIVE_LANDMARKS,
                    ConsentPurpose.INTERNAL_RESEARCH,
                }),
                evidence_sha256="0" * 64,
            )
            self.catalog.add_consent(consent)
            self.input_consent_id.clear()
            self.input_signer_id.clear()
            self.refresh()
            QMessageBox.information(self, "Success", f"Consent {c_id} registered.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def _revoke_selected(self) -> None:
        curr_row = self.table.currentRow()
        if curr_row < 0:
            QMessageBox.warning(self, "Selection", "Select a consent row to revoke.")
            return

        item = self.table.item(curr_row, 0)
        if item is None:
            return
        c_id = item.text()
        now_utc = datetime.now(UTC).isoformat()
        self.catalog.revoke_consent(c_id, now_utc)
        self.refresh()
        QMessageBox.information(self, "Revocation", f"Consent {c_id} has been revoked at {now_utc}.")

    def refresh(self) -> None:
        participants = self.catalog.list_participants()
        self.table.setRowCount(0)
        row = 0
        for p in participants:
            c = self.catalog.get_latest_consent_for_signer(p.signer_id)
            if c is not None:
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(c.consent_id))
                self.table.setItem(row, 1, QTableWidgetItem(c.signer_id))
                self.table.setItem(row, 2, QTableWidgetItem(c.form_version))
                purps = ", ".join(p.value for p in sorted(c.granted_purposes))
                self.table.setItem(row, 3, QTableWidgetItem(purps))
                self.table.setItem(row, 4, QTableWidgetItem(c.signed_at_utc))
                rev_item = QTableWidgetItem(c.revoked_at_utc or "ACTIVE")
                if c.revoked_at_utc:
                    rev_item.setForeground(Qt.GlobalColor.red)
                else:
                    rev_item.setForeground(Qt.GlobalColor.green)
                self.table.setItem(row, 5, rev_item)
                row += 1
