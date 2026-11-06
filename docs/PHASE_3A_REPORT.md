# PHASE 3A — CORPUS BACKEND REPORT
**SLT Bilingual Core — Corpus Engineering & Governance Infrastructure**  
**Execution Date:** 2026-11-06  
**Status:** COMPLETED & AUDITED (100% Tests Passing, Strict Mypy Clean, 88% Coverage)  
**Package:** `src/slt_corpus/`  

---

## 1. Corpus Scope

The SLT Corpus Backend establishes the data management, legal authorization, and research infrastructure for **Lengua de Señas Colombiana (LSC)**:
- Primary Sign Language: LSC (`lsc`).
- Target Output Locales: `es-CO` and `en-US`.
- Modality: Continuous discourse and controlled isolated signs.
- Principle: Sign recognition is an empirical linguistic technology stack, requiring structured, consent-gated, and reproducible corpus engineering before training machine learning models.

---

## 2. Domain Contracts

Defined in `src/slt_corpus/domain.py` with immutable dataclasses (`slots=True`, `frozen=True`):
- `Participant`: Pseudonymous `signer_id`, linguistic variant, experience band, schema version. Zero direct PII in metadata.
- `ConsentRecord`: `consent_id`, `signer_id`, `form_version`, `signed_at_utc` (ISO-8601 UTC), `granted_purposes: frozenset[ConsentPurpose]`, `evidence_sha256`, `status`, optional revocation/expiration timestamps.
- `Session`: Associates participant, protocol version, operator, and UTC timestamp.
- `Recording`: Media attributes (width, height, FPS ratio, duration ns, codec, container, SHA-256, storage key).
- `Asset`: Extracted derived features linked to parent recording.
- `Annotation`: Linguistic tier segment with `alignment_kind` (`TIME_ALIGNED`, `REFERENCE`, `UNRESOLVED`), nanosecond boundaries, annotator, revision, status, and parent/previous references.
- `AnnotationDocument`: EAF source container with versioning.
- `DatasetRelease` & `SplitAssignment`: Release manifest entity and partition assignments.

---

## 3. Consent Model

Implemented in `src/slt_corpus/consent.py`:
- Granular purposes: `RECORD_AND_STORE`, `DERIVE_VISUAL_FEATURES`, `DERIVE_LANDMARKS`, `INTERNAL_RESEARCH`, `NONCOMMERCIAL_TRAINING`, `COMMERCIAL_TRAINING`, `SHARE_WITH_PARTNERS`, `PUBLISH_RAW_MEDIA`, `PUBLISH_DERIVED_DATA`.
- `require_consent()`: Validates that active, unrevoked consent exists for the exact requested purpose and matching signer ID.
- Multi-participant rule: Every visible person in a session requires an independent, valid consent authorization.
- Gating: Research consent never permits commercial training.

---

## 4. Storage Architecture

Implemented in `src/slt_corpus/storage.py` and `src/slt_corpus/hashing.py`:
- Content-addressed layout:
  ```
  data/private/
  ├── catalog.sqlite3
  └── objects/
      └── sha256/
          ├── ab/
          │   └── abcdef0123456789... (immutable raw media)
          └── ...
  ```
- Ingestion is atomic: files are streamed to temporary staging, verified via SHA-256, and atomically moved into content-addressed paths.
- Deduplication: Existing objects with identical SHA-256 are detected and reused without duplicating storage.
- Private isolation: `data/private` is untracked and excluded from version control via `.gitignore`.

---

## 5. Media Validation

Implemented in `src/slt_corpus/media_probe.py`:
- PyAV inspection: `probe_video()` extracts exact container format, width, height, time base, frame rate fraction, and duration without trusting file extensions.
- Decoding verification: `full_decode_audit()` decodes stream frames to detect corruption, packet truncation, missing PTS values, and timestamp discontinuities.

---

## 6. SQLite Schema

Defined in `schemas/sqlite/001_initial.sql`:
- Tables:
  1. `participants` (pseudonymous `signer_id` PK)
  2. `consents` (FK to `participants`, revoked status)
  3. `consent_purposes` (FK to `consents`, composite PK)
  4. `sessions` (FK to `participants`)
  5. `session_participants` (composite PK, role)
  6. `recordings` (FK to `sessions`, self-referential `parent_recording_id`)
  7. `recording_participants` (composite PK, role)
  8. `recording_consents` (FK to `recordings`, FK to `consents`)
  9. `assets` (FK to `recordings`, self-referential `parent_asset_id`)
  10. `annotation_documents` (FK to `recordings`)
  11. `annotations` (FK to `annotation_documents`, self-referential `parent_annotation_id`)
  12. `annotation_revisions` (FK to `annotations`, audit trail)
  13. `reviews` (FK to `annotations`, decisions)
  14. `dataset_releases` (release manifest record, unique dataset+version)
  15. `release_recordings` (FK to `dataset_releases`, FK to `recordings`)
  16. `audit_events` (append-only event trail)

---

## 7. Database Migrations

Managed in `src/slt_corpus/database.py`:
- `CorpusDatabase` initializes connections with:
  - `PRAGMA journal_mode = WAL;`
  - `PRAGMA foreign_keys = ON;`
  - `PRAGMA busy_timeout = 10000;`
  - `PRAGMA synchronous = FULL;`
