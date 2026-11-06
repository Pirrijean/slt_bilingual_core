"""Main window for SLT Dataset Studio."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from slt_corpus.catalog import CorpusCatalog
from slt_studio.screens.adjudication import AdjudicationScreen
from slt_studio.screens.annotations import AnnotationsScreen
from slt_studio.screens.builder import DatasetBuilderScreen
from slt_studio.screens.capture import CaptureScreen
from slt_studio.screens.consent import ConsentScreen
from slt_studio.screens.dashboard import DashboardScreen
from slt_studio.screens.participants import ParticipantsScreen
from slt_studio.screens.recordings import RecordingsScreen
from slt_studio.screens.release import ReleaseScreen
from slt_studio.screens.review import ReviewScreen
from slt_studio.screens.splits import SplitValidationScreen


class DatasetStudioMainWindow(QMainWindow):
    """Main window hosting navigation and stacked workspace screens."""

    def __init__(self, db_path: str | Path = "data/private/catalog.sqlite3") -> None:
        super().__init__()
        self.setWindowTitle("SLT Dataset Studio — LSC Corpus Engineering")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)

        self.catalog = CorpusCatalog(db_path)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b0f17;
            }
            QLabel {
                color: #e2e8f0;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Navigation Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0f141c;
                border-right: 1px solid #1a2332;
            }
        """)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(16, 20, 16, 20)
        s_layout.setSpacing(8)

        # App Brand
        brand = QLabel("SLT STUDIO")
        brand.setStyleSheet("font-size: 16px; font-weight: bold; letter-spacing: 2px; color: #00e5ff;")
        sub_brand = QLabel("Corpus & Datasets — LSC")
        sub_brand.setStyleSheet("font-size: 11px; color: #64748b; margin-bottom: 12px;")
        s_layout.addWidget(brand)
        s_layout.addWidget(sub_brand)

        # Navigation Buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        screens_meta = [
            ("Dashboard", 0),
            ("Participants", 1),
            ("Consent", 2),
            ("Capture", 3),
            ("Recordings", 4),
            ("Review QA", 5),
            ("Annotations", 6),
            ("Adjudication", 7),
            ("Dataset Builder", 8),
            ("Split Validator", 9),
            ("Release Manager", 10),
        ]

        self.buttons: list[QPushButton] = []
        for label, idx in screens_meta:
            btn = QPushButton(f"  {label}")
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94a3b8;
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    padding-left: 10px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #1a2332;
                    color: #f8fafc;
                }
                QPushButton:checked {
                    background-color: #1a2332;
                    color: #00e5ff;
                    font-weight: bold;
                    border-left: 3px solid #00e5ff;
                }
            """)
            btn.clicked.connect(lambda _, i=idx: self.switch_screen(i))
            self.nav_group.addButton(btn, idx)
            s_layout.addWidget(btn)
            self.buttons.append(btn)

        s_layout.addStretch()

        # Offline / Privacy Indicator
        offline_badge = QLabel("OFFLINE LOCAL STORAGE")
        offline_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        offline_badge.setStyleSheet(
            "color: #10b981; font-size: 10px; font-weight: bold; padding: 4px; "
            "border: 1px solid #10b981; border-radius: 4px;"
        )
        s_layout.addWidget(offline_badge)

        main_layout.addWidget(sidebar)

        # Right Stacked Workspaces
        self.stack = QStackedWidget()
        self.screen_dashboard = DashboardScreen(self.catalog)
        self.screen_participants = ParticipantsScreen(self.catalog)
        self.screen_consent = ConsentScreen(self.catalog)
        self.screen_capture = CaptureScreen(self.catalog)
        self.screen_recordings = RecordingsScreen(self.catalog)
        self.screen_review = ReviewScreen(self.catalog)
        self.screen_annotations = AnnotationsScreen(self.catalog)
        self.screen_adjudication = AdjudicationScreen(self.catalog)
        self.screen_builder = DatasetBuilderScreen(self.catalog)
        self.screen_splits = SplitValidationScreen(self.catalog)
        self.screen_release = ReleaseScreen(self.catalog)

        self.stack.addWidget(self.screen_dashboard)
        self.stack.addWidget(self.screen_participants)
        self.stack.addWidget(self.screen_consent)
        self.stack.addWidget(self.screen_capture)
        self.stack.addWidget(self.screen_recordings)
        self.stack.addWidget(self.screen_review)
        self.stack.addWidget(self.screen_annotations)
        self.stack.addWidget(self.screen_adjudication)
        self.stack.addWidget(self.screen_builder)
        self.stack.addWidget(self.screen_splits)
        self.stack.addWidget(self.screen_release)

        main_layout.addWidget(self.stack)

        # Default screen
        self.buttons[0].setChecked(True)
        self.stack.setCurrentIndex(0)

    def switch_screen(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        widget = self.stack.currentWidget()
        if widget is not None and hasattr(widget, "refresh"):
            widget.refresh()
