"""Model asset integrity and checksum verification."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from slt_core.perception.errors import ModelAssetError

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def calculate_sha256(path: str | Path) -> str:
    """Calculate SHA-256 hash of a file on disk."""
    file_path = Path(path)
    digest = hashlib.sha256()
    try:
        with file_path.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise ModelAssetError(f"Cannot read model artifact: {exc}") from exc
    return digest.hexdigest().lower()


def verify_model_asset(
    artifact_path: str | Path,
    manifest_path: str | Path | None = None,
) -> str:
    """
    Verify that the model file exists, is readable, and matches the SHA-256
    hash declared in its corresponding manifest.json.
    Returns the verified lowercase SHA-256 string.
    """
    art_path = Path(artifact_path).resolve()
    if not art_path.is_file():
        raise ModelAssetError(f"Model artifact not found: {art_path}")

    actual_sha256 = calculate_sha256(art_path)

    if manifest_path is None:
        man_path = art_path.with_name("manifest.json")
    else:
        man_path = Path(manifest_path).resolve()

    if not man_path.is_file():
        raise ModelAssetError(f"Model manifest not found: {man_path}")

    try:
        data = json.loads(man_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ModelAssetError(f"Malformed model manifest JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ModelAssetError("Model manifest must be a JSON object.")

    expected_sha256 = data.get("sha256")
    if not isinstance(expected_sha256, str) or not SHA256_PATTERN.fullmatch(expected_sha256.lower()):
        raise ModelAssetError(f"Invalid sha256 declared in manifest: {expected_sha256}")

    if actual_sha256 != expected_sha256.lower():
        raise ModelAssetError(
            f"Checksum mismatch for '{art_path.name}'. Expected: {expected_sha256.lower()}, Actual: {actual_sha256}"
        )

    return actual_sha256
