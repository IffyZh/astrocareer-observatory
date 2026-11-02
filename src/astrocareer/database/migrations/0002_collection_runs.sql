PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE collection_runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    collector_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'success', 'partial', 'not_modified', 'failed'
    )),
    checkpoint_before TEXT,
    checkpoint_after TEXT,
    record_count INTEGER NOT NULL CHECK (record_count >= 0),
    issue_count INTEGER NOT NULL CHECK (issue_count >= 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (finished_at >= started_at),
    CHECK (status != 'failed' OR record_count = 0)
);

CREATE TABLE snapshots (
    snapshot_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES collection_runs(run_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    url TEXT NOT NULL,
    purpose TEXT,
    observed_at TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    content_type TEXT,
    content_sha256 TEXT NOT NULL CHECK (length(content_sha256) = 64),
    byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
    etag TEXT,
    last_modified TEXT,
    storage_path TEXT,
    UNIQUE (run_id, url, content_sha256)
);

CREATE TABLE source_record_observations (
    source_record_observation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES collection_runs(run_id) ON DELETE CASCADE,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    source_record_id TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    record_json TEXT NOT NULL,
    record_sha256 TEXT NOT NULL CHECK (length(record_sha256) = 64),
    posting_id TEXT REFERENCES postings(posting_id),
    UNIQUE (run_id, source_id, source_record_id)
);

CREATE TABLE collection_issues (
    issue_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES collection_runs(run_id) ON DELETE CASCADE,
    snapshot_id TEXT REFERENCES snapshots(snapshot_id) ON DELETE SET NULL,
    severity TEXT NOT NULL CHECK (severity IN ('warning', 'error')),
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    source_record_id TEXT,
    locator TEXT
);

ALTER TABLE observations ADD COLUMN snapshot_id TEXT REFERENCES snapshots(snapshot_id);

CREATE INDEX idx_collection_runs_source_time ON collection_runs(source_id, started_at);
CREATE INDEX idx_snapshots_source_time ON snapshots(source_id, observed_at);
CREATE INDEX idx_source_record_observations_identity ON source_record_observations(
    source_id, source_record_id, observed_at
);
CREATE INDEX idx_collection_issues_run ON collection_issues(run_id, severity);

INSERT INTO schema_migrations (version) VALUES (2);

COMMIT;

