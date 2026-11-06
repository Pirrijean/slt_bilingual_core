#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Subtitle and Transcription Generation Module.
Exports standard SRT subtitles and formatted text transcripts.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional


def format_timestamp(ms: int) -> str:
    """
    Format milliseconds to SRT timecode standard: HH:MM:SS,mmm.
    Guarantees strict 3-digit millisecond precision and 2-digit hour/minute/second.
    """
    ms = max(0, int(ms))
    total_seconds = ms // 1000
    millis = ms % 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def create_srt_content(
    events: List[Dict[str, Any]],
    es_text: str = "",
    en_text: str = ""
) -> str:
    """
    Generates standard SRT formatted subtitle content with sequential 1-based indexing.
    Includes sign-by-sign events followed by consolidated bilingual subtitles if available.
    """
    blocks = []
    block_index = 1

    # 1. Sign-by-sign subtitle blocks
    for ev in events:
        start_ms = ev.get("start_ms", 0)
        end_ms = ev.get("end_ms", start_ms + 1000)
        label = ev.get("label", "")
        if not label or label == "_NADA_":
            continue

        ts_start = format_timestamp(start_ms)
        ts_end = format_timestamp(end_ms)

        blocks.append(f"{block_index}\n{ts_start} --> {ts_end}\n[{label}]\n")
        block_index += 1

    # 2. Consolidated bilingual subtitle block if texts are present
    if es_text or en_text:
        if events:
            global_start_ms = min(ev.get("start_ms", 0) for ev in events)
            global_end_ms = max(ev.get("end_ms", global_start_ms + 1000) for ev in events)
        else:
            global_start_ms = 0
            global_end_ms = 5000

        ts_start = format_timestamp(global_start_ms)
        ts_end = format_timestamp(global_end_ms)

        lines = [f"{block_index}", f"{ts_start} --> {ts_end}"]
        if es_text:
            lines.append(f"ES: {es_text}")
        if en_text:
            lines.append(f"EN: {en_text}")
        lines.append("")

        blocks.append("\n".join(lines))

    return "\n".join(blocks).strip() + "\n" if blocks else ""


def export_srt(filepath: str, content: str) -> None:
    """Export SRT string to a UTF-8 encoded text file."""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def create_transcription_txt(
    events: List[Dict[str, Any]],
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
                f"Seña: {label} (duración: {dur:.1f}s, confianza: {ev.get('stability', 1.0):.2f})"
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
