#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Dark Minimalist Theme & Color Constants.
Modern, high-contrast, professional styling for the communication workspace.
"""
from __future__ import annotations

# Palette Constants
TEAL = "#42BFB0"
MINT = "#2DD4BF"
TEAL_ACCENT = TEAL
MINT_ACCENT = MINT
DARK_BG = "#101820"
CARD_BG = "#172631"
BORDER = "#30434D"
TEXT_COLOR = "#EAF2F5"
MUTED_TEXT = "#8EA5AF"

DARK_THEME = """
QMainWindow {
    background-color: #101820;
}

QWidget {
    color: #EAF2F5;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #42BFB0;
    selection-color: #101820;
}

QLabel#brand {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#subtitle {
    color: #8EA5AF;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

QLabel#status {
    color: #67CCBC;
    font-size: 11px;
    font-weight: 600;
}

QFrame#videoCard,
QFrame#translationCard,
QFrame#HeaderCard,
QFrame#VideoCard,
QFrame#SubtitleCard,
QFrame#TimelineCard,
QFrame#CleanmeterCard {
    background-color: #172631;
    border: 1px solid #30434D;
    border-radius: 10px;
}

/* Primary and Secondary Action Buttons */
QPushButton {
    background-color: #243542;
    color: #FFFFFF;
    border: 1px solid #3A4F5E;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #2F4454;
    border-color: #42BFB0;
}

QPushButton:pressed {
    background-color: #1A2832;
}

QPushButton#PrimaryButton {
    background-color: #42BFB0;
    color: #101820;
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
    background-color: #1E2D3A;
    color: #FFFFFF;
    border: 1px solid #30434D;
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
    background-color: #1E2D3A;
    color: #FFFFFF;
    border: 1px solid #30434D;
    selection-background-color: #42BFB0;
    selection-color: #101820;
    outline: none;
}

/* CheckBox / Toggle Styling */
QCheckBox {
    color: #EAF2F5;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #3A4F5E;
    border-radius: 4px;
    background-color: #1E2D3A;
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
    color: #8EA5AF;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

QProgressBar {
    background-color: #1E2D3A;
    border: 1px solid #30434D;
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
