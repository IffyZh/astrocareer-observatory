PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE source_access_policies (
    source_id TEXT PRIMARY KEY REFERENCES sources(source_id) ON DELETE CASCADE,
    access_status TEXT NOT NULL CHECK (access_status IN (
        'approved', 'manual_only', 'api_only', 'permission_required',
        'prohibited', 'pending_review'
    )),
    allowed_hosts_json TEXT NOT NULL,
    minimum_interval_seconds INTEGER NOT NULL CHECK (minimum_interval_seconds >= 0),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

INSERT INTO schema_migrations (version) VALUES (5);

COMMIT;

