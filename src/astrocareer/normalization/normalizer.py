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
_DURATION_YEARS = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*(?:years?|yrs?)\b", re.IGNORECASE)
_FTE = re.compile(r"\b(0(?:\.\d+)?|1(?:\.0+)?)\s*FTE\b", re.IGNORECASE)
_MONTHS = {
    name: index
    for index, name in enumerate(
        (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ),
        start=1,
    )
}
_MONTH_YEAR = re.compile(
    rf"\b({'|'.join(_MONTHS)})[,]?\s+(\d{{4}})\b",
    re.IGNORECASE,
)
_NUMBER_WORDS = {
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
}

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

_SOURCE_CATEGORY_FAMILIES = {
    "postdocs and fellowships": "postdoc",
    "ph.d. positions": "doctoral",
    "tenure and tenure-track faculty": "faculty",
    "non-tenure track faculty": "faculty",
    "internships": "internship",
}

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
    if match:
        return NormalizedDate(match.group(1), "date", Availability.REPORTED, text)
    month_match = _MONTH_YEAR.search(text)
    if month_match:
        month = _MONTHS[month_match.group(1).casefold()]
        return NormalizedDate(
            f"{month_match.group(2)}-{month:02d}",
            "month",
            Availability.REPORTED,
            text,
        )
    year_match = re.fullmatch(r"\s*(\d{4})\s*", text)
    if year_match:
        return NormalizedDate(year_match.group(1), "year", Availability.REPORTED, text)
    return NormalizedDate(None, None, Availability.AMBIGUOUS, text)


def _classify_job_family(
    title: str,
    source_category: str | None,
) -> NormalizedField[str]:
    if source_category:
        category_family = _SOURCE_CATEGORY_FAMILIES.get(source_category.casefold())
        if category_family:
            return NormalizedField(
                category_family,
                Availability.DERIVED,
                source_category,
            )
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
    lowered = text.casefold()
    if "up to" in lowered or re.search(r"\d\s*[+-]\s*\d", text):
        return NormalizedField(None, Availability.AMBIGUOUS, text)
    if re.search(r"\d\s*[-–]\s*\d", text):
        return NormalizedField(None, Availability.AMBIGUOUS, text)
    month_match = _DURATION_MONTHS.search(text)
    if month_match:
        return NormalizedField(int(month_match.group(1)), Availability.REPORTED, text)
    year_match = _DURATION_YEARS.search(text)
    if year_match:
        months = float(year_match.group(1).replace(",", ".")) * 12
        if months.is_integer():
            return NormalizedField(int(months), Availability.DERIVED, text)
    for word, years in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+years?\b", lowered):
            return NormalizedField(int(years * 12), Availability.DERIVED, text)
    return NormalizedField(None, Availability.AMBIGUOUS, text)


def _normalize_positions(text: str | None) -> NormalizedField[int]:
    if not text:
        return NormalizedField(None, Availability.NOT_REPORTED, text)
    stripped = text.strip()
    if stripped.isdigit():
        return NormalizedField(int(stripped), Availability.REPORTED, text)
    match = re.fullmatch(r"fulltime\s*\((\d+)\s+positions?\)", stripped, re.IGNORECASE)
    if match:
        return NormalizedField(int(match.group(1)), Availability.REPORTED, text)
    return NormalizedField(None, Availability.AMBIGUOUS, text)


def _normalize_extension(text: str | None) -> NormalizedField[bool]:
    if not text:
        return NormalizedField(None, Availability.NOT_REPORTED, text)
    lowered = text.strip().casefold()
    if lowered == "yes":
        return NormalizedField(True, Availability.REPORTED, text)
    if lowered == "no":
        return NormalizedField(False, Availability.REPORTED, text)
    if lowered.startswith("yes") or any(
        phrase in lowered
        for phrase in ("extension possible", "possible extension", "likely extension")
    ):
        return NormalizedField(True, Availability.DERIVED, text)
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
            ("in person", "onsite"),
            ("hybrid", "hybrid"),
            ("remote", "remote"),
            ("flexible", "flexible"),
        )
        if keyword in lowered
    }
    if len(matches) == 1:
        return NormalizedField(matches.pop(), Availability.REPORTED, text)
    return NormalizedField(None, Availability.AMBIGUOUS, text)


