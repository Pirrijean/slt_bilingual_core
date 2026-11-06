"""Unit tests for slt_corpus.elan XML import and nanosecond conversion."""

from __future__ import annotations

from pathlib import Path

import pytest

from slt_corpus.domain import AlignmentKind
from slt_corpus.elan import EAFImportError, import_eaf, to_slt_annotations

SYNTHETIC_EAF = """<?xml version="1.0" encoding="UTF-8"?>
<ANNOTATION_DOCUMENT AUTHOR="test_annotator" DATE="2026-11-06T10:00:00+00:00" FORMAT="3.0" VERSION="3.0">
    <HEADER MEDIA_FILE="sample.mp4" TIME_UNITS="milliseconds"/>
    <TIME_ORDER>
        <TIME_SLOT TIME_SLOT_ID="ts1" TIME_VALUE="100"/>
        <TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="800"/>
        <TIME_SLOT TIME_SLOT_ID="ts3" TIME_VALUE="1200"/>
        <TIME_SLOT TIME_SLOT_ID="ts4" TIME_VALUE="2000"/>
    </TIME_ORDER>
    <TIER TIER_ID="sign_token">
        <ANNOTATION>
            <ALIGNABLE_ANNOTATION ANNOTATION_ID="a1" TIME_SLOT_REF1="ts1" TIME_SLOT_REF2="ts2">
                <ANNOTATION_VALUE>HOLA</ANNOTATION_VALUE>
            </ALIGNABLE_ANNOTATION>
        </ANNOTATION>
        <ANNOTATION>
            <ALIGNABLE_ANNOTATION ANNOTATION_ID="a2" TIME_SLOT_REF1="ts3" TIME_SLOT_REF2="ts4">
                <ANNOTATION_VALUE>GRACIAS</ANNOTATION_VALUE>
            </ALIGNABLE_ANNOTATION>
        </ANNOTATION>
    </TIER>
    <TIER TIER_ID="translation_es" PARENT_REF="sign_token">
        <ANNOTATION>
            <REF_ANNOTATION ANNOTATION_ID="a3" ANNOTATION_REF="a1">
                <ANNOTATION_VALUE>hola amigo</ANNOTATION_VALUE>
            </REF_ANNOTATION>
        </ANNOTATION>
    </TIER>
</ANNOTATION_DOCUMENT>
"""


def test_import_basic_eaf(tmp_path: Path):
    eaf_file = tmp_path / "sample.eaf"
    eaf_file.write_text(SYNTHETIC_EAF, encoding="utf-8")

    records = import_eaf(eaf_file)
    assert len(records) == 3

    # Check nanosecond conversion: 100 ms -> 100_000_000 ns
    rec_a1 = next(r for r in records if r.annotation_id == "a1")
    assert rec_a1.start_ns == 100_000_000
    assert rec_a1.end_ns == 800_000_000
    assert rec_a1.value == "HOLA"
    assert rec_a1.tier_id == "sign_token"

    # Check REF_ANNOTATION non-aligned semantics (no synthetic timing inheritance)
    rec_a3 = next(r for r in records if r.annotation_id == "a3")
    assert rec_a3.start_ns is None
    assert rec_a3.end_ns is None
    assert rec_a3.alignment_kind == AlignmentKind.REFERENCE
    assert rec_a3.value == "hola amigo"
    assert rec_a3.parent_source_annotation_id == "a1"

    # Convert to SLT Annotations with deterministic UUID5 internal IDs
    slt_anns = to_slt_annotations(records, document_id="doc_test_01", recording_id="rec_test_01")
    assert len(slt_anns) == 3
    assert slt_anns[0].document_id == "doc_test_01"
    ann_a1 = next(a for a in slt_anns if a.source_annotation_id == "a1")
    ann_a3 = next(a for a in slt_anns if a.source_annotation_id == "a3")
    assert ann_a3.alignment_kind == AlignmentKind.REFERENCE
    assert ann_a3.start_ns is None
    assert ann_a3.end_ns is None
    assert ann_a3.parent_annotation_id == ann_a1.annotation_id


def test_import_eaf_missing_timeslot_raises(tmp_path: Path):
    broken_eaf = """<?xml version="1.0" encoding="UTF-8"?>
    <ANNOTATION_DOCUMENT FORMAT="3.0">
        <TIME_ORDER>
            <TIME_SLOT TIME_SLOT_ID="ts1" TIME_VALUE="100"/>
        </TIME_ORDER>
        <TIER TIER_ID="sign_token">
            <ANNOTATION>
                <ALIGNABLE_ANNOTATION ANNOTATION_ID="a1" TIME_SLOT_REF1="ts1" TIME_SLOT_REF2="missing_ts">
                    <ANNOTATION_VALUE>HOLA</ANNOTATION_VALUE>
                </ALIGNABLE_ANNOTATION>
            </ANNOTATION>
        </TIER>
    </ANNOTATION_DOCUMENT>
    """
    eaf_file = tmp_path / "broken.eaf"
    eaf_file.write_text(broken_eaf, encoding="utf-8")

    with pytest.raises(EAFImportError, match="references missing time slot"):
        import_eaf(eaf_file)


def test_import_eaf_negative_or_inverted_time_raises(tmp_path: Path):
    inverted_eaf = """<?xml version="1.0" encoding="UTF-8"?>
    <ANNOTATION_DOCUMENT FORMAT="3.0">
        <TIME_ORDER>
            <TIME_SLOT TIME_SLOT_ID="ts1" TIME_VALUE="500"/>
            <TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="200"/>
        </TIME_ORDER>
        <TIER TIER_ID="sign_token">
            <ANNOTATION>
                <ALIGNABLE_ANNOTATION ANNOTATION_ID="a1" TIME_SLOT_REF1="ts1" TIME_SLOT_REF2="ts2">
                    <ANNOTATION_VALUE>TEST</ANNOTATION_VALUE>
                </ALIGNABLE_ANNOTATION>
            </ANNOTATION>
        </TIER>
    </ANNOTATION_DOCUMENT>
    """
    eaf_file = tmp_path / "inverted.eaf"
    eaf_file.write_text(inverted_eaf, encoding="utf-8")

    with pytest.raises(EAFImportError, match="Invalid time interval"):
        import_eaf(eaf_file)