- Atomic migrations: wrapped in explicit `BEGIN IMMEDIATE;` and `COMMIT;` blocks with `PRAGMA user_version = 1;`.
- Online live backup via `Connection.backup()` and health checks via `integrity_check()` and `foreign_key_check()`.

---

## 8. ELAN Import

Implemented in `src/slt_corpus/elan.py`:
- Secure parser: Uses `defusedxml.ElementTree` with size limits (100MB) to prevent XML entity expansion attacks.
- Non-aligned preservation: `REF_ANNOTATION` does not inherit parent intervals (`start_ns=None, end_ns=None`), strictly maintaining the `AlignmentKind.REFERENCE` contract.
- Deterministic IDs (Section 24.2): Internal `annotation_id` is derived via `uuid.uuid5(uuid.NAMESPACE_DNS, f"{recording_id}:{source_annotation_id}:{version}")`, retaining original ELAN IDs in `source_annotation_id`.

---

## 9. Annotation Semantics

Annotations support three alignment kinds:
1. `TIME_ALIGNED`: Continuous or isolated signs anchored by millisecond/nanosecond boundaries.
2. `REFERENCE`: Subordinate tier annotations (e.g. Spanish glosses, grammar notes) tied to parent annotations without synthetic time intervals.
3. `UNRESOLVED`: Incomplete or draft boundaries preserving known start or end points without raising errors (Section 24.1).

---

## 10. Split Validation

Implemented in `src/slt_corpus/splits.py`:
- `validate_group_disjoint()`: Prevents data leakage across partitions (`train`, `validation`, `test`) across multiple grouping dimensions (`signer_id`, `prompt_id`, `session_id`).
- `validate_augmentation_lineage()`: Ensures augmented samples reside strictly in the same split as their parent recording.
- `measure_sentence_overlap()`: Reports pairwise prompt intersections between partitions.

---

## 11. Data Lineage

Every derived asset and dataset release records complete provenance:
- Parent recording ID and source video SHA-256.
- Extractor name, version, and model weights SHA-256.
- Canonical JSON configuration SHA-256 (`src/slt_core/provenance/configuration.py`).
- Timestamp policy and output contract version.

---

## 12. Dataset Release Validation

Implemented in `src/slt_corpus/release.py`:
- `RecordingEligibility`: Evaluates recording integrity, participant consent scopes, technical quality status, and linguistic review.
- Multi-criteria gating: Rejects releases containing draft annotations (when strict review is required), expired/revoked consents, or cross-split leakage.
- Releases generate immutable `dataset_release.json` and `splits.json` manifests.

---

## 13. Audit Events

The `audit_events` table maintains an append-only log of critical operations:
- Event ID, actor ID, action name, resource type, resource ID, UTC timestamp, and JSON details.
- Used for GDPR / Ley 1581 compliance, revocation tracking, and provenance verification.

---

## 14. Security Controls

- **Private Storage:** All raw media stored in local content-addressed directory, excluded from git (`.gitignore`).
- **No Direct PII:** Names, identification numbers, addresses, and emails strictly rejected from participant metadata.
- **Quarantine:** External datasets LSC50, LSC70, and LSC-54 are inventoried in `corpus/lsc/documentation/external_datasets.json` and quarantined from commercial release.

---

## 15. Test Results

The full test suite passed with 100% success:
- **Total Tests:** 186 passed in 10.62 seconds.
- **Corpus Suite (`tests/corpus/`):** 41 tests passed.
  - `test_database.py`: 4 tests (WAL mode, migrations, atomic rollback, backup, foreign keys).
  - `test_media_probe.py`: 5 tests (container probe, stream rates, decode audit, error detection).
  - `test_elan.py`: 3 tests (defusedxml, non-aligned REF_ANNOTATION, deterministic UUID5).
  - `test_consent.py`: 5 tests.
  - `test_corpus_domain.py`: 5 tests.
  - `test_storage.py`: 3 tests.
  - `test_splits.py`: 6 tests.
  - `test_release.py`: 2 tests.
  - `test_validation_and_hashing.py`: 4 tests.
  - `test_audit_and_cli.py`: 2 tests.
  - `test_tools.py`: 2 tests.
- **Code Coverage:** 88% overall across `slt_corpus`, `slt_core`, `slt_capture`.
- **Static Analysis:**
  - `ruff check src tests tools`: 0 errors (clean).
  - `mypy src/slt_core src/slt_corpus src/slt_capture src/slt_studio tools`: 0 errors across 63 source files (strict mode).

---

## 16. Known Limitations

1. **Local Concurrency:** SQLite in WAL mode supports single-writer/multi-reader on local filesystems; distributed network filesystems (NFS/SMB) are not supported.
2. **External Dataset Rights:** LSC50, LSC70, and LSC-54 remain under quarantine until data-level licenses are legally verified.

---

## 17. Approval Status

- **Status:** APPROVED
- **Reviewer:** Antigravity Engineering Core
- **Sign-off:** Phase 3A Corpus Backend is fully verified and ready to support Phase 3B Dataset Studio.
