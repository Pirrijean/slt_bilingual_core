"""Minimalist and modern dark scientific theme for PySide6."""

DARK_THEME = """
QMainWindow {
    background-color: #0d131a;
}

QWidget {
    color: #e6edf3;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
    font-size: 13px;
}

/* Panels and Cards */
QFrame#cardPanel {
    background-color: #16202c;
    border: 1px solid #233140;
    border-radius: 10px;
}

QFrame#cardSubPanel {
    background-color: #1a2736;
    border: 1px solid #2a3a4c;
    border-radius: 8px;
}

/* Headings */
QLabel#headerTitle {
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#headerSubtitle {
    color: #38d9a9;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QLabel#sectionTitle {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Telemetry Pills */
QLabel#telemetryPill {
    background-color: rgba(22, 32, 44, 0.85);
    border: 1px solid #2e4154;
    border-radius: 6px;
    color: #cbd5e1;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#liveBadge {
    background-color: rgba(56, 217, 169, 0.15);
    border: 1px solid #38d9a9;
    border-radius: 6px;
    color: #38d9a9;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

/* Subtitle Displays */
QLabel#subtitleLabelES {
    color: #ffffff;
    font-size: 22px;
    font-weight: 600;
    line-height: 1.3;
}

QLabel#subtitleLabelEN {
    color: #7dd3fc;
    font-size: 20px;
    font-weight: 500;
    line-height: 1.3;
}

QLabel#glossDisplay {
    color: #fbbf24;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* Buttons */
QPushButton {
    background-color: #243447;
    border: 1px solid #364d66;
    border-radius: 6px;
    color: #f1f5f9;
    padding: 8px 14px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #2e435c;
    border-color: #4a6787;
}

QPushButton:pressed {
    background-color: #1a2736;
}

QPushButton#primaryButton {
    background-color: #0d9488;
    border: 1px solid #14b8a6;
    color: #ffffff;
    font-weight: 700;
}

QPushButton#primaryButton:hover {
    background-color: #14b8a6;
    border-color: #2dd4bf;
}

QPushButton#dangerButton {
    background-color: #3f1d24;
    border: 1px solid #7f1d1d;
    color: #fca5a5;
}

QPushButton#dangerButton:hover {
    background-color: #5c202a;
    border-color: #991b1b;
}

/* Inputs & Combos */
QComboBox {
    background-color: #1a2736;
    border: 1px solid #2d3f52;
    border-radius: 6px;
    color: #f1f5f9;
    padding: 6px 12px;
    font-weight: 500;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #16202c;
    border: 1px solid #2d3f52;
    selection-background-color: #0d9488;
    color: #f1f5f9;
}

/* Progress Bars */
QProgressBar {
    background-color: #131b24;
    border: 1px solid #233140;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #38d9a9;
    border-radius: 3px;
}

/* Scroll Area */
QScrollArea {
    background: transparent;
    border: none;
}
"""
