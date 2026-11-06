# SLT Dataset Versioning & Release Manifest Specification
**SLT Bilingual Core — Colombian Sign Language**  
**Version:** 1.0.0 (Phase 3A)  

---

## 1. Semantic Versioning Principles for Linguistic Datasets

Dataset releases adhere to Semantic Versioning (`MAJOR.MINOR.PATCH`):
- **MAJOR (X.0.0):** Breaking structural or semantic changes (e.g. restructuring tier semantics, changing task definition from isolated to continuous, redefining gloss tokenization).
- **MINOR (0.Y.0):** Backwards-compatible expansion of recordings, participants, validated lexical signs, or reviewed annotation documents.
- **PATCH (0.0.Z):** Non-semantic metadata corrections, typo fixes in commentary, or hash updates without altering underlying training splits or audio/video data.

---

## 2. Release Manifest Structure

Every approved release is represented by an immutable `dataset_release.json` paired with `splits.json`:
```json
{
  "schema_version": "1.0.0",
  "release_id": "lsc_continuous_0_1_0",
  "dataset_id": "lsc-continuous",
  "dataset_version": "0.1.0",
  "profile_id": "lsc",
  "task": "continuous_sign_recognition",
  "created_at_utc": "2026-11-06T10:00:00Z",
  "corpus_version": "0.1.0",
  "annotation_schema_version": "1.0.0",
  "usage_scope": "internal_research",
  "split_manifest_relpath": "splits.json",
  "approval_status": "draft",
  "source_recording_ids": ["rec_001", "rec_002"],
  "annotation_document_ids": ["doc_001"],
  "license_review_status": "verified_internal",
  "parent_release_id": null,
  "code_commit": "8701c22"
}
```

---

## 3. Extractor & Model Provenance Lineage

Derived landmark sequences and numerical features (`Asset`) retain cryptographic links to the exact neural extractor that generated them:
- `extractor_name`: e.g. `mediapipe_hand_landmarker`
- `extractor_version`: e.g. `1.2.2`
- `model_sha256`: SHA-256 of the task model weights file
- `configuration_hash`: SHA-256 of the pipeline configuration dictionary
- `source_video_sha256`: Digest of the unedited parent video
