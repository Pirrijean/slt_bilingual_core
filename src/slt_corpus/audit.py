"""Corpus audit and telemetry reporting module.

Computes aggregations for participants, sessions, original vs augmented recordings,
temporal duration, consent coverage, and external dataset quarantine status.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from slt_corpus.catalog import CorpusCatalog


class CorpusAuditor:
    """Audits catalog entities, generating quantitative and governance reports."""

    def __init__(self, catalog: CorpusCatalog) -> None:
        self.catalog = catalog

    def generate_audit_report(
        self, external_registry_path: str | Path | None = None
    ) -> dict[str, Any]:
        """Generate a complete audit report of the corpus state."""
        participants = self.catalog.list_participants()
        recordings = self.catalog.list_recordings()

        total_recordings = len(recordings)
        original_count = sum(1 for r in recordings if r.parent_recording_id is None)
        augmented_count = sum(1 for r in recordings if r.parent_recording_id is not None)
        total_duration_ns = sum(r.duration_ns for r in recordings)

        # Consent analysis
        active_consents = 0
        revoked_consents = 0
        purpose_counts: Counter[str] = Counter()

        for p in participants:
            c = self.catalog.get_latest_consent_for_signer(p.signer_id)
            if c is not None:
                if c.revoked_at_utc is not None:
                    revoked_consents += 1
                else:
                    active_consents += 1
                    for purp in c.granted_purposes:
                        purpose_counts[purp.value] += 1

        # External datasets quarantine analysis
        external_resources: list[dict[str, Any]] = []
        if external_registry_path is not None:
            reg_path = Path(external_registry_path)
            if reg_path.is_file():
                try:
                    data = json.loads(reg_path.read_text(encoding="utf-8"))
                    external_resources = data.get("resources", [])
                except (OSError, json.JSONDecodeError):
                    external_resources = []

        return {
            "summary": {
                "total_participants": len(participants),
                "total_recordings": total_recordings,
                "original_recordings": original_count,
                "augmented_recordings": augmented_count,
                "total_duration_seconds": round(total_duration_ns / 1_000_000_000, 2),
                "total_duration_hours": round(total_duration_ns / (1_000_000_000 * 3600), 4),
            },
            "governance": {
                "active_consents": active_consents,
                "revoked_consents": revoked_consents,
                "purpose_coverage": dict(purpose_counts),
            },
            "external_datasets_quarantined": [
                {
                    "resource_id": r.get("resource_id"),
                    "name": r.get("name"),
                    "decision": r.get("decision"),
                    "commercial_use_status": r.get("commercial_use_status"),
                }
                for r in external_resources
            ],
        }
