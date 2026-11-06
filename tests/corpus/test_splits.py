"""Unit tests for slt_corpus.splits disjointness and leakage validation."""

from __future__ import annotations

import pytest

from slt_corpus.splits import (
    SplitValidationError,
    measure_sentence_overlap,
    validate_group_disjoint,
    validate_no_augmentation_leakage,
)


def test_signers_must_be_disjoint():
    assignments = {
        "train": ["recording_001", "recording_002"],
        "validation": ["recording_003"],
        "test": ["recording_004"],
    }
    signer_by_recording = {
        "recording_001": "signer_A",
        "recording_002": "signer_B",
        "recording_003": "signer_C",
        "recording_004": "signer_D",
    }
    # Clean partition: must succeed without error
    validate_group_disjoint(assignments, signer_by_recording)


def test_signer_leakage_across_splits_raises():
    assignments = {
        "train": ["recording_001"],
        "test": ["recording_002"],
    }
    # Leaking signer_A in both train and test
    signer_by_recording = {
        "recording_001": "signer_A",
        "recording_002": "signer_A",
    }
    with pytest.raises(SplitValidationError, match="leaks across splits"):
        validate_group_disjoint(assignments, signer_by_recording)


def test_recording_in_multiple_splits_raises():
    assignments = {
        "train": ["recording_001"],
        "validation": ["recording_001"],
    }
    signer_by_recording = {
        "recording_001": "signer_A",
    }
    with pytest.raises(SplitValidationError, match="appears in multiple splits"):
        validate_group_disjoint(assignments, signer_by_recording)


def test_augmentation_lineage_no_leakage():
    assignments = {
        "train": ["rec_orig_01", "rec_aug_01"],
        "test": ["rec_orig_02"],
    }
    parent_by_recording = {
        "rec_orig_01": None,
        "rec_aug_01": "rec_orig_01",  # Same split as parent
        "rec_orig_02": None,
    }
    validate_no_augmentation_leakage(assignments, parent_by_recording)


def test_augmentation_leakage_different_splits_raises():
    assignments = {
        "train": ["rec_orig_01"],
        "test": ["rec_aug_01"],
    }
    parent_by_recording = {
        "rec_orig_01": None,
        "rec_aug_01": "rec_orig_01",  # Leaked into test!
    }
    with pytest.raises(SplitValidationError, match="Augmentation leakage"):
        validate_no_augmentation_leakage(assignments, parent_by_recording)


def test_sentence_overlap_measurement():
    assignments = {
        "train": ["r1", "r2"],
        "test": ["r3", "r4"],
    }
    prompt_by_recording = {
        "r1": "HOLA COMO ESTAS",
        "r2": "BUENOS DIAS",
        "r3": "BUENOS DIAS",  # Overlapping prompt
        "r4": "GRACIAS AMIGO",
    }
    report = measure_sentence_overlap(assignments, prompt_by_recording)
    assert report["pairwise_overlap"]["train_vs_test"]["overlap_count"] == 1
    assert "BUENOS DIAS" in report["pairwise_overlap"]["train_vs_test"]["overlapping_prompts"]
