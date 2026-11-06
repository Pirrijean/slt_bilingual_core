# Phase 3A Corpus Backend Report
**SLT Bilingual Core — Corpus Engineering & Governance Infrastructure**  
**Execution Date:** 2026-11-06  
**Status:** COMPLETED & VERIFIED  
**Package:** `src/slt_corpus/`  

---

## 1. Executive Summary

Phase 3A establishes the formal linguistic data engineering, governance, storage, and catalog infrastructure for the **Colombian Sign Language (LSC)** profile. As mandated by project scope decisions, sign recognition is not approached as ad-hoc gesture classification, but as an empirical linguistic technology stack grounded in verified natural signing data, informed consent, and reproducible partitioning.

The Phase 3A backend is strictly decoupled from OpenCV, MediaPipe, and Qt. It provides a pure-Python library (`slt_corpus`), an auditable CLI (`slt-corpus`), an ACID SQLite catalog with foreign key enforcement, content-addressed video storage under `data/private/objects/sha256/`, an ELAN (`.eaf`) XML converter preserving nanosecond time precision ($t_{\text{ns}} = t_{\text{ms}} \times 10^6$), split validation enforcing signer-independence and augmentation lineage, and immutable dataset release manifests.

---

## 2. Implemented Modules & Contracts

| Module | Core Contracts & Capabilities | Key Invariants Enforced |
|---|---|---|
| `domain.py` | `Participant`, `ConsentRecord`, `Session`, `Recording`, `Asset`, `Annotation`, `AnnotationDocument`, `AnnotationReview`, `LexicalEntry`, `DatasetRelease`, `SplitAssignment`. | Strict ISO-8601 UTC with timezone; path traversal rejection (`..`, `\`, `\0`, absolute); positive dimension & duration checks; strict prohibition of direct PII in metadata. |
| `consent.py` | `require_consent()`, `validate_video_storage_scope()`, `validate_landmark_derivation_scope()`, `validate_release_consent()`. | Purpose-specific gating (`record_and_store`, `internal_research`, `commercial_training`, etc.); unrevoked consent check at every sensitive call; signer ID matching. |
| `hashing.py` | `sha256_file()`, `sha256_bytes()`, `sha256_string()`. | Chunked streaming computation (default 1 MiB); positive chunk validation. |
| `storage.py` | `ingest_video()`, `StoredAsset`. | Content-addressed placement: `objects/sha256/ab/abcdef...mp4`; atomic writes via temporary files; isolated `.tmp` cleanup (no shared directory wiping); deduplication detection. |
| `catalog.py` | `CorpusCatalog` with 10 relational tables. | `PRAGMA foreign_keys = ON;` cascade deletions on dependent entities; indexed queries; atomic online backup via `sqlite3.Connection.backup()`. |
| `elan.py` | `import_eaf()`, `to_slt_annotations()`, `EAFRecord`. | Parses EAF v2.8/3.0 `<TIME_ORDER>` and `<TIME_SLOT>` in ms; converts to ns without FPS rounding; inherits timing for `REF_ANNOTATION` hierarchy; preserves Unicode glosses. |
| `splits.py` | `validate_group_disjoint()`, `validate_no_augmentation_leakage()`, `measure_sentence_overlap()`. | Enforces Signer-Independent partitions; detects cross-split signer leakage; requires augmented copies to remain in parent split; quantifies prompt overlap. |
| `release.py` | `DatasetReleaseManager`. | Commercial vs non-commercial consent verification; quarantine gating; immutable manifest generation (`dataset_release.json` + `splits.json`). |
| `validation.py` | `validate_recording_integrity()`, `validate_annotation_tiers()`, `validate_annotation_temporal_bounds()`. | File existence, non-emptiness, checksum verification; tier membership checking; boundary overflow detection. |
| `audit.py` | `CorpusAuditor`. | Aggregates participant count, total duration, original vs augmented breakdown, consent status, and quarantined datasets. |
| `cli.py` | CLI executable `slt-corpus` (`init`, `participant add`, `consent add`, `ingest`, `audit`, `elan-import`, `validate-splits`). | Deterministic exit codes (0/1); strict privacy in stdout/stderr (no raw names logged). |

---

## 3. Storage & Catalog Architecture

### 3.1 Content-Addressed Video Layout
All raw media are ingested through `slt_corpus.storage.ingest_video`:
```
data/private/
├── catalog.sqlite3
└── objects/
    └── sha256/
        ├── 81/
        │   └── 813ca5285c28ccee5cab8b10ebda9c908fd6d78ed9dc94cc65ea6cb67a7f13ae.mp4
        └── ...
```
- Raw filenames never serve as public identifiers.
- Codecs and audio tracks (if present) are preserved untouched.
- Git repository ignores `data/private/*` via `.gitignore`.

### 3.2 Relational Catalog Schema (SQLite)
`CorpusCatalog` enforces referential integrity across 10 tables:
1. `participants` (pseudonymous `signer_id` PK)
2. `consents` (FK to `participants`, revoked status)
3. `sessions` (FK to `participants`)
4. `recordings` (FK to `sessions`, FK to `participants`, self-referential `parent_recording_id`)
5. `assets` (FK to `recordings`)
6. `annotation_documents` (FK to `recordings`)
7. `annotations` (FK to `annotation_documents`, self-referential `parent_annotation_id`)
8. `annotation_reviews` (FK to `annotations`)
9. `dataset_releases` (release manifest record)
10. `split_assignments` (FK to `dataset_releases`, FK to `recordings`, FK to `participants`)

---

## 4. External Dataset Quarantine Inventory (TASK 3A.9)

Per project decisions, external published datasets have been inventoried in `corpus/lsc/documentation/external_datasets.json` and placed under quarantine pending legal and commercial verification:

| Dataset | Stated Scope | Documented Content | License Stated | Quarantine Decision |
|---|---|---|---|---|
| **LSC50** (Nature 2024) | 50 signs, 5 signers, 4,000 videos | RGB, Depth, IR, Landmarks, IMU | Article: CC BY-NC-ND 4.0; Code: MIT | **Quarantine**: MIT code license does not grant rights over biometric video/sensor assets. Commercial use prohibited. |
| **LSC70** (PMC 2025) | 47 signs, 70 signers, 35,208 frames | Sign images & dynamic sequences | Article: CC-BY; Data: Mendeley repository terms | **Quarantine**: Repository terms and biometric consent forms require explicit verification before commercial or derived distribution. |
| **LSC-54** (SciDB 2025) | 54 classes, 22 signers, 2,850 videos | Multimodal landmarks, time series | Article: CC-BY-NC 4.0 | **Quarantine**: 45x augmentation with forward hand imputation. Must remain strictly quarantined as experimental baseline only. |

---

## 5. Test Suite & Quality Verification

- **Total Test Suite:** 153 tests passing (100%).
- **Phase 3A Tests (`tests/corpus/`):** 32 tests passing.
  - `test_corpus_domain.py`: 5 tests
  - `test_consent.py`: 5 tests
  - `test_storage.py`: 3 tests
  - `test_catalog.py`: 3 tests
  - `test_elan.py`: 3 tests
  - `test_splits.py`: 6 tests
  - `test_release.py`: 2 tests
  - `test_validation_and_hashing.py`: 3 tests
  - `test_audit_and_cli.py`: 2 tests
- **Coverage:**
  - `slt_corpus`: 85% overall (hashing 100%, validation 100%, splits 96%, audit 95%, consent 95%, release 93%).
  - `slt_core`: 95%.
- **Static Analysis:**
  - `ruff check src/slt_core src/slt_corpus tests/corpus`: 0 errors.
  - `mypy src/slt_core src/slt_corpus`: 0 errors in 31 source files (strict mode).

---

## 6. Next Steps & Stop Criteria

Phase 3A is fully implemented, tested, and documented.
Per the explicit execution order stopping condition:
> *"Stop after the report and verify all tests pass before proceeding to Phase 3B GUI (PySide6 Dataset Studio)."*

Execution is halted pending review of Phase 3A deliverables.
