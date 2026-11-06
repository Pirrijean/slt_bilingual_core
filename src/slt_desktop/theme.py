#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Dark Minimalist Theme & Color Constants.
Modern, high-contrast, professional styling for the communication workspace.
"""

# Palette Constants
BG_DARK = "#12161E"
BG_CARD = "#1A202C"
BG_PANEL = "#1E2530"
BORDER_COLOR = "#2D3748"
BORDER_FOCUS = "#42BFB0"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#94A3B8"
TEXT_MUTED = "#64748B"
TEAL_ACCENT = "#42BFB0"
MINT_ACCENT = "#2DD4BF"
ACTIVE_LIVE = "#EF4444"
WARN_COLOR = "#F59E0B"

DARK_THEME = """
/* SLT Desktop Modern Clean Theme */
QWidget {
    background-color: #12161E;
    color: #FFFFFF;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #42BFB0;
    selection-color: #12161E;
}

QMainWindow {
    background-color: #12161E;
}

QFrame#HeaderCard, QFrame#VideoCard, QFrame#SubtitleCard, QFrame#TimelineCard, QFrame#CleanmeterCard {
    background-color: #1A202C;
    border: 1px solid #2D3748;
    border-radius: 8px;
}

/* Primary and Secondary Action Buttons */
QPushButton {
    background-color: #2D3748;
    color: #FFFFFF;
    border: 1px solid #4A5568;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #3A475A;
    border-color: #42BFB0;
}

QPushButton:pressed {
    background-color: #1F2733;
}

QPushButton#PrimaryButton {
    background-color: #42BFB0;
    color: #12161E;
    border: 1px solid #2DD4BF;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #2DD4BF;
}

QPushButton#PrimaryButton:pressed {
    background-color: #38A396;
}

QPushButton#DangerButton {
    background-color: #7F1D1D;
    color: #FEE2E2;
    border: 1px solid #991B1B;
}

QPushButton#DangerButton:hover {
    background-color: #991B1B;
}

/* ComboBox Styling */
QComboBox {
    background-color: #1E2530;
    color: #FFFFFF;
    border: 1px solid #2D3748;
    border-radius: 6px;
    padding: 5px 10px;
    min-width: 110px;
}

QComboBox:hover {
    border-color: #42BFB0;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1E2530;
    color: #FFFFFF;
    border: 1px solid #2D3748;
    selection-background-color: #42BFB0;
    selection-color: #12161E;
    outline: none;
}

/* CheckBox / Toggle Styling */
QCheckBox {
    color: #E2E8F0;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #4A5568;
    border-radius: 4px;
    background-color: #1E2530;
}

QCheckBox::indicator:hover {
    border-color: #42BFB0;
}

QCheckBox::indicator:checked {
    background-color: #42BFB0;
    border-color: #2DD4BF;
    image: none;
}

/* Typography Classes */
QLabel#AppTitle {
    font-size: 15px;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: 0.5px;
}

QLabel#ModeBadgeLive {
    background-color: #7F1D1D;
    color: #FCA5A5;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid #991B1B;
}

QLabel#ModeBadgeVideo {
    background-color: #1E3A8A;
    color: #93C5FD;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid #2563EB;
}

QLabel#SubtitleHeading {
    font-size: 11px;
    font-weight: 700;
    color: #42BFB0;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QLabel#SubtitleTextES {
    font-size: 20px;
    font-weight: 700;
    color: #FFFFFF;
    line-height: 1.3;
}

QLabel#SubtitleTextEN {
    font-size: 16px;
    font-weight: 500;
    color: #CBD5E1;
    line-height: 1.3;
}

QLabel#TelemetryItem {
    font-size: 11px;
    color: #94A3B8;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

QProgressBar {
    background-color: #1E2530;
    border: 1px solid #2D3748;
    border-radius: 4px;
    text-align: center;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 600;
    height: 14px;
}

QProgressBar::chunk {
    background-color: #42BFB0;
    border-radius: 3px;
}
"""
