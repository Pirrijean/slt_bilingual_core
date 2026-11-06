#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for slt_desktop.subtitles module.
Verifies standard SRT formatting, indices, and transcript report generation.
"""
import pytest
from pathlib import Path
from slt_desktop.subtitles import (
    format_timestamp,
    create_srt_content,
    export_srt,
    create_transcription_txt
)


def test_format_timestamp():
    """Verify millisecond to SRT timecode conversions."""
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(1500) == "00:00:01,500"
    assert format_timestamp(65230) == "00:01:05,230"
    assert format_timestamp(3661005) == "01:01:01,005"


def test_create_srt_content_sequential_indexing():
    """Verify 1-based sequential indexing and valid block structure."""
    events = [
        {"label": "HOLA", "start_ms": 1000, "end_ms": 2000},
        {"label": "AGUA", "start_ms": 2500, "end_ms": 3800}
    ]
    es = "Hola, quiero agua."
    en = "Hello, I want water."

    srt = create_srt_content(events, es, en)
    lines = srt.strip().split("\n")

    # Block 1: HOLA
    assert lines[0] == "1"
    assert "00:00:01,000 --> 00:00:02,000" in lines[1]
    assert "[HOLA]" in lines[2]

    # Block 2: AGUA
    assert lines[4] == "2"
    assert "00:00:02,500 --> 00:00:03,800" in lines[5]
    assert "[AGUA]" in lines[6]

    # Block 3: Consolidated bilingual translation
    assert lines[8] == "3"
    assert "00:00:01,000 --> 00:00:03,800" in lines[9]
    assert f"ES: {es}" in lines[10]
    assert f"EN: {en}" in lines[11]


def test_export_srt_file(tmp_path: Path):
    """Verify file writing with UTF-8 encoding."""
    test_file = tmp_path / "test_output.srt"
    content = "1\n00:00:01,000 --> 00:00:02,000\n[GRACIAS]\n"
    export_srt(str(test_file), content)

    assert test_file.exists()
    assert test_file.read_text(encoding="utf-8") == content


def test_create_transcription_txt():
    """Verify structured TXT report generation."""
    events = [
        {"label": "AYUDA", "start_ms": 1000, "end_ms": 2500, "stability": 0.95}
    ]
    txt = create_transcription_txt(events, "¡Necesito ayuda!", "I need help!", "video_test.mp4")
    assert "SLT BILINGUAL CORE" in txt
    assert "video_test.mp4" in txt
    assert "AYUDA" in txt
    assert "¡Necesito ayuda!" in txt
    assert "I need help!" in txt
