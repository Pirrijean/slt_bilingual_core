"""Informed consent verification and governance engine.

Ensures that no recording ingestion, feature derivation, or dataset release
occurs without active, unrevoked, purpose-specific authorization from the
corresponding participant.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from slt_corpus.domain import ConsentPurpose, ConsentRecord, ConsentStatus


class ConsentDeniedError(PermissionError):
    """Raised when an operation is attempted without valid authorized consent."""


def require_consent(
    consent: ConsentRecord,
    target_a: str | ConsentPurpose,
    target_b: str | ConsentPurpose,
) -> None:
    """Verify that a consent record grants a specific purpose for a signer.

    Supports both (consent, signer_id, purpose) and (consent, purpose, signer_id).
    """
    if isinstance(target_a, ConsentPurpose):
        purpose = target_a
        signer_id = str(target_b)
    else:
        signer_id = str(target_a)
        purpose = ConsentPurpose(target_b)

    if consent.signer_id != signer_id:
        raise ConsentDeniedError(
            f"Consent belongs to signer {consent.signer_id!r}, not {signer_id!r}."
        )
    if consent.status == ConsentStatus.REVOKED or consent.revoked_at_utc is not None:
        raise ConsentDeniedError(
            f"Consent {consent.consent_id!r} for signer {signer_id!r} was revoked."
        )
    if consent.status != ConsentStatus.ACTIVE:
        raise ConsentDeniedError(
            f"Consent {consent.consent_id!r} for signer {signer_id!r} is not active ({consent.status.value})."
        )

    now = datetime.now(UTC)
    if not consent.permits(purpose, now):
        raise ConsentDeniedError(
            f"Consent {consent.consent_id!r} does not authorize purpose {purpose.value!r} for signer {signer_id!r}."
        )


def validate_video_storage_scope(
    consent: ConsentRecord,
    signer_id: str,
) -> None:
    """Ensure consent grants permission to record and store raw video."""
    require_consent(consent, signer_id, ConsentPurpose.RECORD_AND_STORE)


def validate_release_consent(*args: Any, **kwargs: Any) -> None:
    """Ensure all recordings or signers to be released have active authorization for the target purpose.

    Supports:
        validate_release_consent(consents_by_signer, signers, purpose)
        validate_release_consent(recordings, consents_by_recording, signer_by_recording, purpose)
    """
    if len(args) == 3:
        consents_by_signer, signers, purpose = args
        if (
            not isinstance(consents_by_signer, Mapping)
            or not isinstance(purpose, ConsentPurpose)
            or not isinstance(signers, Iterable)
        ):
            raise ConsentDeniedError("Invalid arguments to validate_release_consent")
        for signer_id in signers:
            if signer_id not in consents_by_signer:
                raise ConsentDeniedError(f"Participant {signer_id!r} has no registered consent record.")
            consent = consents_by_signer[signer_id]
            require_consent(consent, str(signer_id), purpose)
    elif len(args) == 4:
        recordings, consents_by_recording, signer_by_recording, purpose = args
        if (
            not isinstance(consents_by_recording, Mapping)
            or not isinstance(signer_by_recording, Mapping)
            or not isinstance(purpose, ConsentPurpose)
            or not isinstance(recordings, Iterable)
        ):
            raise ConsentDeniedError("Invalid arguments to validate_release_consent")
        for rec_id in recordings:
            if rec_id not in consents_by_recording:
                raise ConsentDeniedError(f"Recording {rec_id!r} has no registered consent record.")
            consent = consents_by_recording[rec_id]
            signer = signer_by_recording[rec_id]
            require_consent(consent, signer, purpose)
    else:
        raise ValueError("validate_release_consent expects 3 or 4 positional arguments.")
