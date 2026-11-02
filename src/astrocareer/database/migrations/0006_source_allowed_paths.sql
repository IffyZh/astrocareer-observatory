PRAGMA foreign_keys = ON;

BEGIN;

ALTER TABLE source_access_policies
ADD COLUMN allowed_path_prefixes_json TEXT NOT NULL DEFAULT '["/"]';

INSERT INTO schema_migrations (version) VALUES (6);

COMMIT;
