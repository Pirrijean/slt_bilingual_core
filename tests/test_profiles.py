"""Unit tests for ProfileRegistry and LanguageProfile validation."""
import json
from pathlib import Path

import pytest

from slt_core.errors import ProfileError, ProfileManifestError
from slt_core.profile_registry import ProfileRegistry


def write_manifest(root: Path, profiles: list[dict], schema_version: int = 1) -> Path:
    profiles_root = root / "profiles" / "sign_languages"
    profiles_root.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": schema_version,
        "profiles": profiles,
    }
    (profiles_root / "manifest.json").write_text(json.dumps(doc), encoding="utf-8")
    return profiles_root


def test_load_profile_without_model(tmp_path: Path):
    prof_dict = {
        "profile_id": "test_lang",
        "display_name": "Test Sign Language",
        "source_language_code": None,
        "vocabulary_version": "1.0.0",
        "output_locales": ["es-CO", "en-US"],
        "capabilities": ["static_signs"],
        "model_manifest": "models/test_lang/manifest.json",
        "vocabulary_file": "vocab.json",
    }
    root = write_manifest(tmp_path, [prof_dict])
    registry = ProfileRegistry(root)

    profile = registry.get_profile("test_lang")
    assert profile.profile_id == "test_lang"
    assert profile.display_name == "Test Sign Language"
    assert "es-CO" in profile.output_locales
    assert "en-US" in profile.output_locales

    # Files do not exist on disk yet
    assert not registry.artifacts_present("test_lang")


def test_artifacts_present_when_files_exist(tmp_path: Path):
    prof_dict = {
        "profile_id": "lsc",
        "display_name": "Lengua de Señas Colombiana",
        "source_language_code": None,
        "vocabulary_version": "1.0.0",
        "output_locales": ["es-CO"],
        "capabilities": ["static_signs"],
        "model_manifest": "model_manifest.json",
        "vocabulary_file": "vocabulary.json",
    }
    root = write_manifest(tmp_path, [prof_dict])

    # Initially false
    registry = ProfileRegistry(root)
    assert not registry.artifacts_present("lsc")

    # Create model manifest only -> still false
    (root / "model_manifest.json").write_text("{}", encoding="utf-8")
    assert not registry.artifacts_present("lsc")

    # Create vocabulary file too -> now True
    (root / "vocabulary.json").write_text("{}", encoding="utf-8")
    assert registry.artifacts_present("lsc")


def test_missing_manifest_raises(tmp_path: Path):
    non_existent = tmp_path / "nowhere"
    non_existent.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ProfileManifestError, match="not found"):
        ProfileRegistry(non_existent)


def test_malformed_json_raises(tmp_path: Path):
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir(parents=True, exist_ok=True)
    (profiles_root / "manifest.json").write_text("{ broken json: ", encoding="utf-8")
    with pytest.raises(ProfileManifestError, match="Failed to read"):
        ProfileRegistry(profiles_root)


def test_invalid_schema_version_raises(tmp_path: Path):
    root = write_manifest(tmp_path, [], schema_version=0)
    with pytest.raises(ProfileManifestError, match="schema_version"):
        ProfileRegistry(root)


def test_duplicate_profile_id_raises(tmp_path: Path):
    prof1 = {
        "profile_id": "lsc",
        "display_name": "Profile 1",
        "vocabulary_version": "1.0",
        "output_locales": ["es-CO"],
    }
    prof2 = {
        "profile_id": "lsc",
        "display_name": "Profile 2",
        "vocabulary_version": "2.0",
        "output_locales": ["es-CO"],
    }
    root = write_manifest(tmp_path, [prof1, prof2])
    with pytest.raises(ProfileManifestError, match="Duplicate profile ID"):
        ProfileRegistry(root)


def test_invalid_profile_id_syntax(tmp_path: Path):
    prof = {
        "profile_id": "INVALID PROFILE ID!",
        "display_name": "Invalid",
        "vocabulary_version": "1.0",
    }
    root = write_manifest(tmp_path, [prof])
    with pytest.raises(ProfileManifestError, match="Invalid profile ID"):
        ProfileRegistry(root)


def test_path_traversal_prevention(tmp_path: Path):
    # Attempt to load a profile with path traversal outside the project directory
    prof = {
        "profile_id": "traversal_attempt",
        "display_name": "Traversal Test",
        "vocabulary_version": "1.0",
        "output_locales": ["es-CO"],
        "model_manifest": "../../../../../../../../../etc/passwd",
    }
    root = write_manifest(tmp_path, [prof])
    with pytest.raises(ProfileManifestError, match="Path traversal"):
        ProfileRegistry(root)


def test_unknown_profile_raises(tmp_path: Path):
    root = write_manifest(tmp_path, [])
    registry = ProfileRegistry(root)

    with pytest.raises(ProfileError, match="not found"):
        registry.get_profile("non_existent")

    with pytest.raises(ProfileError, match="Invalid profile ID"):
        registry.get_profile("../path_traversal")


def test_registry_manifest_structure_errors(tmp_path: Path):
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir(parents=True, exist_ok=True)
    manifest = profiles_root / "manifest.json"

    # Manifest is not a JSON object (e.g. list)
    manifest.write_text("[]", encoding="utf-8")
    with pytest.raises(ProfileManifestError, match="must be a JSON object"):
        ProfileRegistry(profiles_root)

    # Manifest profiles is not a list
    manifest.write_text(json.dumps({"schema_version": 1, "profiles": "not a list"}), encoding="utf-8")
    with pytest.raises(ProfileManifestError, match="'profiles' must be a list"):
        ProfileRegistry(profiles_root)

    # Entry is not a dict
    manifest.write_text(json.dumps({"schema_version": 1, "profiles": ["not a dict"]}), encoding="utf-8")
    with pytest.raises(ProfileManifestError, match="must be a JSON object"):
        ProfileRegistry(profiles_root)

    # Entry has invalid LanguageProfile spec (e.g. empty display name)
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "profiles": [{"profile_id": "test", "display_name": "", "vocabulary_version": "1.0"}]
    }), encoding="utf-8")
    with pytest.raises(ProfileManifestError, match="Invalid profile specification"):
        ProfileRegistry(profiles_root)


def test_registry_entries_and_safe_path(tmp_path: Path):
    prof = {
        "profile_id": "lsc",
        "display_name": "LSC",
        "vocabulary_version": "1.0",
        "output_locales": ["es-CO"],
        "model_manifest": str(tmp_path / "model.json"),  # absolute path inside project
    }
    root = write_manifest(tmp_path, [prof])
    registry = ProfileRegistry(root)

    entries = registry.list_entries()
    assert len(entries) == 1
    assert entries[0].profile.profile_id == "lsc"


def test_registry_listing_and_contains(tmp_path: Path):
    prof1 = {
        "profile_id": "lsc",
        "display_name": "LSC",
        "vocabulary_version": "1.0",
        "output_locales": ["es-CO"],
    }
    prof2 = {
        "profile_id": "asl",
        "display_name": "ASL",
        "vocabulary_version": "1.0",
        "output_locales": ["en-US"],
    }
    root = write_manifest(tmp_path, [prof1, prof2])
    registry = ProfileRegistry(root)

    assert len(registry) == 2
    assert "lsc" in registry
    assert "asl" in registry
    assert "fsl" not in registry

    profiles = registry.list_profiles()
    assert len(profiles) == 2
    assert {p.profile_id for p in profiles} == {"lsc", "asl"}
