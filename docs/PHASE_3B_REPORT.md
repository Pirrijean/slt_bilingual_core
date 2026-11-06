# Phase 3B Dataset Studio & Capture Report
**SLT Bilingual Core — Acquisition & Dataset Studio Interface**  
**Execution Date:** 2026-11-06  
**Status:** IMPLEMENTED & VERIFIED  
**Packages:** `src/slt_capture/`, `src/slt_studio/`  

---

## 1. Executive Summary

Phase 3B completes the graphical management environment (**Dataset Studio**) and the controlled acquisition engine (**Capture Studio**) for Colombian Sign Language (LSC) research. Built on PySide6 and strictly decoupled from the low-level database operations, Dataset Studio serves as the centralized mission control for the corpus lifecycle.

The system guarantees that:
1. No video recording can take place without explicit, unrevoked consent for `RECORD_AND_STORE`.
2. All master takes are hashed (SHA-256) and immediately ingested into content-addressed storage.
3. ELAN (`.eaf`) annotations are imported with exact nanosecond bounds and hierarchical integrity.
4. Dataset partitions are verified against signer leakage before release manifests are built.
5. All operations run offline-first with zero external cloud upload.

---

## 2. Architecture & Modules

### 2.1 Capture Engine (`src/slt_capture/`)
- `protocol.py`: Loads and validates structured capture protocols (`controlled_v1.json`, `continuous_v1.json`) containing task definitions, prompt references, target handshapes, and repetitions.
- `metadata.py`: Encapsulates camera specifications, resolution, lighting lux, and distance parameters; rejects direct personal identifiers in extra metadata.
- `session.py`: `CaptureSessionController` gates session execution, re-verifying consent freshness from the SQLite catalog at start time.
- `recorder.py`: `CaptureRecorder` writes frames, measures effective duration and FPS, performs atomic ingestion via `slt_corpus.storage.ingest_video`, and creates catalog entries.

### 2.2 Dataset Studio GUI (`src/slt_studio/`)
Minimalist professional dark-themed desktop interface organized into 10 dedicated screens:
1. **Corpus Dashboard:** Real-time KPI cards (participants, take count with original vs. augmented breakdown, total duration in seconds, active/revoked consents) and Quarantined External Datasets inventory.
2. **Participants:** Pseudonymous participant registration and list. Programmatically blocks direct PII.
3. **Consent Status:** Displays purpose-specific scopes (`RECORD_AND_STORE`, `DERIVE_LANDMARKS`, `INTERNAL_RESEARCH`, `COMMERCIAL_TRAINING`) and provides one-click revocation.
4. **Capture:** Controlled recording interface with protocol selection, signer verification, live status banners, and take ingestion.
5. **Recording Browser:** Searchable take catalog with duration, resolution, codec, and SHA-256 prefix display.
6. **Technical Review:** One-click physical file, non-emptiness, and checksum integrity verification with multi-dimensional status display (`technical_status`, `linguistic_status`).
7. **Annotation Manager:** ELAN `.eaf` import dialog, nanosecond conversion, tier inspection, and annotation table.
8. **Dataset Builder:** Task configuration (`continuous_sign_recognition`, `isolated_sign_recognition`, etc.) and automated Signer-Independent split generation.
9. **Split Validator:** Automated verification of partitions via `validate_group_disjoint` and `validate_no_augmentation_leakage`, displaying real-time leak analysis.
10. **Release Manager:** Builds immutable `dataset_release.json` manifests, gating releases against missing commercial consent or quarantined resources.

---

## 3. Command-Line & Helper Tooling (`tools/`)
In addition to the unified CLI `slt-corpus` (with `init`, `participant add`, `consent add`, `ingest`, `audit`, `elan-import`, `validate-splits`, `release build`, and `release validate`), convenience scripts are provided:
- `tools/corpus_init.py`
- `tools/corpus_ingest.py`
- `tools/corpus_audit.py`
- `tools/elan_import.py`
- `tools/split_validate.py`
- `tools/dataset_release.py`

---

## 4. Test Evidence & Acceptance Criteria

- **Test Suite Status:** 100% passing across core perception, corpus engineering, capture, and studio interfaces.
- **Headless GUI Testing:** Verified under `QT_QPA_PLATFORM=offscreen`. All 10 screens instantiate, switch without errors, and query the catalog properly.
- **Ruff & Mypy:** Clean, zero errors in strict mode across `src/slt_core`, `src/slt_corpus`, `src/slt_capture`, and `src/slt_studio`.
