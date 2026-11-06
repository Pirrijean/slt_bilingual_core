"""Unit tests for SLT Image Validation."""
import numpy as np
import pytest

from slt_core.domain import FramePacket
from slt_core.perception.errors import InvalidFrameError
from slt_core.perception.image import validate_bgr_frame


def make_packet(image, pixel_format="BGR24"):
    return FramePacket(
        source_id="test_cam",
        frame_index=0,
        timestamp_ns=1000,
        image=image,
        pixel_format=pixel_format,
    )


def test_valid_bgr_image():
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    output = validate_bgr_frame(make_packet(image))
    assert output.shape == (100, 200, 3)
    assert output.dtype == np.uint8
    assert output.flags["C_CONTIGUOUS"]


def test_invalid_pixel_format_raises():
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    with pytest.raises(InvalidFrameError, match="Expected BGR24"):
        validate_bgr_frame(make_packet(image, pixel_format="RGB24"))


def test_image_is_none_raises():
    with pytest.raises(InvalidFrameError, match="cannot be None"):
        validate_bgr_frame(make_packet(None))


def test_incorrect_channels_raises():
    # 4 channels (BGRA)
    img_4ch = np.zeros((100, 200, 4), dtype=np.uint8)
    with pytest.raises(InvalidFrameError, match="exactly 3 color channels"):
        validate_bgr_frame(make_packet(img_4ch))

    # 1 channel (Grayscale 2D)
    img_1ch = np.zeros((100, 200), dtype=np.uint8)
    with pytest.raises(InvalidFrameError, match="three dimensions"):
        validate_bgr_frame(make_packet(img_1ch))


def test_invalid_dtype_raises():
    # Float image instead of uint8
    img_float = np.zeros((100, 200, 3), dtype=np.float32)
    with pytest.raises(InvalidFrameError, match="dtype must be uint8"):
        validate_bgr_frame(make_packet(img_float))


def test_degenerate_dimensions_raises():
    img_1x1 = np.zeros((1, 1, 3), dtype=np.uint8)
    with pytest.raises(InvalidFrameError, match="at least 2x2"):
        validate_bgr_frame(make_packet(img_1x1))


def test_non_contiguous_becomes_contiguous():
    # Slice with step produces non-contiguous stride
    large_img = np.zeros((100, 200, 3), dtype=np.uint8)
    non_contig = large_img[::2, ::2, :]
    assert not non_contig.flags["C_CONTIGUOUS"]

    output = validate_bgr_frame(make_packet(non_contig))
    assert output.flags["C_CONTIGUOUS"]


def test_draw_hand_overlay_leaves_original_unmodified():
    from slt_core.domain import Handedness, HandObservation, Landmark, PerceptionFrame
    from slt_core.perception.overlay import draw_hand_overlay

    orig_image = np.zeros((100, 100, 3), dtype=np.uint8)
    hand = HandObservation(
        tracking_id=1,
        handedness=Handedness.RIGHT,
        landmarks=tuple(Landmark(x=0.5, y=0.5, z=0.0) for _ in range(21)),
        world_landmarks=tuple(Landmark(x=0.0, y=0.0, z=0.0) for _ in range(21)),
        handedness_score=0.95,
    )
    perception = PerceptionFrame(
        source_id="cam",
        frame_index=0,
        timestamp_ns=1000,
        hands=(hand,),
    )

    drawn = draw_hand_overlay(orig_image, perception)
    assert drawn.shape == orig_image.shape
    # Original image is still all zeros
    assert np.all(orig_image == 0)
    # Drawn image has overlay lines/points drawn (not all zeros)
    assert np.any(drawn > 0)

    # Invalid image input raises InvalidFrameError
    with pytest.raises(InvalidFrameError):
        draw_hand_overlay("not an image", perception)
