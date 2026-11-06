"""Unit tests for VideoSource with actual container decoding."""
from pathlib import Path

import pytest

from slt_core.perception.errors import VideoOpenError
from slt_core.sources.video import VideoSource


def test_video_source_reads_and_eos():
    video_path = Path("tests/sample_test_video.mp4")
    assert video_path.is_file()

    source = VideoSource(file_path=video_path, source_id="test_stream")
    assert source.ready is True
    assert source.source_id == "test_stream"

    frames_read = 0
    last_ts = -1

    while True:
        packet = source.read()
        if packet is None:
            break
        assert packet.source_id == "test_stream"
        assert packet.frame_index == frames_read
        assert packet.timestamp_ns > last_ts
        assert packet.pixel_format == "BGR24"
        assert packet.timestamp_kind == "presentation"
        assert packet.image.shape == (64, 64, 3)

        last_ts = packet.timestamp_ns
        frames_read += 1

    assert frames_read == 5
    # Subsequent reads after EOS return None
    assert source.read() is None

    source.close()
    assert source.ready is False


def test_video_source_non_existent_file_raises(tmp_path):
    with pytest.raises(VideoOpenError, match="not found"):
        VideoSource(file_path=tmp_path / "ghost_video.mp4")
