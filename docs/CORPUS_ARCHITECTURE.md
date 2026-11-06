# SLT Corpus Architecture & Storage Specification
**System:** SLT Bilingual Core — Colombian Sign Language (LSC)  
**Version:** 1.0.0  
**Scope:** Offline-first, Content-Addressed, Relational Catalog  

---

## 1. System Boundaries

The `slt_corpus` subsystem manages the acquisition, cataloging, ingestion, and validation of linguistic media and annotations. It operates under strict modularity:
- **Zero GUI / Video Codec dependencies:** Does not import Qt, OpenCV, or MediaPipe.
- **Pure Standard Library Core:** Utilizes Python `sqlite3`, `pathlib`, `hashlib`, and `xml.etree.ElementTree` for core persistence.
- **Content-Addressed Immutability:** Files are addressed strictly by their SHA-256 digest, preventing overwrite corruption and tracking bitrot.

```
       [Raw Capture Source]
                │
                ▼
      [Informed Consent Gate] ─── (Rejects unauthorized/revoked requests)
                │
                ▼
    [Content-Addressed Ingest]
                │
    ┌───────────┴───────────┐
    ▼                       ▼
[data/private/objects/]  [catalog.sqlite3]
(Raw .mp4 by SHA-256)    (Referential Catalog)
                            │
    ┌───────────────────────┴───────────────────────┐
    ▼                                               ▼
[ELAN Adapter (.eaf)]                      [Split & Release Manager]
(Converts ms -> ns)                        (Signer-Independent Manifests)
```

---

## 2. Relational Schema & Integrity

The catalog schema in `catalog.sqlite3` enforces `PRAGMA foreign_keys = ON;` across 10 tables:
1. `participants`: Pseudonymous signer IDs (`signer_id`), creation timestamps, JSON metadata excluding PII.
2. `consents`: Explicit purpose grants (`granted_purposes_json`), evidence SHA-256, optional revocation timestamp (`revoked_at_utc`).
3. `sessions`: Controlled recording sessions bound to a protocol ID and participant.
4. `recordings`: Ingested video files with resolution, duration (ns), codec, container, and SHA-256 digest. Includes `parent_recording_id` for augmentation tracking.
5. `assets`: Extracted features (e.g. landmark series, optical flow) linked to parent recordings with extractor provenance (name, version, model SHA-256, config hash).
6. `annotation_documents`: Annotation container associated with a recording.
7. `annotations`: Nanosecond semi-open intervals $[start, end)$ with tier IDs and revision counters.
8. `annotation_reviews`: Review statuses and comments by independent linguistic reviewers.
9. `dataset_releases`: Immutable release manifest records linked to usage scopes.
10. `split_assignments`: Disjoint split allocations (`train`, `validation`, `test`) linking recordings and signers.

---

## 3. Storage Hierarchy & Naming

Media files are stored under `data/private/objects/sha256/`:
```
data/private/
├── catalog.sqlite3
└── objects/
    └── sha256/
        ├── 0a/
        │   └── 0a1b2c3d...mp4
        ├── 81/
        │   └── 813ca528...mp4
        └── ...
```
- Primary directory prefix: First two characters of the hexadecimal SHA-256 digest.
- Filename: Full 64-character lowercase hexadecimal digest followed by lowercase container suffix (`.mp4`, `.mov`, `.webm`, etc.).
- Writes are performed atomically via isolated `.tmp` files created in the destination directory and replaced once checksum verification passes.
