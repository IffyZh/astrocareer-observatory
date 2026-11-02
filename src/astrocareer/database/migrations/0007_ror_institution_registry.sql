PRAGMA foreign_keys = ON;

BEGIN;

ALTER TABLE institutions ADD COLUMN ror_id TEXT;
ALTER TABLE institutions ADD COLUMN status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'withdrawn', 'local'));
ALTER TABLE institutions ADD COLUMN established_year INTEGER
    CHECK (established_year IS NULL OR established_year BETWEEN 1000 AND 9999);
ALTER TABLE institutions ADD COLUMN source_created_at TEXT;
ALTER TABLE institutions ADD COLUMN source_updated_at TEXT;
ALTER TABLE institutions ADD COLUMN updated_at TEXT;

CREATE UNIQUE INDEX idx_institutions_ror_id
ON institutions(ror_id)
WHERE ror_id IS NOT NULL;

CREATE TABLE institution_names (
    institution_id TEXT NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    language_code TEXT,
    name_types_json TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    PRIMARY KEY (institution_id, name, language_code, name_types_json)
);

CREATE TABLE institution_domains (
    institution_id TEXT NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    domain TEXT NOT NULL COLLATE NOCASE,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    PRIMARY KEY (institution_id, domain)
);

CREATE INDEX idx_institution_domains_domain ON institution_domains(domain);

CREATE TABLE institution_types (
    institution_id TEXT NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    organization_type TEXT NOT NULL CHECK (organization_type IN (
        'archive', 'company', 'education', 'facility', 'funder',
        'government', 'healthcare', 'nonprofit', 'other'
    )),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    PRIMARY KEY (institution_id, organization_type)
);

CREATE TABLE institution_locations (
    institution_id TEXT NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    geonames_id INTEGER NOT NULL,
    name TEXT,
    country_code TEXT CHECK (country_code IS NULL OR length(country_code) = 2),
    country_name TEXT,
    subdivision_code TEXT,
    subdivision_name TEXT,
    continent_code TEXT,
    latitude REAL CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    longitude REAL CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    PRIMARY KEY (institution_id, geonames_id)
);

CREATE TABLE institution_import_runs (
    import_run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    dataset_version TEXT NOT NULL,
    content_sha256 TEXT NOT NULL UNIQUE CHECK (length(content_sha256) = 64),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    record_count INTEGER NOT NULL CHECK (record_count >= 0),
    inserted_count INTEGER NOT NULL CHECK (inserted_count >= 0),
    updated_count INTEGER NOT NULL CHECK (updated_count >= 0),
    importer_version TEXT NOT NULL,
    schema_versions_json TEXT NOT NULL
);

INSERT INTO schema_migrations (version) VALUES (7);

COMMIT;
