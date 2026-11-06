"""Content-addressed video and asset storage management.

Implements immutable, content-addressed ingestion into data/private/objects/sha256/
with atomic writes, collision safety, duplicate detection, and isolated temporary
file cleanup.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from slt_corpus.consent import validate_video_storage_scope
from slt_corpus.domain import ConsentRecord

ALLOWED_EXTENSIONS = frozenset({
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
})


class StorageError(Exception):
    """Raised when an error occurs during file storage or ingestion."""


@dataclass(frozen=True, slots=True)
class StoredAsset:
    """Descriptor of an ingested content-addressed asset."""

    sha256: str
    relative_path: str
    absolute_path: Path
    byte_size: int
    is_duplicate: bool


def ingest_video(
    source_path: str | Path,
    storage_root: str | Path,
    consent: ConsentRecord,
    signer_id: str,
    chunk_size: int = 1024 * 1024,
) -> StoredAsset:
    """Ingest a video file into content-addressed storage after consent validation.

    Args:
        source_path: Path to the local raw video file to ingest.
        storage_root: Base root directory for corpus storage (e.g. data/private).
        consent: Consent record authorizing recording and storage.
        signer_id: Pseudonymous identifier of the participant who signed the consent.
        chunk_size: Chunk size in bytes for hash computation and disk transfer.

    Returns:
        StoredAsset with metadata and status.

    Raises:
        ConsentDeniedError: If consent does not permit record and store.
        StorageError: If source does not exist, format is disallowed, or transfer fails.
    """
    validate_video_storage_scope(consent, signer_id)

    source = Path(source_path).resolve()
    if not source.is_file():
        raise StorageError(f"Source video file not found: {source}")

    suffix = source.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise StorageError(
            f"Unsupported video file extension {suffix!r}. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    # 1. Compute source SHA-256
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    sha256_hash = digest.hexdigest()

    # 2. Compute canonical content-addressed relative path
    prefix = sha256_hash[:2]
    relative_path = f"objects/sha256/{prefix}/{sha256_hash}{suffix}"
    dest_path = (Path(storage_root) / relative_path).resolve()

    # 3. Check for existing identical asset
    if dest_path.is_file():
        dest_size = dest_path.stat().st_size
        source_size = source.stat().st_size
        if dest_size == source_size:
            # Reverify hash of existing destination file
            dest_digest = hashlib.sha256()
            with dest_path.open("rb") as stream:
                while chunk := stream.read(chunk_size):
                    dest_digest.update(chunk)
            if dest_digest.hexdigest() == sha256_hash:
                return StoredAsset(
                    sha256=sha256_hash,
                    relative_path=relative_path,
                    absolute_path=dest_path,
                    byte_size=dest_size,
                    is_duplicate=True,
                )

    # 4. Atomic copy via isolated temporary file in target directory
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.parent / f"{sha256_hash}.{uuid.uuid4().hex}.tmp"

    try:
        write_digest = hashlib.sha256()
        with source.open("rb") as src_stream, tmp_path.open("wb") as dst_stream:
            while chunk := src_stream.read(chunk_size):
                dst_stream.write(chunk)
                write_digest.update(chunk)

        if write_digest.hexdigest() != sha256_hash:
            raise StorageError(
                "Integrity verification failed during atomic ingestion write."
            )

        # Atomic replace
        os.replace(tmp_path, dest_path)
    except Exception as exc:
        # Guarantee cleanup of only this specific temporary file
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        if isinstance(exc, StorageError):
            raise
        raise StorageError(f"Failed to ingest video into storage: {exc}") from exc

    return StoredAsset(
        sha256=sha256_hash,
        relative_path=relative_path,
        absolute_path=dest_path,
        byte_size=dest_path.stat().st_size,
        is_duplicate=False,
    )
