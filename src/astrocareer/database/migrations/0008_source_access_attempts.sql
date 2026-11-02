PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE source_access_attempts (
    access_attempt_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    requested_at TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('dry_run', 'persisted')),
    contact_url TEXT NOT NULL CHECK (contact_url LIKE 'https://%'),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_source_access_attempts_source_time ON source_access_attempts(
    source_id, requested_at
);

INSERT INTO schema_migrations (version) VALUES (8);

COMMIT;
