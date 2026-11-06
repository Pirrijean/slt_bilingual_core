"""Linguistic adjudication service resolving disagreements between annotators."""

from __future__ import annotations

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
    AlignmentKind,
    Annotation,
    AnnotationStatus,
    BoundaryQuality,
)


class AdjudicationService:
    """Handles review disputes, inter-annotator disagreement resolution, and approval."""

    def __init__(self, catalog: CorpusCatalog) -> None:
        self.catalog = catalog

    def get_pending_adjudications(self) -> list[Annotation]:
        """Retrieve annotations flagged for second review, submitted, or adjudication."""
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
                WHERE a.status IN ('submitted', 'reviewed', 'adjudicated')
                ORDER BY d.recording_id, a.tier_id, a.start_ns;
                """
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

    def adjudicate_annotation(
        self,
        annotation_id: str,
        adjudicated_value: str,
        new_status: AnnotationStatus = AnnotationStatus.ADJUDICATED,
        adjudicator_id: str = "adjudicator_01",
    ) -> None:
        """Resolve an annotation dispute by storing the adjudicated value and updating status."""
        with self.catalog._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE annotations
                SET value = ?, status = ?, annotator_id = ?, revision = revision + 1
                WHERE annotation_id = ?;
                """,
                (adjudicated_value, new_status.value, adjudicator_id, annotation_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Annotation {annotation_id!r} not found for adjudication.")

    def approve_recording_annotations(self, recording_id: str) -> None:
        """Mark all annotations for a recording as adjudicated and advance recording status."""
        with self.catalog._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE annotations
                SET status = 'adjudicated'
                WHERE document_id IN (
                    SELECT document_id FROM annotation_documents WHERE recording_id = ?
                ) AND status != 'rejected';
                """,
                (recording_id,),
            )
            cursor.execute(
                """
                UPDATE recordings
                SET status = 'approved'
                WHERE recording_id = ?;
                """,
                (recording_id,),
            )
