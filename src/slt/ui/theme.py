#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Theme & Visual System.
Defines the official brand palette (Graphite, Slate, Teal, Mist) and high-contrast QSS styling.
"""

GRAPHITE = "#101820"
SLATE = "#1B303B"
SLATE_LIGHT = "#243E4D"
TEAL = "#42BFB0"
TEAL_HOVER = "#38A89A"
MIST = "#ECF2F3"
MUTED = "#8899A6"
AMBER = "#F59E0B"
EMERALD = "#10B981"
CRIMSON = "#EF4444"

COMMUNICATION_THEME = f"""
QMainWindow {{
    background-color: {GRAPHITE};
    color: {MIST};
}}

QWidget {{
    background-color: {GRAPHITE};
    color: {MIST};
    font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
}}

/* Surface Containers */
QFrame#stageContainer, QFrame#cardContainer, QFrame#timelineContainer, QFrame#drawerContainer {{
    background-color: {SLATE};
    border: 1px solid {SLATE_LIGHT};
    border-radius: 10px;
}}

QFrame#diagnosticsBar {{
    background-color: #0B1117;
    border-top: 1px solid {SLATE_LIGHT};
    padding: 4px 12px;
}}

/* Typography */
QLabel#headerTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {MIST};
    letter-spacing: 0.5px;
}}

QLabel#headerSubtitle {{
    font-size: 11px;
    font-weight: 600;
    color: {TEAL};
    letter-spacing: 1.2px;
}}

QLabel#sectionTitle {{
    font-size: 12px;
    font-weight: 700;
    color: {MUTED};
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}

QLabel#subtitleText {{
    font-size: 22px;
    font-weight: 600;
    color: {MIST};
    line-height: 1.3;
}}

QLabel#subtitleLangTag {{
    font-size: 10px;
    font-weight: 700;
    color: {TEAL};
    background-color: rgba(66, 191, 176, 0.15);
    border: 1px solid rgba(66, 191, 176, 0.3);
    border-radius: 4px;
    padding: 2px 6px;
}}

QLabel#telemetryText {{
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 11px;
    color: {MUTED};
}}

/* Buttons */
QPushButton {{
    background-color: {SLATE_LIGHT};
    color: {MIST};
    border: 1px solid #335366;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
    font-size: 12px;
}}

QPushButton:hover {{
    background-color: #2F4F61;
    border-color: {TEAL};
    color: #FFFFFF;
}}

QPushButton:pressed {{
    background-color: #1E3542;
}}

QPushButton#primaryActionBtn {{
    background-color: {TEAL};
    color: {GRAPHITE};
    border: 1px solid {TEAL};
    font-weight: 700;
}}

QPushButton#primaryActionBtn:hover {{
    background-color: {TEAL_HOVER};
    border-color: {TEAL_HOVER};
}}

QPushButton#dangerActionBtn {{
    background-color: rgba(239, 68, 68, 0.15);
    color: #FCA5A5;
    border: 1px solid rgba(239, 68, 68, 0.3);
}}

QPushButton#dangerActionBtn:hover {{
    background-color: rgba(239, 68, 68, 0.25);
    border-color: {CRIMSON};
    color: #FFFFFF;
}}

/* Timeline Chip Button */
QPushButton#timelineChip {{
    background-color: rgba(66, 191, 176, 0.12);
    border: 1px solid rgba(66, 191, 176, 0.35);
    border-radius: 14px;
    color: {MIST};
    font-weight: 600;
    font-size: 11px;
    padding: 4px 10px;
}}

QPushButton#timelineChip:hover {{
    background-color: rgba(239, 68, 68, 0.2);
    border-color: {CRIMSON};
    color: #FFFFFF;
}}

/* Scrollbar */
QScrollBar:horizontal {{
    border: none;
    background: {GRAPHITE};
    height: 6px;
    border-radius: 3px;
}}

QScrollBar::handle:horizontal {{
    background: {SLATE_LIGHT};
    min-width: 20px;
    border-radius: 3px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {TEAL};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QScrollBar:vertical {{
    border: none;
    background: {GRAPHITE};
    width: 6px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical {{
    background: {SLATE_LIGHT};
    min-height: 20px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TEAL};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
