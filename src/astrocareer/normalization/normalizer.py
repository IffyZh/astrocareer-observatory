"""Conservative, deterministic normalization rules for source postings."""

import re
from datetime import datetime

from astrocareer.collectors import SourcePosting
from astrocareer.normalization.models import (
    Availability,
    NormalizedCompensation,
    NormalizedDate,
    NormalizedEmploymentTerms,
    NormalizedField,
    NormalizedLanguage,
    NormalizedPostingCandidate,
)

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_IN_TEXT = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_DURATION_MONTHS = re.compile(r"\b(\d+)\s+months?\b", re.IGNORECASE)
_DURATION_YEARS = re.compile(r"\b(\d+(?:\.\d+)?)\s+years?\b", re.IGNORECASE)
_FTE = re.compile(r"\b(0(?:\.\d+)?|1(?:\.0+)?)\s*FTE\b", re.IGNORECASE)
_SALARY = re.compile(
    r"\b(?P<currency>[A-Z]{3})\s*"
    r"(?P<minimum>\d[\d,]*(?:\.\d+)?)"
    r"(?:\s*[-–]\s*(?P<maximum>\d[\d,]*(?:\.\d+)?))?"
    r"\s+per\s+(?P<period>year|month|week|day|hour)\b",
    re.IGNORECASE,
)

_JOB_FAMILIES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bpost[- ]?doctoral|\bpostdoc\b", re.IGNORECASE), "postdoc"),
    (re.compile(r"\bresearch software|\bRSE\b", re.IGNORECASE), "research_software"),
    (re.compile(r"\bprofessor|\bfaculty\b", re.IGNORECASE), "faculty"),
    (re.compile(r"\bresearch scientist\b", re.IGNORECASE), "research_scientist"),
    (re.compile(r"\btechnical staff|\btechnician\b", re.IGNORECASE), "technical_staff"),
    (re.compile(r"\bresearch support\b", re.IGNORECASE), "research_support"),
    (re.compile(r"\bdoctoral|\bPhD position\b", re.IGNORECASE), "doctoral"),
    (re.compile(r"\bintern(?:ship)?\b", re.IGNORECASE), "internship"),
)

_LANGUAGES = {
    "english": ("en", "English"),
    "portuguese": ("pt", "Portuguese"),
    "spanish": ("es", "Spanish"),
    "french": ("fr", "French"),
    "german": ("de", "German"),
}


def _missing(text: str | None) -> Availability:
    return Availability.NOT_REPORTED if not text else Availability.AMBIGUOUS


def _normalize_date(text: str | None) -> NormalizedDate:
    if not text:
        return NormalizedDate(None, None, Availability.NOT_REPORTED, text)
    stripped = text.strip()
    if _DATE.fullmatch(stripped):
        return NormalizedDate(stripped, "date", Availability.REPORTED, text)
    try:
        normalized = stripped.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return NormalizedDate(None, None, Availability.AMBIGUOUS, text)
    if "T" not in stripped:
        return NormalizedDate(None, None, Availability.AMBIGUOUS, text)
    value = parsed.isoformat().replace("+00:00", "Z")
    return NormalizedDate(value, "datetime", Availability.REPORTED, text)


def _extract_start_date(text: str | None) -> NormalizedDate:
    if not text:
        return NormalizedDate(None, None, Availability.NOT_REPORTED, text)
    match = _DATE_IN_TEXT.search(text)
    if not match:
        return NormalizedDate(None, None, Availability.AMBIGUOUS, text)
    return NormalizedDate(match.group(1), "date", Availability.REPORTED, text)


def _classify_job_family(title: str) -> NormalizedField[str]:
    matches = {family for pattern, family in _JOB_FAMILIES if pattern.search(title)}
    if len(matches) == 1:
        return NormalizedField(matches.pop(), Availability.DERIVED, title)
    return NormalizedField(None, Availability.AMBIGUOUS, title)


def _normalize_contract_type(text: str | None) -> NormalizedField[str]:
    if not text:
        return NormalizedField(None, Availability.NOT_REPORTED, text)
    lowered = text.casefold()
    matches: set[str] = set()
    if "permanent" in lowered or "open-ended" in lowered:
        matches.add("permanent")
    if "fixed-term" in lowered or "fixed term" in lowered:
        matches.add("fixed_term")
    if "fellowship" in lowered:
        matches.add("fellowship")
    if "temporary" in lowered:
        matches.add("temporary")
    if len(matches) == 1:
        return NormalizedField(matches.pop(), Availability.REPORTED, text)
    return NormalizedField(None, Availability.AMBIGUOUS, text)