def _normalize_compensation(
    text: str | None,
    location_text: str | None,
) -> NormalizedCompensation:
    if not text:
        return NormalizedCompensation(
            None, None, None, None, None, Availability.NOT_REPORTED, text
        )
    lowered = text.casefold()
    currency: str | None = None
    currency_derived = False
    if re.search(r"\busd\b", text, re.IGNORECASE):
        currency = "USD"
    elif "$" in text:
        location = (location_text or "").casefold()
        if "usa" in location or "united states" in location:
            currency = "USD"
            currency_derived = True
    elif re.search(r"\beur\b|euros?|€", text, re.IGNORECASE):
        currency = "EUR"
    elif re.search(r"\bchf\b|swiss francs?", text, re.IGNORECASE):
        currency = "CHF"
    elif re.search(r"\bjpy\b|yen", text, re.IGNORECASE):
        currency = "JPY"
    elif re.search(r"\bgbp\b|£", text, re.IGNORECASE):
        currency = "GBP"

    period: str | None = None
    for pattern, value in (
        (r"annual|per annum|per year|/\s*year|/\s*yr|yearly", "annual"),
        (r"per month|monthly|/\s*month", "monthly"),
        (r"per week|weekly|/\s*week", "weekly"),
        (r"per day|daily|/\s*day", "daily"),
        (r"per hour|hourly|/\s*hour", "hourly"),
    ):
        if re.search(pattern, lowered):
            period = value
            break
    if currency is None or period is None:
        return NormalizedCompensation(None, None, None, None, None, Availability.AMBIGUOUS, text)
    numbers = re.findall(r"(?<![A-Za-z])(\d[\d, ]*(?:\.\d+)?)([kK]?)", text)
    amounts: list[float] = []
    for number, suffix in numbers:
        cleaned = number.replace(",", "").replace(" ", "")
        try:
            value = float(cleaned)
        except ValueError:
            continue
        if suffix:
            value *= 1_000
        if value >= 100:
            amounts.append(value)
    if not amounts:
        return NormalizedCompensation(None, None, None, None, None, Availability.AMBIGUOUS, text)
    has_range_wording = bool(re.search(r"\bto\b|[-–]", lowered))
    if has_range_wording and len(amounts) < 2:
        return NormalizedCompensation(
            None, None, None, None, None, Availability.AMBIGUOUS, text
        )
    minimum = amounts[0]
    maximum = amounts[1] if len(amounts) > 1 else minimum
    if maximum < minimum:
        minimum, maximum = maximum, minimum
    gross_net = "gross" if "gross" in lowered else "net" if "net" in lowered else "not_stated"
    return NormalizedCompensation(
        amount_min=minimum,
        amount_max=maximum,
        currency=currency,
        pay_period=period,
        gross_net=gross_net,
        availability=Availability.DERIVED if currency_derived else Availability.REPORTED,
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
        canonical_url=source.canonical_url,
        official_title=source.official_title,
        normalized_title=normalized_title,
        source_category_text=source.source_category_text,
        institution_text=source.institution_text,
        department_text=source.department_text,
        location_text=source.location_text,
        positions_available=_normalize_positions(source.positions_text),
        extension_possible=_normalize_extension(source.extension_text),
        reference_code_text=source.reference_code_text,
        official_announcement_url=source.official_announcement_url,
        job_family=_classify_job_family(normalized_title, source.source_category_text),
        posted_at=_normalize_date(source.posted_at_text),
        application_deadline_at=_normalize_date(source.deadline_text),
        employment_terms=NormalizedEmploymentTerms(
            contract_type=_normalize_contract_type(source.contract_text),
            contract_duration_months=_normalize_contract_duration(source.contract_text),
            employment_fraction=_normalize_fraction(source.employment_fraction_text),
            start_date=_extract_start_date(source.start_date_text),
            work_mode=_normalize_work_mode(source.work_mode_text),
        ),
        compensation=_normalize_compensation(source.salary_text, source.location_text),
        languages=_normalize_languages(source.language_texts),
    )
