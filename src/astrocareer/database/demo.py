"""Load a fictional, internally consistent demonstration dataset."""

import hashlib
import sqlite3

DEMO_POSTING_ID = "demo-posting-rse-2026"
DEMO_ROUND_ID = "demo-round-rse-2026"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _seed_employment_details(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO employment_terms (
            employment_terms_id, posting_id,
            contract_type, contract_type_availability,
            contract_duration_months, contract_duration_availability,
            employment_fraction, employment_fraction_availability,
            start_date, start_date_precision, start_date_availability,
            work_mode, work_mode_availability, official_text, evidence_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "demo-employment-terms",
            DEMO_POSTING_ID,
            "fixed_term",
            "reported",
            36,
            "reported",
            1.0,
            "reported",
            "2026-07-01",
            "date",
            "reported",
            "hybrid",
            "reported",
            "Fixed-term contract for 36 months; full-time; expected start 2026-07-01; hybrid work.",
            "demo-evidence-job",
        ),
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO compensations (
            compensation_id, posting_id, amount_min, amount_max,
            currency, pay_period, gross_net, availability,
            official_text, evidence_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "demo-compensation",
            DEMO_POSTING_ID,
            70000,
            85000,
            "USD",
            "annual",
            "gross",
            "reported",
            "USD 70000-85000 per year, gross.",
            "demo-evidence-job",
        ),
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO posting_languages (
            posting_language_id, posting_id, language_code, language_name,
            requirement_level, availability, official_text, evidence_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "demo-language-english",
            DEMO_POSTING_ID,
            "en",
            "English",
            "required",
            "reported",
            "Professional working proficiency in English is required.",
            "demo-evidence-job",
        ),
    )


