BEGIN IMMEDIATE;

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS participants (
    signer_id TEXT PRIMARY KEY,
    language_experience_band TEXT,
    self_reported_variant TEXT,
    metadata_schema_version TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consents (
    consent_id TEXT PRIMARY KEY,
    signer_id TEXT NOT NULL,
    form_version TEXT NOT NULL,
    signed_at_utc TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    revoked_at_utc TEXT,
    expires_at_utc TEXT,
    FOREIGN KEY (signer_id)
        REFERENCES participants(signer_id)
);

CREATE TABLE IF NOT EXISTS consent_purposes (
    consent_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    PRIMARY KEY (consent_id, purpose),
    FOREIGN KEY (consent_id)
        REFERENCES consents(consent_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    corpus_id TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_participants (
    session_id TEXT NOT NULL,
    signer_id TEXT NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (session_id, signer_id),
    FOREIGN KEY (session_id)
        REFERENCES sessions(session_id),
    FOREIGN KEY (signer_id)
        REFERENCES participants(signer_id)
);

CREATE TABLE IF NOT EXISTS recordings (
    recording_id TEXT PRIMARY KEY,
    corpus_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    duration_ns INTEGER,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    fps_num INTEGER,
    fps_den INTEGER,
    capture_protocol_version TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (session_id)
        REFERENCES sessions(session_id),
    CHECK (size_bytes > 0),
    CHECK (width > 0),
    CHECK (height > 0),
    CHECK (
        (fps_num IS NULL AND fps_den IS NULL)
        OR
        (fps_num > 0 AND fps_den > 0)
    )
);

CREATE TABLE IF NOT EXISTS recording_participants (
    recording_id TEXT NOT NULL,
    signer_id TEXT NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (recording_id, signer_id),
    FOREIGN KEY (recording_id)
        REFERENCES recordings(recording_id),
    FOREIGN KEY (signer_id)
        REFERENCES participants(signer_id)
);

CREATE TABLE IF NOT EXISTS recording_consents (
    recording_id TEXT NOT NULL,
    consent_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    PRIMARY KEY (recording_id, consent_id, purpose),
    FOREIGN KEY (recording_id)
        REFERENCES recordings(recording_id),
    FOREIGN KEY (consent_id)
        REFERENCES consents(consent_id)
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    recording_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    producer_json TEXT NOT NULL,
    parent_asset_id TEXT,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (recording_id)
        REFERENCES recordings(recording_id),
    FOREIGN KEY (parent_asset_id)
        REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS annotation_documents (
    document_id TEXT PRIMARY KEY,
    recording_id TEXT NOT NULL,
    format TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    annotator_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (recording_id)
        REFERENCES recordings(recording_id),
    CHECK (revision > 0)
);

CREATE TABLE IF NOT EXISTS annotations (
    annotation_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    source_annotation_id TEXT,
    tier_id TEXT NOT NULL,
    alignment_kind TEXT NOT NULL,
    start_ns INTEGER,
    end_ns INTEGER,
    value TEXT NOT NULL,
    parent_annotation_id TEXT,
    previous_annotation_id TEXT,
    revision INTEGER NOT NULL,
    status TEXT NOT NULL,
    boundary_quality TEXT NOT NULL,
    FOREIGN KEY (document_id)
        REFERENCES annotation_documents(document_id),
    FOREIGN KEY (parent_annotation_id)
        REFERENCES annotations(annotation_id),
    FOREIGN KEY (previous_annotation_id)
        REFERENCES annotations(annotation_id),
    CHECK (
        start_ns IS NULL
        OR start_ns >= 0
    ),
    CHECK (
        end_ns IS NULL
        OR end_ns >= 0
    ),
    CHECK (
        end_ns IS NULL
        OR start_ns IS NULL
        OR end_ns > start_ns
    ),
    CHECK (revision > 0)
);

CREATE TABLE IF NOT EXISTS annotation_revisions (
    revision_id TEXT PRIMARY KEY,
    annotation_id TEXT NOT NULL,
    previous_revision INTEGER,
    new_revision INTEGER NOT NULL,
    modified_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    old_value_json TEXT,
    new_value_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (annotation_id)
        REFERENCES annotations(annotation_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    annotation_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    notes TEXT,
    reviewed_at_utc TEXT NOT NULL,
    FOREIGN KEY (annotation_id)
        REFERENCES annotations(annotation_id)
);

CREATE TABLE IF NOT EXISTS dataset_releases (
    release_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    version TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    task TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    usage_scope TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    UNIQUE (dataset_id, version)
);

CREATE TABLE IF NOT EXISTS release_recordings (
    release_id TEXT NOT NULL,
    recording_id TEXT NOT NULL,
    split_name TEXT NOT NULL,
    PRIMARY KEY (release_id, recording_id),
    FOREIGN KEY (release_id)
        REFERENCES dataset_releases(release_id),
    FOREIGN KEY (recording_id)
        REFERENCES recordings(recording_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    details_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recordings_session
    ON recordings(session_id);

CREATE INDEX IF NOT EXISTS idx_recordings_status
    ON recordings(status);

CREATE INDEX IF NOT EXISTS idx_assets_recording
    ON assets(recording_id);

CREATE INDEX IF NOT EXISTS idx_annotations_document
    ON annotations(document_id);

CREATE INDEX IF NOT EXISTS idx_annotations_tier
    ON annotations(tier_id);

CREATE INDEX IF NOT EXISTS idx_releases_dataset
    ON dataset_releases(dataset_id);

PRAGMA user_version = 1;

COMMIT;
