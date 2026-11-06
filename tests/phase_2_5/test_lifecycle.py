"""Unit tests for Phase 2.5 pipeline lifecycle and resource release."""
from __future__ import annotations

import numpy as np
import pytest

from slt_core.domain import (
    FramePacket,
    LanguageProfile,
    PerceptionFrame,
    RecognitionHypothesis,
    SignEvent,
    TranslationOutput,
)
from slt_core.errors import ClosedPipelineError
from slt_core.pipeline import CorePipeline


class FakePerception:
    def __init__(self) -> None:
        self.ready = True
        self.closed = False

    def detect(self, packet: FramePacket) -> PerceptionFrame:
        return PerceptionFrame(
            source_id=packet.source_id,
            frame_index=packet.frame_index,
            timestamp_ns=packet.timestamp_ns,
            hands=(),
        )

    def close(self) -> None:
        self.closed = True


class FakeRecognizer:
    def __init__(self) -> None:
        self.ready = True
        self.closed = False

    def predict(
        self, perception: PerceptionFrame, profile: LanguageProfile
    ) -> tuple[RecognitionHypothesis, ...]:
        return ()

    def close(self) -> None:
        self.closed = True


class FakeDecoder:
    def __init__(self) -> None:
        self.ready = True
        self.closed = False

    def update(
        self,
        timestamp_ns: int,
        hypotheses: tuple[RecognitionHypothesis, ...],
        perception: PerceptionFrame,
    ) -> tuple[SignEvent, ...]:
        return ()

    def flush(self) -> tuple[SignEvent, ...]:
        return ()

    def reset(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class FakeTranslator:
    def __init__(self) -> None:
        self.ready = True
        self.closed = False

    def translate(
        self,
        events: tuple[SignEvent, ...],
        profile: LanguageProfile,
        target_locale: str,
    ) -> TranslationOutput:
        return TranslationOutput(
            profile_id=profile.profile_id,
            target_locale=target_locale,
            source_sign_ids=(),
            display_text="",
            is_final=True,
            confidence=1.0,
            produced_at_ns=1_000_000_000,
        )

    def reset(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


def test_pipeline_lifecycle_close_and_prevent_reuse():
    p = FakePerception()
    r = FakeRecognizer()
    d = FakeDecoder()
    t = FakeTranslator()

    profile = LanguageProfile(
        profile_id="lsc",
        display_name="Colombian Sign Language",
        source_language_code="lsc",
        vocabulary_version="1.0.0",
        output_locales=("es-CO", "en-US"),
        capabilities=frozenset({"isolated", "continuous"}),
    )

    pipeline = CorePipeline(p, r, d, t, profile)

    dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
    packet = FramePacket(
        source_id="cam_0",
        frame_index=0,
        timestamp_ns=1_000_000_000,
        image=dummy_image,
    )

    # Process frame
    pipeline.process_frame(packet)

    # Close pipeline
    pipeline.close()
    assert pipeline.is_closed
    assert p.closed
    assert r.closed
    assert d.closed
    assert t.closed

    # Calling process_frame on closed pipeline raises ClosedPipelineError
    with pytest.raises(ClosedPipelineError, match="closed"):
        pipeline.process_frame(packet)

    # Idempotent close
    pipeline.close()
    assert pipeline.is_closed
