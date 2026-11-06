"""Unit tests for slt_corpus.consent authorization and governance."""

from __future__ import annotations

import pytest

from slt_corpus.consent import (
    ConsentDeniedError,
    require_consent,
    validate_release_consent,
    validate_video_storage_scope,
)
from slt_corpus.domain import ConsentPurpose, ConsentRecord

TEST_HASH = "b" * 64


def make_consent(
    grants: set[ConsentPurpose],
    revoked_at: str | None = None,
    signer_id: str = "signer_001",
) -> ConsentRecord:
    return ConsentRecord(
        consent_id="consent_001",
        signer_id=signer_id,
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:00:00+00:00",
        granted_purposes=frozenset(grants),
        evidence_sha256=TEST_HASH,
        revoked_at_utc=revoked_at,
    )


def test_explicit_storage_consent():
    consent = make_consent({ConsentPurpose.RECORD_AND_STORE})
    # Must succeed without error
    validate_video_storage_scope(consent, "signer_001")


def test_consent_denied_for_unauthorized_purpose():
    # Only internal research granted
    consent = make_consent({ConsentPurpose.INTERNAL_RESEARCH})
    # Attempting commercial training must fail
    with pytest.raises(ConsentDeniedError, match="does not authorize purpose"):
        require_consent(consent, ConsentPurpose.COMMERCIAL_TRAINING, "signer_001")


def test_revoked_consent_denies_all_operations():
    consent = make_consent(
        {ConsentPurpose.RECORD_AND_STORE, ConsentPurpose.INTERNAL_RESEARCH},
        revoked_at="2026-11-06T12:00:00Z",
    )
    with pytest.raises(ConsentDeniedError, match="was revoked"):
        validate_video_storage_scope(consent, "signer_001")


def test_wrong_participant_raises():
    consent = make_consent({ConsentPurpose.RECORD_AND_STORE}, signer_id="signer_001")
    with pytest.raises(ConsentDeniedError, match="Consent belongs to signer 'signer_001', not 'signer_002'"):
        validate_video_storage_scope(consent, "signer_002")


def test_release_consent_verification():
    c1 = make_consent({ConsentPurpose.INTERNAL_RESEARCH}, signer_id="signer_A")
    c2 = make_consent({ConsentPurpose.INTERNAL_RESEARCH}, signer_id="signer_B")

    # Both signers authorized for INTERNAL_RESEARCH
    validate_release_consent(
        {"signer_A": c1, "signer_B": c2},
        ["signer_A", "signer_B"],
        ConsentPurpose.INTERNAL_RESEARCH,
    )

    # If COMMERCIAL_TRAINING is requested, it must be denied because neither granted it
    with pytest.raises(ConsentDeniedError, match="does not authorize purpose"):
        validate_release_consent(
            {"signer_A": c1, "signer_B": c2},
            ["signer_A", "signer_B"],
            ConsentPurpose.COMMERCIAL_TRAINING,
        )

    # Missing signer consent raises
    with pytest.raises(ConsentDeniedError, match="has no registered consent record"):
        validate_release_consent(
            {"signer_A": c1},
            ["signer_A", "signer_unknown"],
            ConsentPurpose.INTERNAL_RESEARCH,
        )
