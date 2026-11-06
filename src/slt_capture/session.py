"""Capture session controller managing participant verification and consent gating."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from slt_capture.protocol import CaptureProtocol, ProtocolTask
from slt_corpus.catalog import CorpusCatalog
from slt_corpus.consent import ConsentDeniedError, validate_video_storage_scope
from slt_corpus.domain import (
    ConsentRecord,
    Session,
)


class SessionState(StrEnum):
    """Lifecycle state of an acquisition session."""

    CONFIGURED = "configured"
    READY = "ready"
    RECORDING = "recording"
    COMPLETED = "completed"
    ERROR = "error"


class CaptureSessionController:
    """Controls the lifecycle of a physical capture session."""

    def __init__(
        self,
        catalog: CorpusCatalog,
        session_id: str,
        signer_id: str,
        protocol: CaptureProtocol,
        operator_id: str,
        allow_draft_protocol: bool = True,
    ) -> None:
        self.catalog = catalog
        self.session_id = session_id
        self.signer_id = signer_id
        self.protocol = protocol
        self.operator_id = operator_id
        self.allow_draft_protocol = allow_draft_protocol
        self.state: SessionState = SessionState.CONFIGURED
        self.active_task: ProtocolTask | None = None
        self._consent: ConsentRecord | None = None

        if not self.allow_draft_protocol and self.protocol.status.lower() == "draft":
            self.state = SessionState.ERROR
            raise ValueError(
                f"Cannot capture with draft protocol {self.protocol.protocol_id!r}. "
                "Protocol must be approved by linguistic and ethics review."
            )

        self._verify_participant_and_consent()

    def _verify_participant_and_consent(self) -> None:
        """Verify participant registration and unrevoked storage consent."""
        participant = self.catalog.get_participant(self.signer_id)
        if participant is None:
            self.state = SessionState.ERROR
            raise ValueError(f"Participant {self.signer_id!r} is not registered in catalog.")

        consent = self.catalog.get_latest_consent_for_signer(self.signer_id)
        if consent is None:
            self.state = SessionState.ERROR
            raise ConsentDeniedError(f"No consent record found for participant {self.signer_id!r}")

        validate_video_storage_scope(consent, self.signer_id)
        self._consent = consent
        self.state = SessionState.READY

    def select_task(self, task_id: str) -> ProtocolTask:
        """Select an active protocol task for the recording."""
        for t in self.protocol.tasks:
            if t.task_id == task_id:
                self.active_task = t
                return t
        raise ValueError(f"Task {task_id!r} not found in protocol {self.protocol.protocol_id!r}")

    def start_recording(self) -> None:
        """Gate check before starting recording: re-verify consent freshness."""
        if self._consent is None:
            raise ConsentDeniedError("Cannot record without verified consent.")
        # Re-check from DB to prevent cached authorization on revoked consent
        latest = self.catalog.get_latest_consent_for_signer(self.signer_id)
        if latest is None:
            raise ConsentDeniedError(f"Consent was deleted for signer {self.signer_id!r}")
        validate_video_storage_scope(latest, self.signer_id)
        self._consent = latest
        self.state = SessionState.RECORDING

    def stop_recording(self) -> None:
        """Transition state from RECORDING to READY."""
        if self.state == SessionState.RECORDING:
            self.state = SessionState.READY

    def register_in_catalog(self) -> Session:
        """Register this capture session record into the SQLite catalog."""
        now_utc = datetime.now(UTC).isoformat()
        session_record = Session(
            session_id=self.session_id,
            signer_id=self.signer_id,
            protocol_id=self.protocol.protocol_id,
            recorded_at_utc=now_utc,
            operator_id=self.operator_id,
            metadata_json=f'{{"protocol_mode": "{self.protocol.mode}"}}',
        )
        self.catalog.add_session(session_record)
        return session_record
