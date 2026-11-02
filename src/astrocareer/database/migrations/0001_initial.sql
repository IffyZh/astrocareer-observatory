PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    organization TEXT,
    homepage_url TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN (
        'employer', 'professional_society', 'government', 'job_board',
        'research_dataset', 'community', 'other'
    )),
    authority_level TEXT NOT NULL CHECK (authority_level IN ('a', 'b', 'c', 'd')),
    collection_method TEXT NOT NULL CHECK (collection_method IN (
        'api', 'feed', 'email', 'html', 'manual', 'import'
    )),
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    robots_reviewed_at TEXT,
    terms_reviewed_at TEXT,
    redistribution_notes TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE institutions (
    institution_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country_code TEXT CHECK (country_code IS NULL OR length(country_code) = 2),
    homepage_url TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE postings (
    posting_id TEXT PRIMARY KEY,
    official_title TEXT NOT NULL,
    normalized_title TEXT,
    institution_id TEXT REFERENCES institutions(institution_id),
    job_family TEXT CHECK (job_family IS NULL OR job_family IN (
        'postdoc', 'faculty', 'research_scientist', 'research_software',
        'technical_staff', 'research_support', 'doctoral', 'internship', 'other'
    )),
    country_code TEXT CHECK (country_code IS NULL OR length(country_code) = 2),
    region TEXT,
    city TEXT,
    remote_status TEXT CHECK (remote_status IS NULL OR remote_status IN (
        'onsite', 'hybrid', 'remote', 'not_reported', 'ambiguous'
    )),
    positions_available INTEGER CHECK (positions_available IS NULL OR positions_available >= 0),
    positions_availability TEXT NOT NULL DEFAULT 'not_collected' CHECK (
        positions_availability IN (
            'reported', 'derived', 'not_reported', 'not_applicable',
            'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
            'not_collected', 'parsing_failed'
        )
    ),
    status TEXT NOT NULL DEFAULT 'observed' CHECK (status IN (
        'observed', 'open', 'closed', 'expired', 'withdrawn', 'filled', 'unknown'
    )),
    posted_at TEXT,
    posted_at_precision TEXT CHECK (posted_at_precision IS NULL OR posted_at_precision IN (
        'date', 'datetime', 'derived_date'
    )),
    application_deadline_at TEXT,
    deadline_precision TEXT CHECK (deadline_precision IS NULL OR deadline_precision IN (
        'date', 'datetime'
    )),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    source_updated_at TEXT,
    verified_at TEXT,
    closed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (last_seen_at >= first_seen_at),
    CHECK (
        (positions_availability IN ('reported', 'derived') AND positions_available IS NOT NULL)
        OR
        (positions_availability NOT IN ('reported', 'derived') AND positions_available IS NULL)
    )
);

CREATE TABLE observations (
    observation_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    source_record_id TEXT,
    canonical_url TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    http_status INTEGER,
    content_sha256 TEXT CHECK (content_sha256 IS NULL OR length(content_sha256) = 64),
    parser_version TEXT,
    collection_status TEXT NOT NULL CHECK (collection_status IN (
        'success', 'not_modified', 'inaccessible', 'parsing_failed', 'manual'
    )),
    raw_snapshot_location TEXT,
    UNIQUE (source_id, source_record_id, observed_at)
);

CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    observation_id TEXT REFERENCES observations(observation_id),
    canonical_url TEXT NOT NULL,
    source_organization TEXT,
    source_type TEXT NOT NULL CHECK (source_type IN (
        'official_posting', 'employer_document', 'government_policy',
        'professional_society', 'research_dataset', 'community_report', 'other'
    )),
    authority_level TEXT NOT NULL CHECK (authority_level IN ('a', 'b', 'c', 'd')),
    published_at TEXT,
    observed_at TEXT NOT NULL,
    content_sha256 TEXT CHECK (content_sha256 IS NULL OR length(content_sha256) = 64),
    parser_version TEXT,
    verification_method TEXT CHECK (verification_method IS NULL OR verification_method IN (
        'automated', 'manual', 'automated_and_manual'
    )),
    verified_at TEXT,
    locator TEXT,
    excerpt TEXT,
    redistribution_notes TEXT
);

