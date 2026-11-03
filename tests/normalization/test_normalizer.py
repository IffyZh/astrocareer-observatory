"""Tests for conservative deterministic normalization."""

from astrocareer.collectors import SourcePosting
from astrocareer.normalization import Availability, normalize_source_posting


def _source_posting(**overrides: object) -> SourcePosting:
    values: dict[str, object] = {
        "source_id": "example-source",
        "source_record_id": "RSE-001",
        "snapshot_url": "https://jobs.example.test/",
        "snapshot_sha256": "a" * 64,
        "canonical_url": "https://jobs.example.test/RSE-001",
        "official_title": "  Research   Software Engineer  ",
        "institution_text": "Example Observatory",
        "location_text": "Example City, XZ",
        "posted_at_text": "2026-01-15",
        "deadline_text": "2026-03-01T23:59:00Z",
        "contract_text": "Fixed-term contract for 36 months.",
        "salary_text": "USD 70000-85000 per year, gross.",
        "employment_fraction_text": "Full-time, 1.0 FTE.",
        "start_date_text": "Expected start date: 2026-07-01.",
        "work_mode_text": "Hybrid work.",
        "language_texts": (
            "Professional working proficiency in English is required.",
        ),
    }
    values.update(overrides)
    return SourcePosting(**values)  # type: ignore[arg-type]


def test_normalize_explicit_demo_values() -> None:
    candidate = normalize_source_posting(_source_posting())

    assert candidate.normalized_title == "Research Software Engineer"
    assert candidate.job_family.value == "research_software"
    assert candidate.job_family.availability is Availability.DERIVED
    assert candidate.posted_at.value == "2026-01-15"
    assert candidate.posted_at.precision == "date"
    assert candidate.application_deadline_at.value == "2026-03-01T23:59:00Z"
    assert candidate.employment_terms.contract_type.value == "fixed_term"
    assert candidate.employment_terms.contract_duration_months.value == 36
    assert candidate.employment_terms.employment_fraction.value == 1.0
    assert candidate.employment_terms.start_date.value == "2026-07-01"
    assert candidate.employment_terms.work_mode.value == "hybrid"
    assert candidate.compensation.amount_min == 70000
    assert candidate.compensation.amount_max == 85000
    assert candidate.compensation.currency == "USD"
    assert candidate.compensation.pay_period == "annual"
    assert candidate.compensation.gross_net == "gross"
    assert candidate.languages[0].language_code == "en"
    assert candidate.languages[0].requirement_level == "required"


def test_year_duration_is_marked_as_derived() -> None:
    candidate = normalize_source_posting(
        _source_posting(contract_text="Fixed-term contract for 2 years.")
    )

    duration = candidate.employment_terms.contract_duration_months
    assert duration.value == 24
    assert duration.availability is Availability.DERIVED


def test_missing_values_remain_not_reported() -> None:
    candidate = normalize_source_posting(
        _source_posting(
            contract_text=None,
            salary_text=None,
            employment_fraction_text=None,
            start_date_text=None,
            work_mode_text=None,
            language_texts=(),
        )
    )

    assert candidate.employment_terms.contract_type.availability is Availability.NOT_REPORTED
    assert candidate.employment_terms.contract_duration_months.value is None
    assert candidate.compensation.availability is Availability.NOT_REPORTED
    assert candidate.languages == ()


def test_unrecognized_values_are_ambiguous_not_guessed() -> None:
    candidate = normalize_source_posting(
        _source_posting(
            official_title="Scientific Opportunity",
            contract_text="An attractive appointment may be offered.",
            salary_text="Competitive salary.",
            work_mode_text="Working arrangements will be discussed.",
        )
    )

    assert candidate.job_family.availability is Availability.AMBIGUOUS
    assert candidate.employment_terms.contract_type.availability is Availability.AMBIGUOUS
    assert candidate.compensation.availability is Availability.AMBIGUOUS
    assert candidate.employment_terms.work_mode.availability is Availability.AMBIGUOUS


def test_conflicting_job_family_is_ambiguous() -> None:
    candidate = normalize_source_posting(
        _source_posting(official_title="Postdoctoral Research Software Engineer")
    )

    assert candidate.job_family.value is None
    assert candidate.job_family.availability is Availability.AMBIGUOUS


def test_feed_mvp_fields_use_conservative_source_rules() -> None:
    candidate = normalize_source_posting(
        _source_posting(
            official_title="Open academic opportunity",
            source_category_text="Tenure and tenure-track faculty",
            department_text="Planetary Sciences",
            positions_text="2",
            extension_text="Likely extension for a third year",
            reference_code_text="ABC-123",
            official_announcement_url="https://careers.example.test/ABC-123",
            start_date_text="January 2027",
            work_mode_text="In person",
        )
    )

    assert candidate.job_family.value == "faculty"
    assert candidate.positions_available.value == 2
    assert candidate.extension_possible.value is True
    assert candidate.department_text == "Planetary Sciences"
    assert candidate.reference_code_text == "ABC-123"
    assert candidate.employment_terms.start_date.value == "2027-01"
    assert candidate.employment_terms.start_date.precision == "month"
    assert candidate.employment_terms.work_mode.value == "onsite"


def test_salary_symbols_require_period_and_safe_currency_context() -> None:
    candidate = normalize_source_posting(
        _source_posting(
            location_text="Pasadena, CA, USA",
            salary_text="$130k - $170k/year",
        )
    )

    assert candidate.compensation.amount_min == 130_000
    assert candidate.compensation.amount_max == 170_000
    assert candidate.compensation.currency == "USD"
    assert candidate.compensation.availability is Availability.DERIVED

    unresolved = normalize_source_posting(
        _source_posting(
            location_text="Location not stated",
            salary_text="$75,000",
        )
    )
    assert unresolved.compensation.amount_min is None
    assert unresolved.compensation.currency is None
    assert unresolved.compensation.availability is Availability.AMBIGUOUS


def test_duration_ranges_remain_ambiguous() -> None:
    for official_text in ("2+1 years", "4-5 years", "up to 3 years"):
        candidate = normalize_source_posting(
            _source_posting(contract_text=official_text)
        )
        assert candidate.employment_terms.contract_duration_months.value is None
        assert (
            candidate.employment_terms.contract_duration_months.availability
            is Availability.AMBIGUOUS
        )


def test_malformed_salary_range_remains_ambiguous() -> None:
    candidate = normalize_source_posting(
        _source_posting(
            location_text="Portsmouth, UK",
            salary_text="£36,320 - £40.704 per annum",
        )
    )

    assert candidate.compensation.amount_min is None
    assert candidate.compensation.availability is Availability.AMBIGUOUS
