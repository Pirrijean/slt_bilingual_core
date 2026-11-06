"""Dataset split integrity and data leakage validation.

Enforces signer-independent and sentence-disjoint partitioning constraints,
verifying that no participant or augmented derivative leaks across
train/validation/test splits.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


class SplitValidationError(ValueError):
    """Raised when dataset split integrity or leakage invariants are violated."""


def validate_group_disjoint(
    split_members: Mapping[str, Sequence[str]],
    group_by_recording: Mapping[str, str],
) -> None:
    """Validate that groupings (e.g. signers) are strictly disjoint across splits.

    Args:
        split_members: Mapping from split name ('train', 'validation', 'test')
            to sequences of recording IDs.
        group_by_recording: Mapping from recording ID to group ID (e.g. signer_id).

    Raises:
        SplitValidationError: If a recording is unknown, appears in multiple splits,
            or if a group (signer) is observed in more than one split.
    """
    group_owner: dict[str, str] = {}
    recording_owner: dict[str, str] = {}

    for split_name, recording_ids in split_members.items():
        for recording_id in recording_ids:
            if recording_id not in group_by_recording:
                raise SplitValidationError(
                    f"Unknown recording {recording_id!r} not found in group mapping."
                )
            if recording_id in recording_owner:
                prior_split = recording_owner[recording_id]
                raise SplitValidationError(
                    f"Recording {recording_id!r} appears in multiple splits: "
                    f"{prior_split!r} and {split_name!r}"
                )
            recording_owner[recording_id] = split_name

            group_id = group_by_recording[recording_id]
            if group_id in group_owner and group_owner[group_id] != split_name:
                prior_split = group_owner[group_id]
                raise SplitValidationError(
                    f"Signer/Group {group_id!r} leaks across splits: "
                    f"assigned to both {prior_split!r} and {split_name!r}."
                )
            group_owner[group_id] = split_name


def validate_no_augmentation_leakage(
    split_members: Mapping[str, Sequence[str]],
    parent_by_recording: Mapping[str, str | None],
) -> None:
    """Validate that every augmented sample resides in the same split as its parent recording.

    Args:
        split_members: Mapping from split name to sequences of recording IDs.
        parent_by_recording: Mapping from recording ID to parent_recording_id (or None if original).

    Raises:
        SplitValidationError: If an augmented recording is in a different split
            than its parent or if parent is omitted.
    """
    recording_split: dict[str, str] = {}
    for split_name, recording_ids in split_members.items():
        for rec_id in recording_ids:
            recording_split[rec_id] = split_name

    for rec_id, split_name in recording_split.items():
        parent_id = parent_by_recording.get(rec_id)
        if parent_id is not None:
            if parent_id not in recording_split:
                raise SplitValidationError(
                    f"Augmented recording {rec_id!r} is in split {split_name!r}, "
                    f"but its parent {parent_id!r} is not in any split."
                )
            parent_split = recording_split[parent_id]
            if parent_split != split_name:
                raise SplitValidationError(
                    f"Augmentation leakage: recording {rec_id!r} is in split {split_name!r}, "
                    f"but its parent {parent_id!r} is in {parent_split!r}."
                )


def measure_sentence_overlap(
    split_members: Mapping[str, Sequence[str]],
    prompt_by_recording: Mapping[str, str],
) -> dict[str, Any]:
    """Measure prompt / sentence overlap across dataset splits.

    Returns:
        Dictionary reporting unique prompt counts per split and pair-wise intersection sets.
    """
    prompts_per_split: dict[str, set[str]] = defaultdict(set)
    for split_name, rec_ids in split_members.items():
        for rec_id in rec_ids:
            if rec_id in prompt_by_recording:
                prompts_per_split[split_name].add(prompt_by_recording[rec_id])

    splits = list(split_members.keys())
    overlaps: dict[str, Any] = {
        "unique_prompts_per_split": {s: len(p) for s, p in prompts_per_split.items()},
        "pairwise_overlap": {},
    }

    for i in range(len(splits)):
        for j in range(i + 1, len(splits)):
            s1, s2 = splits[i], splits[j]
            intersection = prompts_per_split[s1].intersection(prompts_per_split[s2])
            pair_key = f"{s1}_vs_{s2}"
            overlaps["pairwise_overlap"][pair_key] = {
                "overlap_count": len(intersection),
                "overlapping_prompts": sorted(intersection),
            }

    return overlaps