CREATE TABLE eligibility_requirements (
    requirement_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    requirement_type TEXT NOT NULL CHECK (requirement_type IN (
        'degree', 'field', 'experience', 'citizenship', 'residence', 'language',
        'publication_record', 'availability_date', 'security_clearance', 'other'
    )),
    requirement_level TEXT NOT NULL CHECK (requirement_level IN (
        'required', 'preferred', 'desirable', 'informational'
    )),
    official_text TEXT,
    normalized_value_json TEXT,
    availability TEXT NOT NULL CHECK (availability IN (
        'reported', 'derived', 'not_reported', 'not_applicable',
        'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
        'not_collected', 'parsing_failed'
    )),
    evidence_id TEXT REFERENCES evidence(evidence_id),
    valid_from TEXT,
    valid_to TEXT,
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from),
    CHECK (availability NOT IN ('reported', 'derived') OR official_text IS NOT NULL)
);

CREATE TABLE skills (
    skill_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    category TEXT,
    description TEXT
);

CREATE TABLE skill_aliases (
    skill_id TEXT NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    alias TEXT NOT NULL COLLATE NOCASE,
    PRIMARY KEY (skill_id, alias)
);

CREATE TABLE skill_requirements (
    skill_requirement_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    skill_id TEXT REFERENCES skills(skill_id),
    official_term TEXT,
    requirement_level TEXT NOT NULL CHECK (requirement_level IN (
        'required', 'preferred', 'desirable', 'mentioned'
    )),
    experience_minimum_months INTEGER CHECK (
        experience_minimum_months IS NULL OR experience_minimum_months >= 0
    ),
    official_text TEXT,
    availability TEXT NOT NULL CHECK (availability IN (
        'reported', 'derived', 'not_reported', 'not_applicable',
        'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
        'not_collected', 'parsing_failed'
    )),
    evidence_id TEXT REFERENCES evidence(evidence_id),
    CHECK (availability NOT IN ('reported', 'derived') OR official_term IS NOT NULL)
);

CREATE TABLE recruitment_rounds (
    round_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    label TEXT,
    opened_at TEXT,
    closed_at TEXT,
    positions_available INTEGER CHECK (positions_available IS NULL OR positions_available >= 0),
    CHECK (closed_at IS NULL OR opened_at IS NULL OR closed_at >= opened_at)
);

CREATE TABLE recruitment_metrics (
    metric_id TEXT PRIMARY KEY,
    round_id TEXT NOT NULL REFERENCES recruitment_rounds(round_id) ON DELETE CASCADE,
    metric_type TEXT NOT NULL CHECK (metric_type IN (
        'applications_submitted', 'applications_eligible', 'applications_complete',
        'candidates_shortlisted', 'candidates_interviewed', 'offers_made', 'hires_final'
    )),
    value INTEGER CHECK (value IS NULL OR value >= 0),
    availability TEXT NOT NULL CHECK (availability IN (
        'reported', 'derived', 'not_reported', 'not_applicable',
        'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
        'not_collected', 'parsing_failed'
    )),
    as_of_at TEXT,
    population_definition TEXT,
    evidence_id TEXT REFERENCES evidence(evidence_id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (
        (availability IN ('reported', 'derived') AND value IS NOT NULL)
        OR
        (availability NOT IN ('reported', 'derived') AND value IS NULL)
    )
);

CREATE TABLE posting_events (
    event_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'first_seen', 'updated', 'deadline_changed', 'closed', 'expired',
        'withdrawn', 'reopened', 'filled', 'verification_changed'
    )),
    occurred_at TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    details_json TEXT,
    evidence_id TEXT REFERENCES evidence(evidence_id)
);

