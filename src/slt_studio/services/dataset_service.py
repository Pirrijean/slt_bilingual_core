"""Dataset compilation and partition validation service."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import ConsentPurpose, DatasetRelease
from slt_corpus.release import DatasetReleaseManager
from slt_corpus.splits import (
    SplitValidationError,
    validate_group_disjoint,
    validate_no_augmentation_leakage,
)


class DatasetService:
    """Manages partition generation, leak verification, and immutable release building."""

    def __init__(self, catalog: CorpusCatalog, storage_root: str | Path = "data/private/storage") -> None:
        self.catalog = catalog
        self.storage_root = Path(storage_root).resolve()
        self.release_manager = DatasetReleaseManager(catalog, self.storage_root)

    def generate_splits(
        self,
        task: str,
        output_path: str | Path | None = None,
    ) -> dict[str, list[str]]:
        """Create signer-independent train/val/test splits across catalog recordings."""
        recs = self.catalog.list_recordings()
        signers = sorted({r.signer_id for r in recs})
        splits: dict[str, list[str]] = {"train": [], "validation": [], "test": []}

        if len(signers) <= 1:
            splits["train"] = [r.recording_id for r in recs]
        else:
            n_train = max(1, int(len(signers) * 0.7))
            train_signers = set(signers[:n_train])
            val_signers = set(signers[n_train : n_train + 1])

            for r in recs:
                if r.signer_id in train_signers:
                    splits["train"].append(r.recording_id)
                elif r.signer_id in val_signers:
                    splits["validation"].append(r.recording_id)
                else:
                    splits["test"].append(r.recording_id)

        if output_path is not None:
            path = Path(output_path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": "1.0.0",
                "task": task,
                "splits": splits,
            }
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return splits

    def validate_splits(self, splits_path: str | Path) -> tuple[bool, str]:
        """Validate that a splits JSON file exhibits zero signer and augmentation leakage."""
        path = Path(splits_path).resolve()
        if not path.is_file():
            return False, f"File not found: {path}"

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            splits = data.get("splits", data)

            recs = self.catalog.list_recordings()
            signer_by_rec = {r.recording_id: r.signer_id for r in recs}
            parent_by_rec = {r.recording_id: r.parent_recording_id for r in recs}

            validate_group_disjoint(splits, signer_by_rec)
            validate_no_augmentation_leakage(splits, parent_by_rec)
            return True, "VALID: Zero signer overlap and zero augmentation leakage detected."
        except SplitValidationError as se:
            return False, f"LEAK DETECTED: {se}"
        except Exception as exc:
            return False, f"Error validating splits: {exc}"

    def build_release(
        self,
        dataset_id: str,
        dataset_version: str,
        profile_id: str,
        task: str,
        corpus_version: str,
        annotation_schema_version: str,
        usage_scope: ConsentPurpose,
        split_members: Mapping[str, Sequence[str]],
        output_dir: str | Path,
        code_commit: str | None = None,
    ) -> DatasetRelease:
        """Validate eligibility and construct the release manifest using DatasetReleaseManager."""
        return self.release_manager.build_release(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            profile_id=profile_id,
            task=task,
            corpus_version=corpus_version,
            annotation_schema_version=annotation_schema_version,
            usage_scope=usage_scope,
            split_members=split_members,
            output_dir=output_dir,
            code_commit=code_commit,
        )
