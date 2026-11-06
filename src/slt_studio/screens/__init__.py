"""Screens for Dataset Studio interface."""

from __future__ import annotations

from slt_studio.screens.adjudication import AdjudicationScreen
from slt_studio.screens.annotations import AnnotationsScreen
from slt_studio.screens.builder import DatasetBuilderScreen
from slt_studio.screens.capture import CaptureScreen
from slt_studio.screens.consent import ConsentScreen
from slt_studio.screens.dashboard import DashboardScreen
from slt_studio.screens.participants import ParticipantsScreen
from slt_studio.screens.recordings import RecordingsScreen
from slt_studio.screens.release import ReleaseScreen
from slt_studio.screens.review import ReviewScreen
from slt_studio.screens.splits import SplitValidationScreen

__all__ = [
    "AdjudicationScreen",
    "AnnotationsScreen",
    "CaptureScreen",
    "ConsentScreen",
    "DashboardScreen",
    "DatasetBuilderScreen",
    "ParticipantsScreen",
    "RecordingsScreen",
    "ReleaseScreen",
    "ReviewScreen",
    "SplitValidationScreen",
]
