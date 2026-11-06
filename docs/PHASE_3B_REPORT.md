# PHASE 3B — DATASET STUDIO REPORT
**SLT Bilingual Core — Acquisition & Dataset Studio Technical Audit**  
**Execution Date:** 2026-11-06  
**Status:** IMPLEMENTED & AUDITED  
**Packages:** `src/slt_capture/`, `src/slt_studio/`  

---

## 1. Capture Workflow
The controlled acquisition pipeline in `src/slt_capture/` is structured around formal session gating and multi-take recording lifecycles:
1. **Operator Configuration:** The studio operator launches a session via `CaptureSessionRequest`, specifying `session_id`, `signer_id`, and `protocol_id`.
2. **Consent & Pseudonym Verification:** The `CaptureSessionController` queries `CorpusCatalog` for participant existence and verifies unrevoked `RECORD_AND_STORE` authorization. If consent is absent or revoked, the session enters `SessionState.ERROR` immediately.
3. **Task Selection:** The active task is selected from the approved protocol (`ProtocolTask`), setting target handshape and elicitation prompt references.
4. **Recording State:** `CaptureRecorder.start()` initiates an isolated raw `.mp4` video container and allocates an authoritative timestamp sidecar (`<recording_id>.timestamps.json`).
5. **Frame Processing:** Each incoming BGR frame is written to disk alongside its measured monotonic capture timestamp (`time.monotonic_ns()`).
6. **Teardown & Atomic Ingestion:** Calling `CaptureRecorder.stop()` terminates the OpenCV writer, seals the sidecar JSON, computes SHA-256 hashes for both files, and delegates to `CaptureIngestService` / `ingest_video()` to transfer the asset into immutable content-addressed storage.

---

## 2. Consent Enforcement
Consent gating is implemented strictly per operation without assumptions:
- **Pre-Flight Validation:** `CaptureSessionController` verifies consent before allowing transitions to `SessionState.READY`.
- **Runtime Freshness Check:** When `start()` is invoked, the controller re-queries SQLite to ensure consent was not revoked during staging.
- **Scope Specificity:** The system enforces `validate_video_storage_scope()`, asserting that `ConsentPurpose.RECORD_AND_STORE` is present in `granted_purposes`.
- **Revocation Propagation:** When a participant's consent is revoked via `CorpusCatalog.revoke_consent()`, any further recording attempts raise `ConsentDeniedError`.

---

## 3. Recording Integrity
Media files must satisfy multi-level physical and logical verification:
1. **File Non-Emptiness:** Recordings with zero frames or 0 bytes trigger `RecorderError` and are purged from temporary staging without catalog registration.
2. **Cryptographic Sealing:** All master takes are hashed using SHA-256 before ingestion. The hash determines the content-addressed storage relative path (`objects/sha256/xx/yy/<sha256>.mp4`).
3. **Transactional Catalog Registration:** Recordings are committed to the SQLite catalog within atomic database transactions with foreign keys enabled (`PRAGMA foreign_keys = ON;`).
4. **Physical Media Audit:** `ReviewService.audit_recording()` validates that physical files exist on the approved storage mount, re-verifies hashes, and executes a full frame decode audit via PyAV (`full_decode_audit()`).

---

## 4. Timestamp Preservation
To avoid synthetic $+1$ms corrections and artificial timing assumptions:
- **Dual Recording Architecture:** Every recording take generates both the encoded container and an authoritative sidecar `CaptureArtifact.timestamps_sidecar_path`.
- **Monotonic Capture Timestamps:** Each frame records `frame_index`, `capture_timestamp_ns`, `encoded_pts`, `encoded_time_base_num`, and `encoded_time_base_den`.
- **VFR vs CFR Distinction:** Ingested metadata explicitly distinguishes between fixed video container frame rates and real-world variable arrival intervals, preserving the original sensor timeline in the sidecar.

---

## 5. Capture Protocols
Capture sessions must adhere strictly to structured protocols:
- **Specifications:** `corpus/lsc/capture_protocols/controlled_v1.json` (isolated units, phonological handshape minimal pairs) and `continuous_v1.json` (co-articulated sentences, narrative sequences).
- **Draft Rejection:** `CaptureSessionController` enforces that unreviewed draft protocols cannot be utilized for acquisition without explicit authorized test parameters (`allow_draft_protocol=False` in production).
- **Audio Policy:** Audio capture is disabled by default (`audio_enabled: false`) to minimize unnecessary biometric data collection.

---

## 6. ELAN Workflow
External ELAN (`.eaf` v3.0) integration is achieved through clean export/import bridges rather than an embedded re-implementation:
1. **EAF Ingestion:** `slt_corpus.elan.import_eaf()` parses XML safely using `defusedxml.ElementTree`.
2. **Nanosecond Slot Conversion:** Millisecond time slots from `<TIME_ORDER>` are converted into authoritative nanoseconds ($t_{\text{ns}} = t_{\text{ms}} \times 10^6$).
3. **Reference Annotation Non-Alignment:** Annotations under symbolic tiers (`REF_ANNOTATION`) preserve non-aligned semantics with `start_ns=None, end_ns=None`, retaining parental references without synthesizing artificial time intervals.
4. **Deterministic UUID5 Identifiers:** SLT internal annotation IDs are generated reproducibly via `uuid.uuid5(uuid.NAMESPACE_DNS, f"{recording_id}:{source_annotation_id}:{version}")`, completely eliminating cross-document token collisions while preserving original tokens in `source_annotation_id`.

---

