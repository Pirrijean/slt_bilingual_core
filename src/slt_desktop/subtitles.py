#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Subtitle and Transcription Generation Module.
Exports standard SRT subtitles and formatted text transcripts.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional


def format_timestamp(milliseconds: int) -> str:
    """
    Format milliseconds to SRT timecode standard: HH:MM:SS,mmm.
    Uses divmod for exact integer arithmetic and formatting.
    """
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d},"
        f"{millis:03d}"
    )


def create_srt_content(
    events: list[dict],
    es_text: str = "",
    en_text: str = ""
) -> str:
    """
    Generates standard SRT formatted subtitle content.
    Correctly computes index = len(blocks) + 1 to avoid omitted indices.
    """
    blocks = []
    valid_events = sorted(
        events,
        key=lambda event: int(event.get("start_ms", 0))
    )

    for event in valid_events:
        label = event.get("label", "")
        if not label or label == "_NADA_":
            continue

        index = len(blocks) + 1
        start_ms = int(event.get("start_ms", 0))
        end_ms = int(event.get("end_ms", start_ms + 1000))

        ts_start = format_timestamp(start_ms)
        ts_end = format_timestamp(end_ms)

        block_lines = [str(index), f"{ts_start} --> {ts_end}", label]

        # Check for event-level or passed translation text
        ev_es = event.get("es", "")
        ev_en = event.get("en", "")
        if ev_es:
            block_lines.append(f"ES: {ev_es}")
        if ev_en:
            block_lines.append(f"EN: {ev_en}")

        blocks.append("\n".join(block_lines) + "\n")

    # Add consolidated translation block if provided and not in individual events
    has_event_level_trans = any(bool(e.get("es") or e.get("en")) for e in valid_events)
    if (es_text or en_text) and not has_event_level_trans:
        index = len(blocks) + 1
        if valid_events:
            global_start_ms = min(int(ev.get("start_ms", 0)) for ev in valid_events)
            global_end_ms = max(int(ev.get("end_ms", global_start_ms + 1000)) for ev in valid_events)
        else:
            global_start_ms = 0
            global_end_ms = 5000

        ts_start = format_timestamp(global_start_ms)
        ts_end = format_timestamp(global_end_ms)

        lines = [str(index), f"{ts_start} --> {ts_end}"]
        if es_text:
            lines.append(f"ES: {es_text}")
        if en_text:
            lines.append(f"EN: {en_text}")
        blocks.append("\n".join(lines) + "\n")

    return "\n".join(blocks).strip() + "\n" if blocks else ""


def export_srt(filepath: str | Path, content: str) -> None:
    """Export SRT string to a UTF-8 encoded text file."""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def create_transcription_txt(
    events: list[dict],
    es_text: str,
    en_text: str,
    source_name: str = "Video"
) -> str:
    """Generate structured plain text transcription report."""
    lines = [
        "============================================================",
        "SLT BILINGUAL CORE · REPORTE DE TRADUCCIÓN DE VIDEO",
        f"Archivo / Fuente: {source_name}",
        "============================================================",
        "",
        "--- SECUENCIA CRONOLÓGICA DE SEÑAS ---"
    ]

    if events:
        for ev in events:
            s_sec = ev.get("start_ms", 0) / 1000.0
            e_sec = ev.get("end_ms", 0) / 1000.0
            dur = max(0.0, e_sec - s_sec)
            label = ev.get("label", "DESCONOCIDO")
            mins_s = int(s_sec // 60)
            secs_s = int(s_sec % 60)
            mins_e = int(e_sec // 60)
            secs_e = int(e_sec % 60)
            lines.append(
                f"{mins_s:02d}:{secs_s:02d} – {mins_e:02d}:{secs_e:02d} | "
                f"Seña: {label} (duración: {dur:.1f}s, estabilidad: {ev.get('stability', 1.0):.2f})"
            )
    else:
        lines.append("(No se detectaron señas en el video)")

    lines.extend([
        "",
        "--- TRADUCCIÓN BILINGÜE SIMULTÁNEA ---",
        f"Español : {es_text or '...'}",
        f"English : {en_text or '...'}",
        "",
        "============================================================"
    ])
    return "\n".join(lines)
