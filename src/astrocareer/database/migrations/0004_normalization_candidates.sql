PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE normalization_candidates (
    candidate_id TEXT PRIMARY KEY,
    source_record_observation_id TEXT NOT NULL
        REFERENCES source_record_observations(source_record_observation_id)
        ON DELETE CASCADE,
    normalizer_version TEXT NOT NULL,
    candidate_json TEXT NOT NULL,
    candidate_sha256 TEXT NOT NULL CHECK (length(candidate_sha256) = 64),
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN (
        'pending', 'accepted', 'rejected', 'superseded'
    )),
    review_notes TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (source_record_observation_id, normalizer_version, candidate_sha256),
    CHECK (
        (review_status = 'pending' AND reviewed_at IS NULL)
        OR
        (review_status != 'pending' AND reviewed_at IS NOT NULL)
    )
);

CREATE INDEX idx_normalization_candidates_review ON normalization_candidates(
    review_status, created_at
);

INSERT INTO schema_migrations (version) VALUES (4);

COMMIT;

