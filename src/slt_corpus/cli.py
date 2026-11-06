"""Command-line interface for SLT Corpus management."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from slt_corpus.audit import CorpusAuditor
from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
    AnnotationDocument,
    ConsentPurpose,
    ConsentRecord,
    Participant,
    Recording,
    RecordingStatus,
)
from slt_corpus.elan import import_eaf, to_slt_annotations
from slt_corpus.release import DatasetReleaseManager
from slt_corpus.splits import validate_group_disjoint
from slt_corpus.storage import ingest_video


def build_parser() -> argparse.ArgumentParser:
    """Build the slt-corpus CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="slt-corpus",
        description="SLT Bilingual Core — Corpus Management CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. init
    init_parser = subparsers.add_parser("init", help="Initialize corpus directory and database")
    init_parser.add_argument("--root", default="corpus/lsc", help="Corpus root directory")
    init_parser.add_argument("--db", default="data/private/catalog.sqlite3", help="Catalog database path")

    # 2. participant add
    part_parser = subparsers.add_parser("participant", help="Participant operations")
    part_sub = part_parser.add_subparsers(dest="subcommand", required=True)
    part_add = part_sub.add_parser("add", help="Register a pseudonymous participant")
    part_add.add_argument("--signer-id", required=True, help="Pseudonymous ID (slug)")
    part_add.add_argument("--metadata", default="{}", help="Metadata JSON (no PII)")
    part_add.add_argument("--db", default="data/private/catalog.sqlite3")

    # 3. consent add
    consent_parser = subparsers.add_parser("consent", help="Consent operations")
    consent_sub = consent_parser.add_subparsers(dest="subcommand", required=True)
    consent_add = consent_sub.add_parser("add", help="Register a consent record")
    consent_add.add_argument("--consent-id", required=True)
    consent_add.add_argument("--signer-id", required=True)
    consent_add.add_argument("--form-version", required=True)
    consent_add.add_argument(
        "--purposes",
        required=True,
        nargs="+",
        help="Granted purposes (e.g. record_and_store noncommercial_training)",
    )
    consent_add.add_argument("--evidence-sha256", required=True)
    consent_add.add_argument("--db", default="data/private/catalog.sqlite3")

    # 4. ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a media recording")
    ingest_parser.add_argument("--file", required=True, help="Source video file")
    ingest_parser.add_argument("--storage-root", default="data/private", help="Storage root")
    ingest_parser.add_argument("--signer-id", required=True)
    ingest_parser.add_argument("--consent-id", required=True)
    ingest_parser.add_argument("--session-id", required=True)
    ingest_parser.add_argument("--recording-id", required=True)
    ingest_parser.add_argument("--duration-ns", type=int, default=1_000_000_000)
    ingest_parser.add_argument("--width", type=int, default=1920)
    ingest_parser.add_argument("--height", type=int, default=1080)
    ingest_parser.add_argument("--container", default="mp4")
    ingest_parser.add_argument("--codec", default="h264")
    ingest_parser.add_argument("--db", default="data/private/catalog.sqlite3")

    # 5. audit
    audit_parser = subparsers.add_parser("audit", help="Generate corpus audit statistics")
    audit_parser.add_argument("--db", default="data/private/catalog.sqlite3")
    audit_parser.add_argument(
        "--external-registry",
        default="corpus/lsc/documentation/external_datasets.json",
    )

    # 6. elan-import
    elan_parser = subparsers.add_parser("elan-import", help="Import ELAN .eaf annotation")
    elan_parser.add_argument("--eaf", required=True, help="Path to .eaf XML")
    elan_parser.add_argument("--recording-id", required=True)
    elan_parser.add_argument("--document-id", required=True)
    elan_parser.add_argument("--schema-version", default="1.0.0")
    elan_parser.add_argument("--db", default="data/private/catalog.sqlite3")

    # 7. validate-splits
    split_parser = subparsers.add_parser("validate-splits", help="Validate split disjointness")
    split_parser.add_argument("--splits-json", required=True, help="Path to splits JSON")
    split_parser.add_argument(
        "--mapping-json",
        required=True,
        help="JSON mapping recording_id to signer_id",
    )

    # 8. release
    rel_parser = subparsers.add_parser("release", help="Dataset release management")
    rel_sub = rel_parser.add_subparsers(dest="subcommand", required=True)

    rel_build = rel_sub.add_parser("build", help="Build an immutable dataset release")
    rel_build.add_argument("--dataset-id", required=True)
    rel_build.add_argument("--version", required=True)
    rel_build.add_argument("--profile-id", default="lsc")
    rel_build.add_argument("--task", default="continuous_sign_recognition")
    rel_build.add_argument("--corpus-version", default="0.1.0")
    rel_build.add_argument("--schema-version", default="1.0.0")
    rel_build.add_argument("--scope", default="internal_research")
    rel_build.add_argument("--splits-json", required=True)
    rel_build.add_argument("--output-dir", required=True)
    rel_build.add_argument("--storage-root", default="data/private")
    rel_build.add_argument("--db", default="data/private/catalog.sqlite3")

    rel_val = rel_sub.add_parser("validate", help="Validate an existing release manifest")
    rel_val.add_argument("--manifest", required=True)
    rel_val.add_argument("--db", default="data/private/catalog.sqlite3")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint function."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            Path(args.root).mkdir(parents=True, exist_ok=True)
            catalog = CorpusCatalog(args.db)
            print(f"Initialized corpus catalog at {catalog.db_path}")
            return 0

        elif args.command == "participant":
            if args.subcommand == "add":
                catalog = CorpusCatalog(args.db)
                now_utc = datetime.now(UTC).isoformat()
                p = Participant(
                    signer_id=args.signer_id,
                    metadata_json=args.metadata,
                    created_at_utc=now_utc,
                )
                catalog.add_participant(p)
                print(f"Registered participant: {p.signer_id}")
                return 0

        elif args.command == "consent":
            if args.subcommand == "add":
                catalog = CorpusCatalog(args.db)
                purposes = frozenset(ConsentPurpose(p) for p in args.purposes)
                now_utc = datetime.now(UTC).isoformat()
                c = ConsentRecord(
                    consent_id=args.consent_id,
                    signer_id=args.signer_id,
                    form_version=args.form_version,
                    signed_at_utc=now_utc,
                    granted_purposes=purposes,
                    evidence_sha256=args.evidence_sha256,
                )
                catalog.add_consent(c)
                print(f"Registered consent: {c.consent_id}")
                return 0

        elif args.command == "ingest":
            catalog = CorpusCatalog(args.db)
            consent = catalog.get_consent(args.consent_id)
            if consent is None:
                print(f"Error: Consent {args.consent_id} not found.", file=sys.stderr)
                return 1

            stored = ingest_video(
                source_path=args.file,
                storage_root=args.storage_root,
                consent=consent,
                signer_id=args.signer_id,
            )
            recording = Recording(
                recording_id=args.recording_id,
                session_id=args.session_id,
                signer_id=args.signer_id,
                source_video_sha256=stored.sha256,
                storage_relative_path=stored.relative_path,
                duration_ns=args.duration_ns,
                fps_num=None,
                fps_den=None,
                width=args.width,
                height=args.height,
                container_format=args.container,
                video_codec=args.codec,
                status=RecordingStatus.INGESTED,
            )
            catalog.add_recording(recording)
            print(f"Ingested recording {recording.recording_id} -> {stored.relative_path} (duplicate: {stored.is_duplicate})")
            return 0

        elif args.command == "audit":
            catalog = CorpusCatalog(args.db)
            auditor = CorpusAuditor(catalog)
            report = auditor.generate_audit_report(args.external_registry)
            print(json.dumps(report, indent=2))
            return 0

        elif args.command == "elan-import":
            catalog = CorpusCatalog(args.db)
            records = import_eaf(args.eaf)
            now_utc = datetime.now(UTC).isoformat()
            doc = AnnotationDocument(
                document_id=args.document_id,
                recording_id=args.recording_id,
                schema_version=args.schema_version,
                eaf_source_path=None,
                created_at_utc=now_utc,
            )
            annotations = to_slt_annotations(records, document_id=args.document_id)
            catalog.add_annotation_document(doc)
            catalog.add_annotations(annotations)
            print(f"Imported {len(annotations)} annotations into document {doc.document_id}")
            return 0

        elif args.command == "validate-splits":
            splits_data = json.loads(Path(args.splits_json).read_text(encoding="utf-8"))
            mapping_data = json.loads(Path(args.mapping_json).read_text(encoding="utf-8"))
            validate_group_disjoint(splits_data.get("splits", splits_data), mapping_data)
            print("Split validation SUCCESS: Signer-independent partitioning verified.")
            return 0

        elif args.command == "release":
            catalog = CorpusCatalog(args.db)
            if args.subcommand == "build":
                splits_data = json.loads(Path(args.splits_json).read_text(encoding="utf-8"))
                split_members = splits_data.get("splits", splits_data)
                manager = DatasetReleaseManager(catalog, args.storage_root)
                release = manager.build_release(
                    dataset_id=args.dataset_id,
                    dataset_version=args.version,
                    profile_id=args.profile_id,
                    task=args.task,
                    corpus_version=args.corpus_version,
                    annotation_schema_version=args.schema_version,
                    usage_scope=ConsentPurpose(args.scope),
                    split_members=split_members,
                    output_dir=args.output_dir,
                )
                print(f"Dataset release built successfully: {release.release_id}")
                return 0
            elif args.subcommand == "validate":
                manifest_path = Path(args.manifest)
                if not manifest_path.is_file():
                    print(f"Manifest not found: {manifest_path}", file=sys.stderr)
                    return 1
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                release_id = data.get("release_id")
                fetched = catalog.get_dataset_release(release_id)
                if fetched is None:
                    print(f"Release {release_id} not registered in catalog.", file=sys.stderr)
                    return 1
                print(f"Release {release_id} is VALID and registered.")
                return 0

    except Exception as exc:  # noqa: BLE001
        print(f"Execution failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
