"""Cryptographic hashing utilities for corpus content addressing."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(
    path: str | Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    """Compute the SHA-256 hexadecimal digest of a file in streaming chunks.

    Args:
        path: Path to the target file.
        chunk_size: Byte size per read iteration (default: 1 MiB). Must be > 0.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest string.

    Raises:
        ValueError: If chunk_size <= 0.
        FileNotFoundError: If the target file does not exist.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be strictly positive (> 0).")
    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute the SHA-256 hexadecimal digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_string(text: str, encoding: str = "utf-8") -> str:
    """Compute the SHA-256 hexadecimal digest of an encoded string."""
    return hashlib.sha256(text.encode(encoding)).hexdigest()
