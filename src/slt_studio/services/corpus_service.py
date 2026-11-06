"""Corpus business service decoupling catalog interactions from Qt presentations."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
    ConsentPurpose,
    ConsentRecord,
    ConsentStatus,
    Participant,
    Recording,
)


class CorpusService:
    """Provides high-level transactional corpus queries and participant operations."""

    def __init__(self, catalog: CorpusCatalog) -> None:
        self.catalog = catalog

    def get_participants(self) -> list[Participant]:
        """Retrieve all registered participants."""
        return self.catalog.list_participants()

    def register_participant(self, signer_id: str, metadata_json: str = "{}") -> Participant:
        """Register a new pseudonymous participant."""
        now_utc = datetime.now(UTC).isoformat()
        participant = Participant(
            signer_id=signer_id,
            metadata_json=metadata_json,
            created_at_utc=now_utc,
        )
        self.catalog.add_participant(participant)
        return participant

    def get_consents(self) -> list[ConsentRecord]:
        """Retrieve all consent records."""
        results: list[ConsentRecord] = []
        with self.catalog._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT consent_id, signer_id, form_version, signed_at_utc,
                       granted_purposes_json, evidence_sha256, revoked_at_utc
                FROM consents
                ORDER BY signed_at_utc DESC;
                """
            )
            for row in cursor.fetchall():
                purposes_raw = json.loads(row[4])
                purposes = frozenset(ConsentPurpose(p) for p in purposes_raw)
                revoked_at = row[6]
                status = ConsentStatus.REVOKED if revoked_at is not None else ConsentStatus.ACTIVE
                results.append(
                    ConsentRecord(
                        consent_id=row[0],
                        signer_id=row[1],
                        form_version=row[2],
                        signed_at_utc=row[3],
                        granted_purposes=purposes,
                        evidence_sha256=row[5],
                        revoked_at_utc=revoked_at,
                        status=status,
                    )
                )
        return results

    def register_consent(
        self,
        consent_id: str,
        signer_id: str,
        form_version: str,
        purposes: frozenset[ConsentPurpose],
        evidence_sha256: str,
    ) -> ConsentRecord:
        """Register a new consent authorization."""
        now_utc = datetime.now(UTC).isoformat()
        consent = ConsentRecord(
            consent_id=consent_id,
            signer_id=signer_id,
            form_version=form_version,
            signed_at_utc=now_utc,
            granted_purposes=purposes,
            status=ConsentStatus.ACTIVE,
            evidence_sha256=evidence_sha256,
        )
        self.catalog.add_consent(consent)
        return consent

    def revoke_consent(self, consent_id: str) -> None:
        """Revoke an existing consent record."""
        now_utc = datetime.now(UTC).isoformat()
        self.catalog.revoke_consent(consent_id, now_utc)

    def get_recordings(self) -> list[Recording]:
        """Retrieve all registered takes."""
        return self.catalog.list_recordings()

    def get_statistics(self) -> dict[str, object]:
        """Aggregate high-level KPI corpus statistics."""
        participants = self.catalog.list_participants()
        consents = self.get_consents()
        recordings = self.catalog.list_recordings()

        active_consents = sum(1 for c in consents if c.status == ConsentStatus.ACTIVE)
        revoked_consents = sum(1 for c in consents if c.status == ConsentStatus.REVOKED)
        total_duration_sec = sum(r.duration_ns for r in recordings) / 1_000_000_000.0

        return {
            "participant_count": len(participants),
            "recording_count": len(recordings),
            "active_consents": active_consents,
            "revoked_consents": revoked_consents,
            "total_duration_seconds": total_duration_sec,
        }
