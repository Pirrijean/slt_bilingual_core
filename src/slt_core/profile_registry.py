"""SLT Core Profile Registry."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from slt_core.domain import LanguageProfile
from slt_core.errors import ProfileError, ProfileManifestError

PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass(frozen=True, slots=True)
class ProfileEntry:
    """Registry entry for a sign language profile and its associated files."""

    profile: LanguageProfile
    recognition_manifest_path: Path | None
    vocabulary_path: Path | None

    @property
    def artifacts_present(self) -> bool:
        """True only if both the recognition manifest and vocabulary files exist."""
        return (
            self.recognition_manifest_path is not None
            and self.recognition_manifest_path.is_file()
            and self.vocabulary_path is not None
            and self.vocabulary_path.is_file()
        )


class ProfileRegistry:
    """Manages sign language profiles and their filesystem artifacts."""

    def __init__(self, profiles_root: Path | str) -> None:
        self.profiles_root = Path(profiles_root).resolve()
        self._profiles: dict[str, ProfileEntry] = {}
        self.load_manifest()

    def load_manifest(self) -> None:
        """Load and validate manifest.json from the profiles root."""
        manifest_file = self.profiles_root / "manifest.json"
        if not manifest_file.is_file():
            raise ProfileManifestError(f"Manifest file not found: {manifest_file}")

        try:
            content = manifest_file.read_text(encoding="utf-8")
            data = json.loads(content)
        except (json.JSONDecodeError, OSError) as exc:
            raise ProfileManifestError(f"Failed to read manifest JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise ProfileManifestError("Manifest must be a JSON object.")

        schema_version = data.get("schema_version")
        if not isinstance(schema_version, int) or schema_version < 1:
            raise ProfileManifestError("Invalid or missing schema_version.")

        profiles_data = data.get("profiles")
        if not isinstance(profiles_data, list):
            raise ProfileManifestError("Manifest 'profiles' must be a list.")

        self._profiles.clear()
        for item in profiles_data:
            if not isinstance(item, dict):
                raise ProfileManifestError("Each profile entry must be a JSON object.")

            profile_id = item.get("profile_id")
            if not isinstance(profile_id, str) or not PROFILE_ID_PATTERN.fullmatch(profile_id):
                raise ProfileManifestError(f"Invalid profile ID: {profile_id}")

            if profile_id in self._profiles:
                raise ProfileManifestError(f"Duplicate profile ID: {profile_id}")

            try:
                profile = LanguageProfile(
                    profile_id=profile_id,
                    display_name=item.get("display_name", ""),
                    source_language_code=item.get("source_language_code"),
                    vocabulary_version=item.get("vocabulary_version", ""),
                    output_locales=tuple(item.get("output_locales", ())),
                    capabilities=frozenset(item.get("capabilities", ())),
                )
            except Exception as exc:
                raise ProfileManifestError(f"Invalid profile specification for '{profile_id}': {exc}") from exc

            model_manifest_raw = item.get("model_manifest")
            model_manifest_path = self._resolve_safe_path(model_manifest_raw) if model_manifest_raw else None

            vocab_raw = item.get("vocabulary_file")
            vocab_path = self._resolve_safe_path(vocab_raw) if vocab_raw else None

            self._profiles[profile_id] = ProfileEntry(
                profile=profile,
                recognition_manifest_path=model_manifest_path,
                vocabulary_path=vocab_path,
            )

    def _resolve_safe_path(self, rel_path: str) -> Path:
        """Resolve a relative path, rejecting any path traversal outside the project directory."""
        path_obj = Path(rel_path)
        if path_obj.is_absolute():
            resolved = path_obj.resolve()
        else:
            resolved = (self.profiles_root / path_obj).resolve()

        # Path traversal guard: ensure path is within profiles_root or parent project
        # and doesn't resolve to an invalid root
        try:
            # Path traversal guard: must be within profiles_root or project ancestors
            is_safe = False
            curr = self.profiles_root
            for _ in range(4):
                if resolved == curr or curr in resolved.parents:
                    is_safe = True
                    break
                curr = curr.parent
            if not is_safe:
                raise ProfileManifestError(f"Path traversal detected: {rel_path}")
        except (ValueError, OSError) as exc:
            raise ProfileManifestError(f"Path traversal detected: {rel_path}") from exc

        return resolved

    def get_entry(self, profile_id: str) -> ProfileEntry:
        """Retrieve the ProfileEntry for a given profile_id."""
        if not PROFILE_ID_PATTERN.fullmatch(profile_id):
            raise ProfileError(f"Invalid profile ID syntax: {profile_id}")
        if profile_id not in self._profiles:
            raise ProfileError(f"Profile not found: {profile_id}")
        return self._profiles[profile_id]

    def get_profile(self, profile_id: str) -> LanguageProfile:
        """Retrieve the LanguageProfile for a given profile_id."""
        return self.get_entry(profile_id).profile

    def artifacts_present(self, profile_id: str) -> bool:
        """Check whether the model manifest and vocabulary files exist on disk."""
        return self.get_entry(profile_id).artifacts_present

    def list_profiles(self) -> tuple[LanguageProfile, ...]:
        """Return all registered profiles."""
        return tuple(entry.profile for entry in self._profiles.values())

    def list_entries(self) -> tuple[ProfileEntry, ...]:
        """Return all registered profile entries."""
        return tuple(self._profiles.values())

    def __contains__(self, profile_id: str) -> bool:
        return profile_id in self._profiles

    def __len__(self) -> int:
        return len(self._profiles)