def _normalize_contract_duration(text: str | None) -> NormalizedField[int]:
    if not text:
        return NormalizedField(None, Availability.NOT_REPORTED, text)
    month_match = _DURATION_MONTHS.search(text)
    if month_match:
        return NormalizedField(int(month_match.group(1)), Availability.REPORTED, text)
    year_match = _DURATION_YEARS.search(text)
    if year_match:
        months = float(year_match.group(1)) * 12
        if months.is_integer():
            return NormalizedField(int(months), Availability.DERIVED, text)
    return NormalizedField(None, Availability.AMBIGUOUS, text)


def _normalize_fraction(text: str | None) -> NormalizedField[float]:
    if not text:
        return NormalizedField(None, Availability.NOT_REPORTED, text)
    match = _FTE.search(text)
    if match:
        return NormalizedField(float(match.group(1)), Availability.REPORTED, text)
    lowered = text.casefold()
    if "full-time" in lowered or "full time" in lowered:
        return NormalizedField(1.0, Availability.DERIVED, text)
    return NormalizedField(None, Availability.AMBIGUOUS, text)


def _normalize_work_mode(text: str | None) -> NormalizedField[str]:
    if not text:
        return NormalizedField(None, Availability.NOT_REPORTED, text)
    lowered = text.casefold()
    matches = {
        value
        for keyword, value in (
            ("onsite", "onsite"),
            ("on-site", "onsite"),
            ("hybrid", "hybrid"),
            ("remote", "remote"),
            ("flexible", "flexible"),
        )
        if keyword in lowered
    }
    if len(matches) == 1:
        return NormalizedField(matches.pop(), Availability.REPORTED, text)
    return NormalizedField(None, Availability.AMBIGUOUS, text)


def _normalize_compensation(text: str | None) -> NormalizedCompensation:
    if not text:
        return NormalizedCompensation(
            None, None, None, None, None, Availability.NOT_REPORTED, text
        )
    match = _SALARY.search(text)
    if not match:
        return NormalizedCompensation(None, None, None, None, None, Availability.AMBIGUOUS, text)

    minimum = float(match.group("minimum").replace(",", ""))
    maximum_text = match.group("maximum")
    maximum = float(maximum_text.replace(",", "")) if maximum_text else minimum
    periods = {
        "year": "annual",
        "month": "monthly",
        "week": "weekly",
        "day": "daily",
        "hour": "hourly",
    }
    lowered = text.casefold()
    gross_net = "gross" if "gross" in lowered else "net" if "net" in lowered else "not_stated"
    return NormalizedCompensation(
        amount_min=minimum,
        amount_max=maximum,
        currency=match.group("currency").upper(),
        pay_period=periods[match.group("period").lower()],
        gross_net=gross_net,
        availability=Availability.REPORTED,
        official_text=text,
    )


def _requirement_level(text: str) -> str:
    lowered = text.casefold()
    if "required" in lowered or "must" in lowered:
        return "required"
    if "preferred" in lowered:
        return "preferred"
    if "desirable" in lowered:
        return "desirable"
    return "mentioned"


def _normalize_languages(texts: tuple[str, ...]) -> tuple[NormalizedLanguage, ...]:
    normalized: list[NormalizedLanguage] = []
    for text in texts:
        lowered = text.casefold()
        matches = [value for name, value in _LANGUAGES.items() if name in lowered]
        if len(matches) != 1:
            continue
        code, name = matches[0]
        normalized.append(
            NormalizedLanguage(
                language_code=code,
                language_name=name,
                requirement_level=_requirement_level(text),
                official_text=text,
            )
        )
    return tuple(normalized)


def normalize_source_posting(source: SourcePosting) -> NormalizedPostingCandidate:
    """Normalize only values supported by conservative deterministic rules."""
    normalized_title = " ".join(source.official_title.split())
    return NormalizedPostingCandidate(
        source_id=source.source_id,
        source_record_id=source.source_record_id,
        snapshot_sha256=source.snapshot_sha256,
        official_title=source.official_title,
        normalized_title=normalized_title,
        institution_text=source.institution_text,
        location_text=source.location_text,
        job_family=_classify_job_family(normalized_title),
        posted_at=_normalize_date(source.posted_at_text),
        application_deadline_at=_normalize_date(source.deadline_text),
        employment_terms=NormalizedEmploymentTerms(
            contract_type=_normalize_contract_type(source.contract_text),
            contract_duration_months=_normalize_contract_duration(source.contract_text),
            employment_fraction=_normalize_fraction(source.employment_fraction_text),
            start_date=_extract_start_date(source.start_date_text),
            work_mode=_normalize_work_mode(source.work_mode_text),
        ),
        compensation=_normalize_compensation(source.salary_text),
        languages=_normalize_languages(source.language_texts),
    )

