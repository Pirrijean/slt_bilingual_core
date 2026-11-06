"""Pytest configuration and fixtures for SLT Core testing."""
import pytest

from slt_core.domain import LanguageProfile


@pytest.fixture
def test_profile() -> LanguageProfile:
    """Fixture providing a test sign language profile."""
    return LanguageProfile(
        profile_id="test_sign_language",
        display_name="Test Sign Language",
        source_language_code=None,
        vocabulary_version="test-1.0",
        output_locales=("es-CO", "en-US"),
        capabilities=frozenset({
            "static_signs",
            "dynamic_signs",
            "continuous_sequences",
        }),
    )
