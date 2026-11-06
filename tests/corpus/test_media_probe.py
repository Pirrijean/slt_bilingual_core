"""Unit tests for slt_corpus.media_probe video container and stream validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from slt_corpus.media_probe import (
    MediaProbeError,
    full_decode_audit,
    probe_video,
)

SAMPLE_VIDEO_PATH = Path(__file__).resolve().parent.parent / "sample_test_video.mp4"


def test_probe_sample_video():
    if not SAMPLE_VIDEO_PATH.is_file():
        pytest.skip(f"Sample test video not found at {SAMPLE_VIDEO_PATH}")

    info = probe_video(SAMPLE_VIDEO_PATH)
    assert info.media_type.startswith("video")
    assert info.width > 0
    assert info.height > 0
    assert info.duration_ns is not None and info.duration_ns > 0
    assert info.frame_rate_num is not None and info.frame_rate_num > 0


def test_probe_missing_file_raises():
    with pytest.raises(MediaProbeError, match="Video file does not exist"):
        probe_video("non_existent_file.mp4")


def test_probe_corrupt_file_raises(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.mp4"
    corrupt_file.write_bytes(b"not a video file content")

    with pytest.raises(MediaProbeError, match="Failed to open media container"):
        probe_video(corrupt_file)


def test_full_decode_audit_sample_video():
    if not SAMPLE_VIDEO_PATH.is_file():
        pytest.skip(f"Sample test video not found at {SAMPLE_VIDEO_PATH}")

    audit = full_decode_audit(SAMPLE_VIDEO_PATH, max_frames=10)
    assert audit["is_corrupt"] is False
    assert audit["decoded_frames"] > 0
    assert "pts_discontinuities" in audit


def test_full_decode_audit_corrupt_file(tmp_path: Path):
    corrupt_file = tmp_path / "garbage.mp4"
    corrupt_file.write_bytes(b"corrupt header and payload data")

    audit = full_decode_audit(corrupt_file)
    assert audit["is_corrupt"] is True
    assert "error" in audit
