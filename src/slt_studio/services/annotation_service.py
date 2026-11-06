"""Annotation service managing ELAN synchronization and linguistic revisions."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
    AlignmentKind,
    Annotation,
    AnnotationDocument,
    AnnotationStatus,
    BoundaryQuality,
)
from slt_corpus.elan import import_eaf, to_slt_annotations


class AnnotationService:
    """Manages ELAN file importing, tier structuring, and linguistic revisions."""

    def __init__(self, catalog: CorpusCatalog) -> None:
        self.catalog = catalog

    def import_elan_file(
        self,
        eaf_path: str | Path,
        document_id: str,
        recording_id: str,
        annotator_id: str | None = None,
        document_version: str = "1.0.0",
    ) -> list[Annotation]:
        """Parse ELAN XML file and persist document and annotations with deterministic UUIDs."""
        path = Path(eaf_path).resolve()
        records = import_eaf(path)

        now_utc = datetime.now(UTC).isoformat()
        doc = AnnotationDocument(
            document_id=document_id,
            recording_id=recording_id,
            schema_version="1.0.0",
            eaf_source_path=path.name,
            created_at_utc=now_utc,
            status=AnnotationStatus.DRAFT,
        )

        annotations = to_slt_annotations(
            document_or_records=records,
            document_id=document_id,
            recording_id=recording_id,
            annotator_id=annotator_id,
            document_version=document_version,
        )

        self.catalog.add_annotation_document(doc)
        self.catalog.add_annotations(annotations)
        return annotations

    def get_annotations_for_recording(self, recording_id: str) -> list[Annotation]:
        """Retrieve all annotations linked to a recording."""
        results: list[Annotation] = []
        with self.catalog._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT a.annotation_id, a.document_id, d.recording_id, a.tier_id,
                       a.start_ns, a.end_ns, a.value, a.parent_annotation_id,
                       a.boundary_quality, a.status, a.annotator_id, a.revision
                FROM annotations a
                JOIN annotation_documents d ON a.document_id = d.document_id
                WHERE d.recording_id = ?
                ORDER BY a.tier_id, a.start_ns;
                """,
                (recording_id,),
            )
            for row in cursor.fetchall():
                start_ns = row[4]
                end_ns = row[5]
                alignment_kind = (
                    AlignmentKind.TIME_ALIGNED
                    if (start_ns is not None and end_ns is not None)
                    else AlignmentKind.REFERENCE
                )
                results.append(
                    Annotation(
                        annotation_id=row[0],
                        document_id=row[1],
                        recording_id=row[2],
                        tier_id=row[3],
                        alignment_kind=alignment_kind,
                        start_ns=start_ns,
                        end_ns=end_ns,
                        value=row[6],
                        parent_annotation_id=row[7],
                        boundary_quality=BoundaryQuality(row[8]),
                        status=AnnotationStatus(row[9]),
                        annotator_id=row[10],
                        revision=row[11],
                    )
                )
        return results
