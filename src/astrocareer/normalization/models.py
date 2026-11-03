"""Immutable normalized values awaiting review and database acceptance."""

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Generic, TypeVar

T = TypeVar("T")


class Availability(StrEnum):
    REPORTED = "reported"
    DERIVED = "derived"
    NOT_REPORTED = "not_reported"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class NormalizedField(Generic[T]):
    value: T | None
    availability: Availability
    official_text: str | None = None

    def __post_init__(self) -> None:
        has_value = self.value is not None
        expects_value = self.availability in {Availability.REPORTED, Availability.DERIVED}
        if has_value != expects_value:
            raise ValueError("Normalized value and availability are inconsistent")


@dataclass(frozen=True)
class NormalizedDate:
    value: str | None
    precision: str | None
    availability: Availability
    official_text: str | None = None

    def __post_init__(self) -> None:
        has_value = self.value is not None
        expects_value = self.availability in {Availability.REPORTED, Availability.DERIVED}
        if has_value != expects_value:
            raise ValueError("Normalized date and availability are inconsistent")
        if has_value and self.precision not in {"date", "datetime", "month", "year"}:
            raise ValueError("A normalized date requires a supported precision")
        if not has_value and self.precision is not None:
            raise ValueError("A missing normalized date cannot have precision")


@dataclass(frozen=True)
class NormalizedEmploymentTerms:
    contract_type: NormalizedField[str]
    contract_duration_months: NormalizedField[int]
    employment_fraction: NormalizedField[float]
    start_date: NormalizedDate
    work_mode: NormalizedField[str]


@dataclass(frozen=True)
class NormalizedCompensation:
    amount_min: float | None
    amount_max: float | None
    currency: str | None
    pay_period: str | None
    gross_net: str | None
    availability: Availability
    official_text: str | None

    def __post_init__(self) -> None:
        has_value = self.amount_min is not None or self.amount_max is not None
        expects_value = self.availability in {Availability.REPORTED, Availability.DERIVED}
        if has_value != expects_value:
            raise ValueError("Compensation value and availability are inconsistent")
        if has_value and (self.currency is None or self.pay_period is None):
            raise ValueError("Normalized compensation requires currency and pay period")


@dataclass(frozen=True)
class NormalizedLanguage:
    language_code: str
    language_name: str
    requirement_level: str
    official_text: str


@dataclass(frozen=True)
class NormalizedPostingCandidate:
    source_id: str
    source_record_id: str
    snapshot_sha256: str
    canonical_url: str
    official_title: str
    normalized_title: str
    source_category_text: str | None
    institution_text: str | None
    department_text: str | None
    location_text: str | None
    positions_available: NormalizedField[int]
    extension_possible: NormalizedField[bool]
    reference_code_text: str | None
    official_announcement_url: str | None
    job_family: NormalizedField[str]
    posted_at: NormalizedDate
    application_deadline_at: NormalizedDate
    employment_terms: NormalizedEmploymentTerms
    compensation: NormalizedCompensation
    languages: tuple[NormalizedLanguage, ...]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready representation with string-valued enums."""
        return asdict(self)
