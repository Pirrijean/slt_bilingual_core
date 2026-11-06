"""Unit tests for MediaPipe Hand Landmarker result conversion."""
from types import SimpleNamespace

import pytest

from slt_core.domain import Handedness
from slt_core.perception.mediapipe_hand import convert_mediapipe_result


def make_points(offset: float = 0.0):
    return [
        SimpleNamespace(x=float(i) / 21.0 + offset, y=float(i) / 21.0, z=0.0)
        for i in range(21)
    ]


def make_result(handedness_str: str = "Left", score: float = 0.97):
    category = SimpleNamespace(category_name=handedness_str, score=score)
    return SimpleNamespace(
        hand_landmarks=[make_points()],
        hand_world_landmarks=[make_points(offset=0.1)],
        handedness=[[category]],
    )


def test_convert_single_hand_result():
    res = make_result(handedness_str="Left", score=0.96)
    observations = convert_mediapipe_result(res)

    assert len(observations) == 1
    obs = observations[0]
    assert obs.handedness == Handedness.LEFT
    assert obs.handedness_score == 0.96
    assert len(obs.landmarks) == 21
    assert len(obs.world_landmarks) == 21
    assert obs.tracking_id is None  # Tracking ID is assigned downstream by HandTracker


def test_convert_two_hands_result():
    cat_left = SimpleNamespace(category_name="Left", score=0.95)
    cat_right = SimpleNamespace(category_name="Right", score=0.92)

    res = SimpleNamespace(
        hand_landmarks=[make_points(0.0), make_points(0.4)],
        hand_world_landmarks=[make_points(0.0), make_points(0.4)],
        handedness=[[cat_left], [cat_right]],
    )
    observations = convert_mediapipe_result(res)

    assert len(observations) == 2
    assert observations[0].handedness == Handedness.LEFT
    assert observations[1].handedness == Handedness.RIGHT
    assert len(observations[0].landmarks) == 21
    assert len(observations[1].landmarks) == 21


def test_convert_empty_or_none_result():
    assert convert_mediapipe_result(None) == ()
    empty_res = SimpleNamespace(hand_landmarks=[], hand_world_landmarks=[], handedness=[])
    assert convert_mediapipe_result(empty_res) == ()


def test_model_asset_verification(tmp_path):
    import json

    from slt_core.perception.errors import ModelAssetError
    from slt_core.perception.model_assets import calculate_sha256, verify_model_asset

    # 1. Create a dummy artifact and manifest
    art = tmp_path / "test.task"
    art.write_bytes(b"dummy model bytes")
    actual_hash = calculate_sha256(art)

    man = tmp_path / "manifest.json"
    man.write_text(json.dumps({"sha256": actual_hash}), encoding="utf-8")

    verified = verify_model_asset(art, man)
    assert verified == actual_hash

    # 2. Checksum mismatch raises ModelAssetError
    man_bad = tmp_path / "bad_manifest.json"
    man_bad.write_text(json.dumps({"sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(ModelAssetError, match="Checksum mismatch"):
        verify_model_asset(art, man_bad)

    # 3. Missing files raise ModelAssetError
    with pytest.raises(ModelAssetError, match="not found"):
        verify_model_asset(tmp_path / "non_existent.task")


def test_mediapipe_hand_perception_end_to_end_if_available():
    from pathlib import Path

    import numpy as np

    from slt_core.domain import FramePacket
    from slt_core.perception.mediapipe_hand import MediaPipeHandPerception

    model_file = Path("models/mediapipe/hand_landmarker.task")
    if not model_file.is_file():
        pytest.skip("MediaPipe model not present in local test environment.")

    perception_engine = MediaPipeHandPerception(model_path=model_file)
    assert perception_engine.ready is True

    # Feed blank frame
    packet = FramePacket(
        source_id="test_cam",
        frame_index=0,
        timestamp_ns=1_000_000,
        image=np.zeros((100, 100, 3), dtype=np.uint8),
    )
    result = perception_engine.detect(packet)
    assert result.source_id == "test_cam"
    assert result.frame_index == 0
    assert result.timestamp_ns == 1_000_000
    assert isinstance(result.hands, tuple)

    perception_engine.close()
    assert perception_engine.ready is False