def seed_demo_data(connection: sqlite3.Connection) -> bool:
    """Insert the fictional demo dataset.

    Returns ``True`` when rows were inserted and ``False`` when the complete
    demo posting was already present. All names and URLs are intentionally
    fictional.
    """
    existing = connection.execute(
        "SELECT 1 FROM postings WHERE posting_id = ?", (DEMO_POSTING_ID,)
    ).fetchone()
    if existing:
        with connection:
            _seed_employment_details(connection)
        return False

    observed_at = "2026-11-01T12:00:00Z"
    job_url = "https://careers.example-observatory.test/jobs/rse-2026"
    policy_url = "https://immigration.example-government.test/researcher-route"
    job_text = (
        "Fictional Research Software Engineer vacancy. International applications "
        "are welcome and visa sponsorship is available."
    )
    policy_text = (
        "Fictional researcher route policy used only to demonstrate policy provenance."
    )

    with connection:
        connection.executemany(
            """
            INSERT INTO sources (
                source_id, name, organization, homepage_url, source_type,
                authority_level, collection_method, enabled,
                robots_reviewed_at, terms_reviewed_at, redistribution_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "demo-source-employer",
                    "Example Observatory Careers",
                    "Example Observatory",
                    "https://careers.example-observatory.test/",
                    "employer",
                    "a",
                    "manual",
                    0,
                    "2026-11-01",
                    "2026-11-01",
                    "Fictional source for tests and demonstrations only.",
                ),
                (
                    "demo-source-policy",
                    "Example Government Immigration Service",
                    "Example Government",
                    "https://immigration.example-government.test/",
                    "government",
                    "a",
                    "manual",
                    0,
                    "2026-11-01",
                    "2026-11-01",
                    "Fictional policy source for demonstrations only.",
                ),
            ],
        )
        connection.execute(
            """
            INSERT INTO institutions (
                institution_id, name, country_code, homepage_url
            ) VALUES (?, ?, ?, ?)
            """,
            (
                "demo-institution-observatory",
                "Example Observatory",
                "XZ",
                "https://www.example-observatory.test/",
            ),
        )
        connection.execute(
            """
            INSERT INTO postings (
                posting_id, official_title, normalized_title, institution_id,
                job_family, country_code, city, remote_status,
                positions_available, positions_availability, status,
                posted_at, posted_at_precision, application_deadline_at,
                deadline_precision, first_seen_at, last_seen_at, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                DEMO_POSTING_ID,
                "Research Software Engineer for Astronomical Data Systems",
                "Research Software Engineer",
                "demo-institution-observatory",
                "research_software",
                "XZ",
                "Example City",
                "hybrid",
                1,
                "reported",
                "filled",
                "2026-01-15",
                "date",
                "2026-03-01T23:59:00Z",
                "datetime",
                observed_at,
                "2026-11-01T12:00:00Z",
                "2026-11-01T12:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO observations (
                observation_id, posting_id, source_id, source_record_id,
                canonical_url, observed_at, http_status, content_sha256,
                parser_version, collection_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "demo-observation-job",
                DEMO_POSTING_ID,
                "demo-source-employer",
                "RSE-2026-001",
                job_url,
                observed_at,
                200,
                _sha256(job_text),
                "demo-manual-1",
                "manual",
            ),
        )
        connection.executemany(
            """
            INSERT INTO evidence (
                evidence_id, source_id, observation_id, canonical_url,
                source_organization, source_type, authority_level,
                published_at, observed_at, content_sha256, parser_version,
                verification_method, verified_at, locator, excerpt,
                redistribution_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "demo-evidence-job",
                    "demo-source-employer",
                    "demo-observation-job",
                    job_url,
                    "Example Observatory",
                    "official_posting",
                    "a",
                    "2026-01-15",
                    observed_at,
                    _sha256(job_text),
                    "demo-manual-1",
                    "manual",
                    "2026-06-15T09:00:00Z",
                    "Vacancy page, requirements and eligibility sections",
                    job_text,
                    "Fictional text; redistribution permitted for the demo.",
                ),
                (
                    "demo-evidence-policy",
                    "demo-source-policy",
                    None,
                    policy_url,
                    "Example Government",
                    "government_policy",
                    "a",
                    "2026-01-01",
                    observed_at,
                    _sha256(policy_text),
                    None,
                    "manual",
                    "2026-06-15T09:00:00Z",
                    "Researcher route eligibility section",
                    policy_text,
                    "Fictional text; redistribution permitted for the demo.",
                ),
            ],
        )
        connection.executemany(
            """
            INSERT INTO eligibility_requirements (
                requirement_id, posting_id, requirement_type, requirement_level,
                official_text, normalized_value_json, availability, evidence_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "demo-requirement-degree",
                    DEMO_POSTING_ID,
                    "degree",
                    "required",
                    "A PhD in astronomy, physics, computer science, or a related field is required.",
                    '{"degree":"PhD","fields":["astronomy","physics","computer science"]}',
                    "reported",
                    "demo-evidence-job",
                ),
                (
                    "demo-requirement-language",
                    DEMO_POSTING_ID,
                    "language",
                    "required",
                    "Professional working proficiency in English is required.",
                    '{"language":"English","level":"professional working"}',
                    "reported",
                    "demo-evidence-job",
                ),
            ],
        )
        connection.executemany(
            "INSERT INTO skills (skill_id, canonical_name, category) VALUES (?, ?, ?)",
            [
                ("demo-skill-python", "Python", "programming_language"),
                ("demo-skill-sql", "SQL", "data"),
                ("demo-skill-hpc", "High-performance computing", "computing"),
            ],
        )
        connection.executemany(
            "INSERT INTO skill_aliases (skill_id, alias) VALUES (?, ?)",
            [
                ("demo-skill-python", "Python 3"),
                ("demo-skill-hpc", "HPC"),
            ],
        )
        connection.executemany(
            """
            INSERT INTO skill_requirements (
                skill_requirement_id, posting_id, skill_id, official_term,
                requirement_level, experience_minimum_months, official_text,
                availability, evidence_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "demo-skill-requirement-python",
                    DEMO_POSTING_ID,
                    "demo-skill-python",
                    "Python",
                    "required",
                    None,
                    "Strong Python software development skills are required.",
                    "reported",
                    "demo-evidence-job",
                ),
                (
                    "demo-skill-requirement-sql",
                    DEMO_POSTING_ID,
                    "demo-skill-sql",
                    "SQL",
                    "preferred",
                    None,
                    "Experience with SQL is preferred.",
                    "reported",
                    "demo-evidence-job",
                ),
                (
                    "demo-skill-requirement-hpc",
                    DEMO_POSTING_ID,
                    "demo-skill-hpc",
                    "HPC",
                    "desirable",
                    None,
                    "HPC experience is desirable.",
                    "reported",
                    "demo-evidence-job",
                ),
            ],
        )
        connection.execute(
            """
            INSERT INTO recruitment_rounds (
                round_id, posting_id, label, opened_at, closed_at, positions_available
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                DEMO_ROUND_ID,
                DEMO_POSTING_ID,
                "2026 recruitment round",
                "2026-01-15",
                "2026-06-15",
                1,
            ),
        )
        connection.executemany(
            """
            INSERT INTO recruitment_metrics (
                metric_id, round_id, metric_type, value, availability,
                as_of_at, population_definition, evidence_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "demo-metric-applications",
                    DEMO_ROUND_ID,
                    "applications_submitted",
                    37,
                    "reported",
                    "2026-06-15",
                    "All applications submitted before the deadline.",
                    "demo-evidence-job",
                ),
                (
                    "demo-metric-interviews",
                    DEMO_ROUND_ID,
                    "candidates_interviewed",
                    5,
                    "reported",
                    "2026-06-15",
                    "Candidates who completed a formal interview.",
                    "demo-evidence-job",
                ),
                (
                    "demo-metric-offers",
                    DEMO_ROUND_ID,
                    "offers_made",
                    2,
                    "reported",
                    "2026-06-15",
                    "Formal offers issued during the recruitment round.",
                    "demo-evidence-job",
                ),
                (
                    "demo-metric-hires",
                    DEMO_ROUND_ID,
                    "hires_final",
                    1,
                    "reported",
                    "2026-06-15",
                    "Candidate who accepted and was formally hired.",
                    "demo-evidence-job",
                ),
            ],
        )
        connection.executemany(
            """
            INSERT INTO posting_events (
                event_id, posting_id, event_type, occurred_at,
                observed_at, details_json, evidence_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "demo-event-first-seen",
                    DEMO_POSTING_ID,
                    "first_seen",
                    observed_at,
                    observed_at,
                    '{"source_record_id":"RSE-2026-001"}',
                    "demo-evidence-job",
                ),
                (
                    "demo-event-filled",
                    DEMO_POSTING_ID,
                    "filled",
                    "2026-06-15T09:00:00Z",
                    "2026-06-15T09:00:00Z",
                    '{"hires_final":1}',
                    "demo-evidence-job",
                ),
            ],
        )
        connection.execute(
            """
            INSERT INTO international_eligibility (
                international_eligibility_id, posting_id,
                applicant_eligibility, applicant_eligibility_availability,
                work_authorization_requirement, work_authorization_availability,
                visa_support, visa_support_availability,
                official_text, evidence_id, valid_from
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "demo-international-eligibility",
                DEMO_POSTING_ID,
                "explicitly_open",
                "reported",
                "employer_may_sponsor",
                "reported",
                "sponsorship_available",
                "reported",
                "International applications are welcome and visa sponsorship is available.",
                "demo-evidence-job",
                "2026-01-15",
            ),
        )
        connection.execute(
            """
            INSERT INTO applicant_profiles (
                applicant_profile_id, name, description, profile_version,
                citizenship_group, residence_group, existing_work_authorization,
                degree_level, career_stage, is_public_scenario
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "demo-profile-international-phd-v1",
                "International PhD applicant without local work authorization",
                "Non-identifying public scenario used only for demonstration.",
                1,
                "non_domestic",
                "outside_destination_country",
                "none",
                "doctorate",
                "early_career",
                1,
            ),
        )
        connection.execute(
            """
            INSERT INTO international_access_assessments (
                assessment_id, posting_id, applicant_profile_id,
                destination_country, route_id, assessment_level,
                eligibility_result, explanation, availability,
                policy_as_of_at, assessed_at, method_version, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "demo-assessment-international-phd",
                DEMO_POSTING_ID,
                "demo-profile-international-phd-v1",
                "XZ",
                "fictional-researcher-route",
                "moderate",
                "conditionally_eligible",
                "The fictional employer confirms sponsorship and a fictional researcher route exists.",
                "derived",
                "2026-06-15",
                "2026-06-15T09:00:00Z",
                "demo-rules-1",
                "2026-12-15",
            ),
        )
        connection.executemany(
            "INSERT INTO assessment_reasons (assessment_id, reason_code) VALUES (?, ?)",
            [
                (
                    "demo-assessment-international-phd",
                    "employer_sponsorship_confirmed",
                ),
                (
                    "demo-assessment-international-phd",
                    "occupation_or_researcher_route_available",
                ),
            ],
        )
        connection.executemany(
            """
            INSERT INTO assessment_evidence (
                assessment_id, evidence_id, evidence_role
            ) VALUES (?, ?, ?)
            """,
            [
                (
                    "demo-assessment-international-phd",
                    "demo-evidence-job",
                    "job",
                ),
                (
                    "demo-assessment-international-phd",
                    "demo-evidence-policy",
                    "policy",
                ),
            ],
        )
        _seed_employment_details(connection)
    return True
