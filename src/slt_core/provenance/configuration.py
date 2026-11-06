"""Configuration hashing and canonical serialization for model provenance."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: dict[str, Any]) -> bytes:
    """Serialize dictionary canonically for deterministic SHA-256 calculation."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def configuration_sha256(configuration: dict[str, Any]) -> str:
    """Compute reproducible SHA-256 checksum of an extractor/model configuration."""
    return hashlib.sha256(canonical_json(configuration)).hexdigest()
