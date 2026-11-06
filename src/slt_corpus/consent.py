"""Informed consent verification and governance engine.

Ensures that no recording ingestion, feature derivation, or dataset release
occurs without active, unrevoked, purpose-specific authorization from the
corresponding participant.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from slt_corpus.domain import ConsentPurpose, ConsentRecord


class ConsentDeniedError(PermissionError):
    """Raised when an operation is attempted without valid authorized consent."""


def require_consent(
    consent: ConsentRecord,
    purpose: ConsentPurpose,
    signer_id: str,
) -> None:
    """Verify that a consent record grants a specific purpose for a signer.

    Raises:
        ConsentDeniedError: If signer does not match, consent is revoked,
            or the specific purpose is not authorized.
    """
    if consent.signer_id != signer_id:
        raise ConsentDeniedError(
            f"Consent belongs to signer {consent.signer_id!r}, not {signer_id!r}."
        )
    if consent.revoked_at_utc is not None:
        raise ConsentDeniedError(
            f"Consent {consent.consent_id!r} for signer {signer_id!r} was revoked at {consent.revoked_at_utc}."
        )
    if not consent.permits(purpose):
        raise ConsentDeniedError(
            f"Consent {consent.consent_id!r} does not authorize purpose: {purpose.value!r}"
        )


def validate_video_storage_scope(
    consent: ConsentRecord,
    signer_id: str,
) -> None:
    """Ensure consent grants permission to record and store raw video."""
    require_consent(consent, ConsentPurpose.RECORD_AND_STORE, signer_id)


def validate_landmark_derivation_scope(
    consent: ConsentRecord,
    signer_id: str,
) -> None:
    """Ensure consent grants permission to extract landmark and feature data."""
    require_consent(consent, ConsentPurpose.DERIVE_LANDMARKS, signer_id)


def validate_release_consent(
    consents_by_signer: Mapping[str, ConsentRecord],
    recording_signers: Iterable[str],
    usage_scope: ConsentPurpose,
) -> None:
    """Verify that all signers contributing to a dataset release have authorized the scope.

    Raises:
        ConsentDeniedError: If any contributing signer lacks an active consent record
            authorizing the specified release usage scope (e.g. COMMERCIAL_TRAINING).
    """
    for signer_id in recording_signers:
        if signer_id not in consents_by_signer:
            raise ConsentDeniedError(
                f"Signer {signer_id!r} has no registered consent record."
            )
        require_consent(consents_by_signer[signer_id], usage_scope, signer_id)
