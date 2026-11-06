"""Dataset split integrity and data leakage validation.

Enforces signer-independent, sentence-disjoint, and multi-dimensional partitioning constraints,
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
    groups_by_recording: Mapping[str, Mapping[str, Sequence[str]] | str],
    required_dimensions: Sequence[str] | None = None,
) -> None:
    """Validate that groupings (e.g. signers, prompts) are strictly disjoint across splits.

    Supports both:
    1. Multi-dimensional dictionary grouping:
       groups_by_recording = {"rec1": {"signer_id": ["s1"], "prompt_id": ["p1"]}}
       with explicit required_dimensions=("signer_id", "prompt_id").
    2. Single-dimension string grouping (backward compatible):
       groups_by_recording = {"rec1": "s1"} with optional or omitted required_dimensions.

    Args:
        split_members: Mapping from split name ('train', 'validation', 'test')
            to sequences of recording IDs.
        groups_by_recording: Mapping from recording ID to either a group identifier
            string or a dictionary of dimension names to group ID sequences.
        required_dimensions: Optional sequence of dimension names to validate. If
            provided, must be non-empty.

    Raises:
        SplitValidationError: If a recording is unknown, appears in multiple splits,
            or if a group dimension leaks across splits.
    """
    if required_dimensions is not None and not required_dimensions:
        raise SplitValidationError("At least one grouping dimension is required.")

    recording_owner: dict[str, str] = {}
    group_owners: dict[str, dict[str, str]] = defaultdict(dict)

    for split_name, recordings in split_members.items():
        for recording_id in recordings:
            if recording_id not in groups_by_recording:
                raise SplitValidationError(f"Unknown recording: {recording_id}")

            previous_split = recording_owner.get(recording_id)
            if previous_split is not None:
                raise SplitValidationError(
                    f"Recording {recording_id!r} appears in multiple splits: "
                    f"{previous_split!r} and {split_name!r}"
                )
            recording_owner[recording_id] = split_name

            raw_group_data = groups_by_recording[recording_id]

            if isinstance(raw_group_data, str):
                # Simple string mapping mode
                group_id = raw_group_data
                dim = "signer_id" if required_dimensions is None else required_dimensions[0]
                prev_owner = group_owners[dim].get(group_id)
                if prev_owner is not None and prev_owner != split_name:
                    raise SplitValidationError(
                        f"Signer/Group {group_id!r} leaks across splits: "
                        f"assigned to both {prev_owner!r} and {split_name!r}."
                    )
                group_owners[dim][group_id] = split_name
            else:
                # Multi-dimensional grouping dictionary mode
                dimensions_to_check = (
                    required_dimensions
                    if required_dimensions is not None
                    else list(raw_group_data.keys())
                )
                if not dimensions_to_check:
                    raise SplitValidationError("At least one grouping dimension is required.")

                for dimension in dimensions_to_check:
                    group_ids_raw = raw_group_data.get(dimension)
                    if not group_ids_raw:
                        raise SplitValidationError(
                            f"Missing {dimension} for {recording_id}"
                        )

                    group_ids: Sequence[str] = (
                        [group_ids_raw] if isinstance(group_ids_raw, str) else group_ids_raw
                    )
                    for group_id in group_ids:
                        if not group_id:
                            raise SplitValidationError(
                                f"Empty group ID for {recording_id}"
                            )
                        previous_owner = group_owners[dimension].get(group_id)
                        if previous_owner is not None and previous_owner != split_name:
                            raise SplitValidationError(
                                f"{dimension} leakage: {group_id} "
                                f"appears in {previous_owner} and {split_name}."
                            )
                        group_owners[dimension][group_id] = split_name


def validate_augmentation_lineage(
    split_members: Mapping[str, Sequence[str]],
    parent_recording_by_sample: Mapping[str, str],
    split_by_recording: Mapping[str, str],
) -> None:
    """Validate that augmented derivatives are strictly co-located with their parent recording.

    Args:
        split_members: Mapping from split name to sequences of sample/recording IDs.
        parent_recording_by_sample: Mapping from sample ID to parent recording ID.
        split_by_recording: Mapping from recording ID to assigned split name.

    Raises:
        SplitValidationError: If sample has no parent, parent is absent from splits,
            or sample is in a different split than its parent.
    """
    for split_name, samples in split_members.items():
        for sample_id in samples:
            parent = parent_recording_by_sample.get(sample_id)
            if parent is None:
                raise SplitValidationError(
                    f"Sample has no parent recording: {sample_id}"
                )
            parent_split = split_by_recording.get(parent)
            if parent_split is None:
                raise SplitValidationError(
                    f"Parent recording is absent from all splits: {parent}"
                )
            if parent_split != split_name:
                raise SplitValidationError(
                    f"Augmented sample {sample_id} is in {split_name}, "
                    f"but its parent is in {parent_split}."
                )


def validate_no_augmentation_leakage(
    split_members: Mapping[str, Sequence[str]],
    parent_by_recording: Mapping[str, str | None],
) -> None:
    """Validate that every augmented sample resides in the same split as its parent recording."""
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
