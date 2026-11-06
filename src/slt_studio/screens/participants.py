"""Participant Registry screen with pseudonym enforcement."""

from __future__ import annotations

from datetime import UTC, datetime

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
from slt_corpus.domain import CorpusValidationError, Participant


class ParticipantsScreen(QWidget):
    """Participant management screen enforcing pseudonymity."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Pseudonymous Participant Registry")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        desc = QLabel(
            "Under Colombian Law 1581 of 2012, direct personal identifiers (names, emails, cedulas) "
            "are strictly prohibited in corpus records. All signers must use pseudonymous slug IDs."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Registration form
        form_layout = QHBoxLayout()
        form_layout.setSpacing(10)

        self.input_signer_id = QLineEdit()
        self.input_signer_id.setPlaceholderText("Pseudonymous ID (e.g. signer_lsc_001)")
        self.input_signer_id.setStyleSheet(
            "background-color: #1a2332; border: 1px solid #23354d; border-radius: 4px; padding: 6px; color: #fff;"
        )
        form_layout.addWidget(self.input_signer_id)

        self.input_metadata = QLineEdit()
        self.input_metadata.setPlaceholderText('Metadata JSON (e.g. {"dialect": "bogota", "age_bracket": "20-30"})')
        self.input_metadata.setStyleSheet(
            "background-color: #1a2332; border: 1px solid #23354d; border-radius: 4px; padding: 6px; color: #fff;"
        )
        form_layout.addWidget(self.input_metadata)

        btn_add = QPushButton("Register Participant")
        btn_add.setStyleSheet(
            "background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
        )
        btn_add.clicked.connect(self._add_participant)
        form_layout.addWidget(btn_add)

        layout.addLayout(form_layout)

        # Participants table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Signer ID", "Creation Date (UTC)", "Metadata JSON"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #1a2332; border: 1px solid #23354d; border-radius: 6px; color: #e2e8f0; }"
            "QHeaderView::section { background-color: #131c28; color: #94a3b8; padding: 6px; border: none; }"
        )
        layout.addWidget(self.table)

    def _add_participant(self) -> None:
        signer_id = self.input_signer_id.text().strip()
        metadata_str = self.input_metadata.text().strip() or "{}"

        if not signer_id:
            QMessageBox.warning(self, "Validation Error", "Signer ID cannot be empty.")
            return

        now_utc = datetime.now(UTC).isoformat()
        try:
            p = Participant(
                signer_id=signer_id,
                metadata_json=metadata_str,
                created_at_utc=now_utc,
            )
            self.catalog.add_participant(p)
            self.input_signer_id.clear()
            self.input_metadata.clear()
            self.refresh()
            QMessageBox.information(self, "Success", f"Participant {signer_id} registered.")
        except CorpusValidationError as cve:
            QMessageBox.critical(self, "Privacy Invariant Error", str(cve))
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", str(exc))

    def refresh(self) -> None:
        participants = self.catalog.list_participants()
        self.table.setRowCount(len(participants))
        for row, p in enumerate(participants):
            self.table.setItem(row, 0, QTableWidgetItem(p.signer_id))
            self.table.setItem(row, 1, QTableWidgetItem(p.created_at_utc))
            self.table.setItem(row, 2, QTableWidgetItem(p.metadata_json))
