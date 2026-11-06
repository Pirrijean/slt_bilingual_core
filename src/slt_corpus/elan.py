"""ELAN (.eaf) XML adapter for SLT linguistic annotation import.

Parses ELAN 2.8 / 3.0 EAF documents securely via defusedxml.
Preserves ALIGNABLE_ANNOTATION vs REF_ANNOTATION semantics without synthetic
timing inheritance (REF_ANNOTATION has start_ns=None, end_ns=None).
Generates deterministic UUID5 internal annotation IDs while preserving the
original EAF ID in source_annotation_id.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree as ET

from slt_corpus.domain import (
    AlignmentKind,
    Annotation,
    AnnotationStatus,
    BoundaryQuality,
)


class EAFImportError(ValueError):
    """Raised when an ELAN .eaf document violates XML schema or timing rules."""


@dataclass(frozen=True, slots=True)
class EAFTier:
    """Tier specification extracted from an EAF document."""

    tier_id: str
    parent_ref: str | None = None
    linguistic_type_ref: str | None = None
    constraint_stereotype: str | None = None


@dataclass(frozen=True, slots=True)
class EAFAnnotation:
    """Intermediate representation of an parsed annotation tier from an EAF."""

    source_annotation_id: str
    tier_id: str
    alignment_kind: AlignmentKind
    start_ns: int | None
    end_ns: int | None
    value: str
    parent_source_annotation_id: str | None = None
    previous_source_annotation_id: str | None = None
    linguistic_type_ref: str | None = None
    constraint_stereotype: str | None = None

    @property
    def annotation_id(self) -> str:
        """Alias for backward compatibility with EAFRecord."""
        return self.source_annotation_id

    @property
    def parent_annotation_id(self) -> str | None:
        """Alias for backward compatibility with EAFRecord."""
        return self.parent_source_annotation_id


# Alias for backward compatibility
EAFRecord = EAFAnnotation


@dataclass(frozen=True, slots=True)
class EAFDocument:
    """Container for parsed EAF document structure, tiers, and annotations."""

    format_version: str | None
    tiers: tuple[EAFTier, ...]
    annotations: tuple[EAFAnnotation, ...]
    time_unit: str = "milliseconds"

    def __iter__(self) -> Iterator[EAFAnnotation]:
        return iter(self.annotations)

    def __len__(self) -> int:
        return len(self.annotations)

    def __getitem__(self, index: int) -> EAFAnnotation:
        return self.annotations[index]


def import_eaf(
    path: str | Path,
    max_file_size_bytes: int = 100_000_000,
) -> EAFDocument:
    """Safely parse an ELAN .eaf document and return structured document entities.

    Args:
        path: Path to the .eaf XML document.
        max_file_size_bytes: Maximum permitted file size in bytes to prevent DoS.

    Returns:
        EAFDocument containing tiers and annotations.

    Raises:
        FileNotFoundError: If the .eaf file does not exist.
        EAFImportError: If the XML is malformed, size exceeds limit, time slots
            are missing, or interval constraints are violated.
    """
    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"EAF file does not exist: {file_path}")

    if file_path.stat().st_size > max_file_size_bytes:
        raise EAFImportError(
            f"EAF file exceeds size limit of {max_file_size_bytes} bytes."
        )

    try:
        root = ET.parse(file_path).getroot()
    except Exception as exc:
        raise EAFImportError(f"Unable to parse EAF XML in {file_path.name}: {exc}") from exc

    if root.tag != "ANNOTATION_DOCUMENT":
        raise EAFImportError(f"Invalid EAF root element: {root.tag!r}")

    # 1. Parse time slots (stored in milliseconds)
    time_slots: dict[str, int | None] = {}
    time_order_elem = root.find("TIME_ORDER")
    if time_order_elem is not None:
        for slot in time_order_elem.findall("TIME_SLOT"):
            slot_id = slot.attrib.get("TIME_SLOT_ID")
            if not slot_id:
                raise EAFImportError("TIME_SLOT without ID attribute.")
            raw_time = slot.attrib.get("TIME_VALUE")
            if raw_time is None:
                time_slots[slot_id] = None
                continue
            try:
                milliseconds = int(raw_time)
            except ValueError as exc:
                raise EAFImportError(f"Invalid TIME_VALUE {raw_time!r} in slot {slot_id!r}") from exc
            if milliseconds < 0:
                raise EAFImportError(f"Negative EAF time value in slot {slot_id!r}: {milliseconds}")
            time_slots[slot_id] = milliseconds * 1_000_000

    # 2. Parse linguistic types and constraints
    linguistic_types: dict[str, str | None] = {}
    for item in root.findall("LINGUISTIC_TYPE"):
        type_id = item.attrib.get("LINGUISTIC_TYPE_ID")
        if not type_id:
            raise EAFImportError("LINGUISTIC_TYPE without ID attribute.")
        linguistic_types[type_id] = item.attrib.get("CONSTRAINTS")

    # 3. Parse tiers
    tiers: dict[str, EAFTier] = {}
    for element in root.findall("TIER"):
        tier_id = element.attrib.get("TIER_ID")
        if not tier_id:
            raise EAFImportError("TIER without ID attribute.")
        type_ref = element.attrib.get("LINGUISTIC_TYPE_REF")
        tiers[tier_id] = EAFTier(
            tier_id=tier_id,
            parent_ref=element.attrib.get("PARENT_REF"),
            linguistic_type_ref=type_ref,
            constraint_stereotype=linguistic_types.get(type_ref) if type_ref else None,
        )

    # 4. Parse annotations
    output: list[EAFAnnotation] = []
    source_ids: set[str] = set()
    pending_references: list[EAFAnnotation] = []

    for tier_element in root.findall("TIER"):
        tier_id = tier_element.attrib["TIER_ID"]
        tier = tiers[tier_id]

        for wrapper in tier_element.findall("ANNOTATION"):
            children = list(wrapper)
            if len(children) != 1:
                raise EAFImportError("Invalid annotation wrapper: expected exactly 1 child.")
            node = children[0]
            source_id = node.attrib.get("ANNOTATION_ID")
            if not source_id:
                raise EAFImportError("Annotation without ANNOTATION_ID.")
            if source_id in source_ids:
                raise EAFImportError(f"Duplicate EAF annotation ID: {source_id!r}")
            source_ids.add(source_id)

            value_element = node.find("ANNOTATION_VALUE")
            value = (
                "".join(value_element.itertext()).strip()
                if value_element is not None
                else ""
            )

            if node.tag == "ALIGNABLE_ANNOTATION":
                slot1 = node.attrib.get("TIME_SLOT_REF1")
                slot2 = node.attrib.get("TIME_SLOT_REF2")
                if not slot1 or not slot2:
                    raise EAFImportError(f"Alignable annotation {source_id!r} missing time slot references.")
                if slot1 not in time_slots or slot2 not in time_slots:
                    raise EAFImportError(
                        f"Annotation {source_id!r} references missing time slot "
                        f"({slot1!r} or {slot2!r})"
                    )

                start_ns = time_slots[slot1]
                end_ns = time_slots[slot2]

                if start_ns is None or end_ns is None:
                    alignment_kind = AlignmentKind.UNRESOLVED
                else:
                    if end_ns <= start_ns:
                        raise EAFImportError(
                            f"Invalid time interval in annotation {source_id!r}: {start_ns} >= {end_ns}"
                        )
                    alignment_kind = AlignmentKind.TIME_ALIGNED

                annotation = EAFAnnotation(
                    source_annotation_id=source_id,
                    tier_id=tier_id,
                    alignment_kind=alignment_kind,
                    start_ns=start_ns,
                    end_ns=end_ns,
                    value=value,
                    parent_source_annotation_id=None,
                    previous_source_annotation_id=None,
                    linguistic_type_ref=tier.linguistic_type_ref,
                    constraint_stereotype=tier.constraint_stereotype,
                )
            elif node.tag == "REF_ANNOTATION":
                parent_id = node.attrib.get("ANNOTATION_REF")
                if not parent_id:
                    raise EAFImportError(f"REF_ANNOTATION {source_id!r} has no parent reference.")

                # Non-aligned semantics: never synthesize time intervals for REF_ANNOTATION
                annotation = EAFAnnotation(
                    source_annotation_id=source_id,
                    tier_id=tier_id,
                    alignment_kind=AlignmentKind.REFERENCE,
                    start_ns=None,
                    end_ns=None,
                    value=value,
                    parent_source_annotation_id=parent_id,
                    previous_source_annotation_id=node.attrib.get("PREVIOUS_ANNOTATION"),
                    linguistic_type_ref=tier.linguistic_type_ref,
                    constraint_stereotype=tier.constraint_stereotype,
                )
                pending_references.append(annotation)
            else:
                raise EAFImportError(f"Unsupported EAF annotation type: {node.tag!r}")

            output.append(annotation)

    # 5. Verify referenced relations
    for item in pending_references:
        if item.parent_source_annotation_id not in source_ids:
            raise EAFImportError(
                f"Missing parent annotation reference {item.parent_source_annotation_id!r} "
                f"for annotation {item.source_annotation_id!r}"
            )
        if (
            item.previous_source_annotation_id is not None
            and item.previous_source_annotation_id not in source_ids
        ):
            raise EAFImportError(
                f"Missing previous annotation reference {item.previous_source_annotation_id!r} "
                f"for annotation {item.source_annotation_id!r}"
            )

    # 6. Verify tier parent relations
    for tier in tiers.values():
        if tier.parent_ref is not None and tier.parent_ref not in tiers:
            raise EAFImportError(f"Tier {tier.tier_id!r} references missing parent tier {tier.parent_ref!r}")

    return EAFDocument(
        format_version=root.attrib.get("VERSION"),
        tiers=tuple(tiers.values()),
        annotations=tuple(output),
        time_unit="milliseconds",
    )


def to_slt_annotations(
    document_or_records: EAFDocument | Sequence[EAFAnnotation | EAFRecord],
    document_id: str = "",
    recording_id: str = "",
    annotator_id: str | None = None,
    default_status: AnnotationStatus = AnnotationStatus.DRAFT,
    document_version: str = "1.0.0",
) -> list[Annotation]:
    """Convert EAFDocument or parsed records into validated Annotation domain models.

    Generates reproducible UUID5 internal annotation IDs derived from:
        uuid.uuid5(uuid.NAMESPACE_DNS, f"{recording_id}:{source_id}:{document_version}")
    while retaining the original ELAN annotation ID in source_annotation_id (Section 24.2).
    """
    records: Sequence[EAFAnnotation]
    if isinstance(document_or_records, EAFDocument):
        records = document_or_records.annotations
    else:
        records = document_or_records

    # Map of source_annotation_id to internal deterministic UUID5 annotation_id
    id_map: dict[str, str] = {}
    for rec in records:
        source_id = rec.source_annotation_id
        internal_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{recording_id}:{source_id}:{document_version}",
            )
        )
        id_map[source_id] = internal_id

    annotations: list[Annotation] = []
    for rec in records:
        internal_id = id_map[rec.source_annotation_id]
        parent_internal_id = (
            id_map.get(rec.parent_source_annotation_id)
            if rec.parent_source_annotation_id
            else None
        )
        previous_internal_id = (
            id_map.get(rec.previous_source_annotation_id)
            if rec.previous_source_annotation_id
            else None
        )

        ann = Annotation(
            annotation_id=internal_id,
            document_id=document_id,
            recording_id=recording_id,
            tier_id=rec.tier_id,
            alignment_kind=rec.alignment_kind,
            start_ns=rec.start_ns,
            end_ns=rec.end_ns,
            value=rec.value,
            annotator_id=annotator_id,
            revision=1,
            status=default_status,
            boundary_quality=(
                BoundaryQuality.PRECISE
                if rec.alignment_kind == AlignmentKind.TIME_ALIGNED
                else BoundaryQuality.APPROXIMATE
            ),
            parent_annotation_id=parent_internal_id,
            previous_annotation_id=previous_internal_id,
            source_annotation_id=rec.source_annotation_id,
        )
        annotations.append(ann)

    return annotations
