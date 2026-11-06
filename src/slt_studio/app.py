"""Application entrypoint for SLT Dataset Studio."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from slt_studio.main_window import DatasetStudioMainWindow


def main() -> int:
    """Launch Dataset Studio desktop interface."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = DatasetStudioMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
