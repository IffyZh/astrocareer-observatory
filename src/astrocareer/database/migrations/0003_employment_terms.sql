PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE employment_terms (
    employment_terms_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    contract_type TEXT CHECK (contract_type IS NULL OR contract_type IN (
        'permanent', 'fixed_term', 'fellowship', 'temporary', 'casual', 'other'
    )),
    contract_type_availability TEXT NOT NULL CHECK (contract_type_availability IN (
        'reported', 'derived', 'not_reported', 'not_applicable',
        'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
        'not_collected', 'parsing_failed'
    )),
    contract_duration_months INTEGER CHECK (
        contract_duration_months IS NULL OR contract_duration_months >= 0
    ),
    contract_duration_availability TEXT NOT NULL CHECK (
        contract_duration_availability IN (
            'reported', 'derived', 'not_reported', 'not_applicable',
            'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
            'not_collected', 'parsing_failed'
        )
    ),
    employment_fraction REAL CHECK (
        employment_fraction IS NULL OR
        (employment_fraction > 0.0 AND employment_fraction <= 1.0)
    ),
    employment_fraction_availability TEXT NOT NULL CHECK (
        employment_fraction_availability IN (
            'reported', 'derived', 'not_reported', 'not_applicable',
            'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
            'not_collected', 'parsing_failed'
        )
    ),
    start_date TEXT,
    start_date_precision TEXT CHECK (
        start_date_precision IS NULL OR start_date_precision IN ('date', 'month', 'year', 'text')
    ),
    start_date_availability TEXT NOT NULL CHECK (start_date_availability IN (
        'reported', 'derived', 'not_reported', 'not_applicable',
        'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
        'not_collected', 'parsing_failed'
    )),
    work_mode TEXT CHECK (work_mode IS NULL OR work_mode IN (
        'onsite', 'hybrid', 'remote', 'flexible', 'other'
    )),
    work_mode_availability TEXT NOT NULL CHECK (work_mode_availability IN (
        'reported', 'derived', 'not_reported', 'not_applicable',
        'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
        'not_collected', 'parsing_failed'
    )),
    official_text TEXT,
    evidence_id TEXT REFERENCES evidence(evidence_id),
    valid_from TEXT,
    valid_to TEXT,
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from),
    CHECK (
        (contract_type_availability IN ('reported', 'derived') AND contract_type IS NOT NULL)
        OR
        (contract_type_availability NOT IN ('reported', 'derived') AND contract_type IS NULL)
    ),
    CHECK (
        (contract_duration_availability IN ('reported', 'derived') AND contract_duration_months IS NOT NULL)
        OR
        (contract_duration_availability NOT IN ('reported', 'derived') AND contract_duration_months IS NULL)
    ),
    CHECK (
        (employment_fraction_availability IN ('reported', 'derived') AND employment_fraction IS NOT NULL)
        OR
        (employment_fraction_availability NOT IN ('reported', 'derived') AND employment_fraction IS NULL)
    ),
    CHECK (
        (start_date_availability IN ('reported', 'derived') AND start_date IS NOT NULL)
        OR
        (start_date_availability NOT IN ('reported', 'derived') AND start_date IS NULL)
    ),
    CHECK (
        (work_mode_availability IN ('reported', 'derived') AND work_mode IS NOT NULL)
        OR
        (work_mode_availability NOT IN ('reported', 'derived') AND work_mode IS NULL)
    )
);

CREATE TABLE compensations (
    compensation_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    amount_min REAL CHECK (amount_min IS NULL OR amount_min >= 0),
    amount_max REAL CHECK (amount_max IS NULL OR amount_max >= 0),
    currency TEXT CHECK (currency IS NULL OR length(currency) = 3),
    pay_period TEXT CHECK (pay_period IS NULL OR pay_period IN (
        'annual', 'monthly', 'weekly', 'daily', 'hourly', 'total_contract'
    )),
    gross_net TEXT CHECK (gross_net IS NULL OR gross_net IN (
        'gross', 'net', 'not_stated'
    )),
    availability TEXT NOT NULL CHECK (availability IN (
        'reported', 'derived', 'not_reported', 'not_applicable',
        'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
        'not_collected', 'parsing_failed'
    )),
    official_text TEXT,
    evidence_id TEXT REFERENCES evidence(evidence_id),
    valid_from TEXT,
    valid_to TEXT,
    CHECK (amount_max IS NULL OR amount_min IS NULL OR amount_max >= amount_min),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from),
    CHECK (
        (
            availability IN ('reported', 'derived')
            AND (amount_min IS NOT NULL OR amount_max IS NOT NULL)
            AND currency IS NOT NULL
            AND pay_period IS NOT NULL
        )
        OR
        (
            availability NOT IN ('reported', 'derived')
            AND amount_min IS NULL
            AND amount_max IS NULL
            AND currency IS NULL
            AND pay_period IS NULL
            AND gross_net IS NULL
        )
    )
);

CREATE TABLE posting_languages (
    posting_language_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    language_code TEXT,
    language_name TEXT,
    requirement_level TEXT NOT NULL CHECK (requirement_level IN (
        'required', 'preferred', 'desirable', 'mentioned'
    )),
    availability TEXT NOT NULL CHECK (availability IN (
        'reported', 'derived', 'not_reported', 'not_applicable',
        'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
        'not_collected', 'parsing_failed'
    )),
    official_text TEXT,
    evidence_id TEXT REFERENCES evidence(evidence_id),
    CHECK (
        (availability IN ('reported', 'derived') AND language_name IS NOT NULL)
        OR
        (availability NOT IN ('reported', 'derived') AND language_name IS NULL AND language_code IS NULL)
    )
);

CREATE INDEX idx_employment_terms_posting ON employment_terms(posting_id);
CREATE INDEX idx_compensations_posting ON compensations(posting_id);
CREATE INDEX idx_posting_languages_posting ON posting_languages(posting_id);

INSERT INTO schema_migrations (version) VALUES (3);

COMMIT;