## 7. Annotation Review
Linguistic annotations progress through a verified review lifecycle:
- **Lifecycle States:** `DRAFT` $\rightarrow$ `SUBMITTED` $\rightarrow$ `REVIEWED` $\rightarrow$ `ADJUDICATED` / `REJECTED`.
- **Quality Ratings:** Boundaries are tagged with `BoundaryQuality` (`PRECISE`, `APPROXIMATE`, `ESTIMATED`).
- **Revision History:** Modifications increment the document `revision` integer, maintaining immutability of previous annotator passes.

---

## 8. Adjudication
Disagreements between independent annotators are resolved via the dedicated Adjudication subsystem:
- **Screen:** `AdjudicationScreen` (`src/slt_studio/screens/adjudication.py`) surfaces all annotations in `submitted`, `reviewed`, or `adjudicated` states across tiers.
- **Service Layer:** `AdjudicationService` allows an appointed linguist adjudicator to inspect conflicting glosses, input the consensus value, advance the revision count, and update status to `ADJUDICATED`.
- **Batch Finalization:** The adjudicator can approve all annotations for a take in a single operation, advancing the underlying take's state to `RecordingStatus.APPROVED`.

---

## 9. Dataset Builder
`DatasetBuilderScreen` (`src/slt_studio/screens/builder.py`) orchestrates partition generation for specific ML tasks:
- **Supported Tasks:** `continuous_sign_recognition`, `isolated_sign_recognition`, `handshape_classification`, and `sign_language_translation`.
- **Signer-Independent Partitioning:** Derives splits by grouping recordings by `signer_id` and distributing signers across train (70%), validation (15%), and test (15%).
- **Draft Export:** Generates structured split manifests (`splits_draft.json`) containing task definitions and recording identifiers.

---

## 10. Split Reports
Partition validity is verified prior to compilation:
- **Automated Validation:** `SplitValidationScreen` invokes `validate_group_disjoint()` and `validate_no_augmentation_leakage()`.
- **Leak Detection:** Guarantees that no signer appears in multiple partitions and that augmented copies are strictly co-located with their parent recording.
- **Real-Time Diagnostics:** Displays validation summaries and split cardinality metrics in the UI console.

---

## 11. Release Manager
`ReleaseScreen` manages the formal publishing of immutable dataset releases:
- **Pre-Conditions:** Releases require valid `usage_scope` (`INTERNAL_RESEARCH` vs. `COMMERCIAL_TRAINING`), zero quarantined resources, zero split leakage, and verified consent.
- **Artifact Generation:** `DatasetReleaseManager.build_release()` writes `dataset_release.json` manifests containing checksums, code commit provenance, and split memberships.

---

## 12. UI Threading
To guarantee zero UI freezing on heavy I/O and frame decoding:
- **Worker Architecture:** Implemented `WorkerRunnable(QRunnable)` and `WorkerSignals` in `src/slt_studio/workers/task_worker.py`.
- **Background Dispatch:** Heavy tasks (PyAV video decoding, checksum calculation, EAF parsing) run on `QThreadPool.globalInstance()`.
- **Decoupled Services:** UI screens never contain raw SQL queries, permissions logic, or storage operations; all calls delegate to `CorpusService`, `ReviewService`, `AnnotationService`, `AdjudicationService`, and `DatasetService`.

---

## 13. Privacy and Access Control
Dataset Studio enforces privacy-by-design:
- **Pseudonymization:** Participant identifiers must match the pseudonym format (`validate_pseudonym_id()`). Direct personal data (names, identification numbers, addresses) are programmatically rejected from metadata schemas.
- **Offline Local Storage:** The entire architecture operates offline-first with zero external cloud transmission.
- **Quarantine Isolation:** External open datasets (LSC50, LSC70, LSC-54) are quarantined in separate directories and barred from commercial dataset releases.

---

## 14. Test Results
The Phase 3B suite has been verified under offscreen headless Qt environments:
- **Total Test Suite:** **192 / 192 passed** (100% pass rate).
- **Dataset Studio Tests:** Verified all 11 workspace screens in `tests/test_studio.py` and service operations in `tests/test_studio_services.py`.
- **Capture Timing Tests:** Verified timestamp sidecar serialization, checksum validation, and `CaptureIngestService` in `tests/test_capture_timing_and_ingest.py`.
- **Code Coverage:** $\ge 85\%$ across core corpus, capture, and studio services.
- **Static Analysis:**
  - `ruff check src tests tools`: 0 errors.
  - `mypy --strict`: 0 errors across 74 source files.

---

## 15. Known Limitations
1. **Camera Sensor Drift:** In variable-rate webcam feeds, monotonic system timestamps reflect software arrival rather than hardware sensor shutter exposure times.
2. **Facial Biometric Data:** Facial video retained in unmasked master takes constitutes biometric data under Ley 1581 and GDPR; raw storage must remain in encrypted offline volumes.
3. **Linear Adjudication:** Disagreement adjudication currently operates on individual annotation values; complex multi-tier segmentation realignment requires external ELAN re-import.

---

## 16. Approval Status
| Milestone | Status | Verifier |
| :--- | :--- | :--- |
| **Capture Engine (`slt_capture`)** | APPROVED | Automated Suite & Ingest Verification |
| **Timestamp Sidecars** | APPROVED | Monotonic Timing Contract |
| **Dataset Studio UI (11 Screens)** | APPROVED | Headless PySide6 Test Suite |
| **Decoupled Service Layer** | APPROVED | Transactional Service Tests |
| **Ethical & Community Gate** | PENDING REVIEW | Formal Ethics & Community Sign-off |
