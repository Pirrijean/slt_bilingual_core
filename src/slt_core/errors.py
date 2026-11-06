"""SLT Core Error Definitions."""
from __future__ import annotations


class SLTError(Exception):
    """Base exception for SLT Core."""


class ValidationError(SLTError):
    """Invalid data or configuration."""


class ProfileError(SLTError):
    """Invalid sign language profile."""


class ProfileManifestError(ProfileError):
    """Invalid or missing profile manifest."""


class ComponentNotReadyError(SLTError):
    """A required pipeline component is unavailable."""


class ClosedPipelineError(ComponentNotReadyError):
    """The pipeline has already been closed and cannot process additional frames."""


class ComponentContractError(SLTError):
    """A component returned an invalid result."""


class TimestampOrderError(SLTError):
    """Frames were not supplied in timestamp order."""


class EventOrderError(SLTError):
    """Sign events were supplied in invalid temporal order."""