CREATE TABLE international_eligibility (
    international_eligibility_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    applicant_eligibility TEXT CHECK (applicant_eligibility IS NULL OR applicant_eligibility IN (
        'explicitly_open', 'open_with_conditions', 'citizenship_required',
        'residency_required', 'existing_work_authorization_required', 'restricted_other'
    )),
    applicant_eligibility_availability TEXT NOT NULL CHECK (
        applicant_eligibility_availability IN (
            'reported', 'derived', 'not_reported', 'not_applicable',
            'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
            'not_collected', 'parsing_failed'
        )
    ),
    work_authorization_requirement TEXT CHECK (
        work_authorization_requirement IS NULL OR work_authorization_requirement IN (
            'not_required', 'required_before_application', 'required_before_start',
            'employer_may_sponsor', 'other_condition'
        )
    ),
    work_authorization_availability TEXT NOT NULL CHECK (
        work_authorization_availability IN (
            'reported', 'derived', 'not_reported', 'not_applicable',
            'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
            'not_collected', 'parsing_failed'
        )
    ),
    visa_support TEXT CHECK (visa_support IS NULL OR visa_support IN (
        'sponsorship_available', 'relocation_or_visa_assistance_available',
        'case_by_case', 'sponsorship_unavailable'
    )),
    visa_support_availability TEXT NOT NULL CHECK (visa_support_availability IN (
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
        (applicant_eligibility_availability IN ('reported', 'derived') AND applicant_eligibility IS NOT NULL)
        OR
        (applicant_eligibility_availability NOT IN ('reported', 'derived') AND applicant_eligibility IS NULL)
    ),
    CHECK (
        (visa_support_availability IN ('reported', 'derived') AND visa_support IS NOT NULL)
        OR
        (visa_support_availability NOT IN ('reported', 'derived') AND visa_support IS NULL)
    ),
    CHECK (
        (work_authorization_availability IN ('reported', 'derived') AND work_authorization_requirement IS NOT NULL)
        OR
        (work_authorization_availability NOT IN ('reported', 'derived') AND work_authorization_requirement IS NULL)
    )
);

CREATE TABLE applicant_profiles (
    applicant_profile_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    profile_version INTEGER NOT NULL DEFAULT 1 CHECK (profile_version > 0),
    citizenship_group TEXT,
    residence_group TEXT,
    existing_work_authorization TEXT,
    degree_level TEXT,
    career_stage TEXT,
    is_public_scenario INTEGER NOT NULL DEFAULT 1 CHECK (is_public_scenario IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (name, profile_version)
);

CREATE TABLE international_access_assessments (
    assessment_id TEXT PRIMARY KEY,
    posting_id TEXT NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    applicant_profile_id TEXT NOT NULL REFERENCES applicant_profiles(applicant_profile_id),
    destination_country TEXT NOT NULL CHECK (length(destination_country) = 2),
    route_id TEXT,
    assessment_level TEXT CHECK (assessment_level IS NULL OR assessment_level IN (
        'low_friction', 'moderate', 'high', 'very_high', 'ineligible', 'indeterminate'
    )),
    eligibility_result TEXT CHECK (eligibility_result IS NULL OR eligibility_result IN (
        'apparently_eligible', 'conditionally_eligible', 'apparently_ineligible', 'indeterminate'
    )),
    explanation TEXT,
    availability TEXT NOT NULL CHECK (availability IN (
        'reported', 'derived', 'not_reported', 'not_applicable',
        'not_yet_available', 'inaccessible', 'ambiguous', 'redacted',
        'not_collected', 'parsing_failed'
    )),
    policy_as_of_at TEXT NOT NULL,
    assessed_at TEXT NOT NULL,
    method_version TEXT NOT NULL,
    expires_at TEXT,
    CHECK (expires_at IS NULL OR expires_at >= policy_as_of_at),
    CHECK (
        (availability = 'derived' AND assessment_level IS NOT NULL AND eligibility_result IS NOT NULL)
        OR
        (availability != 'derived' AND assessment_level IS NULL AND eligibility_result IS NULL)
    )
);

CREATE TABLE assessment_reasons (
    assessment_id TEXT NOT NULL REFERENCES international_access_assessments(assessment_id) ON DELETE CASCADE,
    reason_code TEXT NOT NULL CHECK (reason_code IN (
        'citizenship_restriction', 'residency_restriction',
        'existing_authorization_required', 'employer_sponsorship_required',
        'employer_sponsorship_confirmed', 'employer_sponsorship_not_stated',
        'salary_threshold_met', 'salary_threshold_uncertain',
        'occupation_or_researcher_route_available', 'qualification_recognition_required',
        'security_clearance_restriction', 'contract_too_short_for_route',
        'policy_source_outdated', 'insufficient_job_information'
    )),
    PRIMARY KEY (assessment_id, reason_code)
);

CREATE TABLE assessment_evidence (
    assessment_id TEXT NOT NULL REFERENCES international_access_assessments(assessment_id) ON DELETE CASCADE,
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id),
    evidence_role TEXT NOT NULL CHECK (evidence_role IN ('job', 'policy')),
    PRIMARY KEY (assessment_id, evidence_id, evidence_role)
);

CREATE INDEX idx_postings_deadline ON postings(application_deadline_at);
CREATE INDEX idx_postings_country_family ON postings(country_code, job_family);
CREATE INDEX idx_observations_posting_time ON observations(posting_id, observed_at);
CREATE INDEX idx_requirements_posting ON eligibility_requirements(posting_id);
CREATE INDEX idx_skill_requirements_posting ON skill_requirements(posting_id);
CREATE INDEX idx_metrics_round_type ON recruitment_metrics(round_id, metric_type, as_of_at);
CREATE INDEX idx_events_posting_time ON posting_events(posting_id, occurred_at);
CREATE INDEX idx_assessments_posting_profile ON international_access_assessments(
    posting_id, applicant_profile_id, policy_as_of_at
);

INSERT INTO schema_migrations (version) VALUES (1);

COMMIT;
