"""ELAN (.eaf) XML adapter for SLT linguistic annotation import.

Parses ELAN 2.8 / 3.0 EAF documents, resolves time slots in milliseconds,
converts strictly to nanoseconds (t_ns = t_ms * 10^6), inherits timing for
hierarchical REF_ANNOTATIONs, and produces validated Annotation domain entities.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from slt_corpus.domain import Annotation, AnnotationStatus, BoundaryQuality


class EAFImportError(ValueError):
    """Raised when an ELAN .eaf document violates XML schema or timing rules."""


@dataclass(frozen=True, slots=True)
class EAFRecord:
    """Intermediate representation of an parsed annotation tier from an EAF."""

    annotation_id: str
    tier_id: str
    start_ns: int
    end_ns: int
    value: str
    parent_annotation_id: str | None = None


def import_eaf(eaf_path: str | Path) -> list[EAFRecord]:
    """Parse an ELAN .eaf file and extract all annotations with nanosecond timing.

    Args:
        eaf_path: Path to the .eaf XML document.

    Returns:
        List of EAFRecord instances preserving tier and parent relationships.

    Raises:
        FileNotFoundError: If the .eaf file does not exist.
        EAFImportError: If the XML is malformed, time slots are missing,
            or intervals are invalid.
    """
    path = Path(eaf_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"EAF file not found: {path}")

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as exc:
        raise EAFImportError(f"Malformed XML in EAF file {path.name}: {exc}") from exc

    # 1. Parse TIME_ORDER time slots (time values are in milliseconds)
    time_slots: dict[str, int] = {}
    time_order_elem = root.find("TIME_ORDER")
    if time_order_elem is not None:
        for slot in time_order_elem.findall("TIME_SLOT"):
            slot_id = slot.get("TIME_SLOT_ID")
            val_str = slot.get("TIME_VALUE")
            if slot_id and val_str is not None:
                try:
                    time_slots[slot_id] = int(val_str)
                except ValueError:
                    pass

    # First pass: collect all alignable annotations
    alignable_records: dict[str, EAFRecord] = {}
    # Second pass items: ref annotations needing parent resolution
    ref_elements: list[tuple[str, ET.Element]] = []

    for tier in root.findall("TIER"):
        tier_id = tier.get("TIER_ID")
        if not tier_id:
            continue

        for ann in tier.findall("ANNOTATION"):
            alignable = ann.find("ALIGNABLE_ANNOTATION")
            if alignable is not None:
                ann_id = alignable.get("ANNOTATION_ID")
                ts_ref1 = alignable.get("TIME_SLOT_REF1")
                ts_ref2 = alignable.get("TIME_SLOT_REF2")
                val_elem = alignable.find("ANNOTATION_VALUE")
                value = val_elem.text.strip() if val_elem is not None and val_elem.text else ""

                if not ann_id or not ts_ref1 or not ts_ref2:
                    raise EAFImportError(
                        f"Alignable annotation missing required attributes in tier {tier_id!r}"
                    )

                if ts_ref1 not in time_slots or ts_ref2 not in time_slots:
                    raise EAFImportError(
                        f"Annotation {ann_id!r} references missing time slot "
                        f"({ts_ref1!r} or {ts_ref2!r})"
                    )

                t_start_ms = time_slots[ts_ref1]
                t_end_ms = time_slots[ts_ref2]
                if t_start_ms < 0:
                    raise EAFImportError(f"Negative start time in annotation {ann_id!r}: {t_start_ms}")
                if t_end_ms <= t_start_ms:
                    raise EAFImportError(
                        f"Invalid time interval in annotation {ann_id!r}: {t_start_ms} >= {t_end_ms}"
                    )

                start_ns = t_start_ms * 1_000_000
                end_ns = t_end_ms * 1_000_000

                record = EAFRecord(
                    annotation_id=ann_id,
                    tier_id=tier_id,
                    start_ns=start_ns,
                    end_ns=end_ns,
                    value=value,
                    parent_annotation_id=None,
                )
                alignable_records[ann_id] = record
            else:
                ref = ann.find("REF_ANNOTATION")
                if ref is not None:
                    ref_elements.append((tier_id, ref))

    # Second pass: resolve REF_ANNOTATIONs against parent alignable annotations
    ref_records: dict[str, EAFRecord] = {}
    unresolved = ref_elements
    iteration = 0
    max_iterations = 10  # Prevent infinite loops in cyclic or deep ref hierarchies

    while unresolved and iteration < max_iterations:
        next_unresolved = []
        for tier_id, ref in unresolved:
            ann_id = ref.get("ANNOTATION_ID")
            parent_ref = ref.get("ANNOTATION_REF")
            val_elem = ref.find("ANNOTATION_VALUE")
            value = val_elem.text.strip() if val_elem is not None and val_elem.text else ""

            if not ann_id or not parent_ref:
                raise EAFImportError(f"REF_ANNOTATION missing ID or parent reference in tier {tier_id!r}")

            parent_record = alignable_records.get(parent_ref) or ref_records.get(parent_ref)
            if parent_record is not None:
                record = EAFRecord(
                    annotation_id=ann_id,
                    tier_id=tier_id,
                    start_ns=parent_record.start_ns,
                    end_ns=parent_record.end_ns,
                    value=value,
                    parent_annotation_id=parent_ref,
                )
                ref_records[ann_id] = record
            else:
                next_unresolved.append((tier_id, ref))
        unresolved = next_unresolved
        iteration += 1

    if unresolved:
        missing_ids = [ref.get("ANNOTATION_ID") for _, ref in unresolved]
        raise EAFImportError(f"Unresolvable parent references for annotations: {missing_ids}")

    all_records = list(alignable_records.values()) + list(ref_records.values())
    all_records.sort(key=lambda r: (r.start_ns, r.end_ns, r.tier_id))
    return all_records


def to_slt_annotations(
    records: Sequence[EAFRecord],
    document_id: str,
    annotator_id: str | None = None,
    default_status: AnnotationStatus = AnnotationStatus.DRAFT,
) -> list[Annotation]:
    """Convert EAFRecord instances into validated Annotation domain models."""
    return [
        Annotation(
            annotation_id=rec.annotation_id,
            document_id=document_id,
            tier_id=rec.tier_id,
            start_ns=rec.start_ns,
            end_ns=rec.end_ns,
            value=rec.value,
            parent_annotation_id=rec.parent_annotation_id,
            boundary_quality=BoundaryQuality.EXACT,
            status=default_status,
            annotator_id=annotator_id,
            revision=1,
        )
        for rec in records
    ]
