"""Recording Browser screen displaying cataloged media takes."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from slt_corpus.catalog import CorpusCatalog


class RecordingsScreen(QWidget):
    """Screen for browsing and inspecting ingested recordings."""

    def __init__(self, catalog: CorpusCatalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Ingested Recordings Browser")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        header.addWidget(title)

        header.addStretch()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Filter by recording or signer ID...")
        self.input_search.setStyleSheet("background-color: #1a2332; border: 1px solid #23354d; color: #fff; padding: 6px; width: 220px;")
        self.input_search.textChanged.connect(self._filter_rows)
        header.addWidget(self.input_search)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("background-color: #00e5ff; color: #0f141c; font-weight: bold; padding: 6px 12px;")
        btn_refresh.clicked.connect(self.refresh)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # Recordings table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Recording ID", "Session ID", "Signer ID", "Duration (s)", "Resolution", "Status", "Storage Path", "SHA-256 (Prefix)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #1a2332; border: 1px solid #23354d; border-radius: 6px; color: #e2e8f0; }"
            "QHeaderView::section { background-color: #131c28; color: #94a3b8; padding: 6px; border: none; }"
        )
        layout.addWidget(self.table)

    def refresh(self) -> None:
        recordings = self.catalog.list_recordings()
        self.table.setRowCount(len(recordings))
        for row, r in enumerate(recordings):
            self.table.setItem(row, 0, QTableWidgetItem(r.recording_id))
            self.table.setItem(row, 1, QTableWidgetItem(r.session_id))
            self.table.setItem(row, 2, QTableWidgetItem(r.signer_id))
            self.table.setItem(row, 3, QTableWidgetItem(f"{r.duration_ns / 1_000_000_000:.2f}s"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{r.width}x{r.height}"))
            self.table.setItem(row, 5, QTableWidgetItem(r.status.value))
            self.table.setItem(row, 6, QTableWidgetItem(r.storage_relative_path))
            self.table.setItem(row, 7, QTableWidgetItem(r.source_video_sha256[:16] + "..."))

    def _filter_rows(self, text: str) -> None:
        query = text.lower().strip()
        for row in range(self.table.rowCount()):
            item0 = self.table.item(row, 0)
            item2 = self.table.item(row, 2)
            rec_id = item0.text().lower() if item0 is not None else ""
            signer_id = item2.text().lower() if item2 is not None else ""
            match = query in rec_id or query in signer_id
            self.table.setRowHidden(row, not match)
