"""Unit tests for Phase 2.5 model and configuration provenance."""
from __future__ import annotations

from slt_core.provenance.configuration import canonical_json, configuration_sha256


def test_canonical_json_deterministic():
    config1 = {"b": 2, "a": 1, "nested": {"y": 20, "x": 10}}
    config2 = {"nested": {"x": 10, "y": 20}, "a": 1, "b": 2}

    assert canonical_json(config1) == canonical_json(config2)
    assert configuration_sha256(config1) == configuration_sha256(config2)


def test_configuration_sha256_different_values():
    config1 = {"num_hands": 2, "confidence": 0.5}
    config2 = {"num_hands": 2, "confidence": 0.6}

    assert configuration_sha256(config1) != configuration_sha256(config2)
