"""Stable contracts shared by all source collectors."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol, runtime_checkable


class CollectionStatus(StrEnum):
    """Outcome of one source collection run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    NOT_MODIFIED = "not_modified"
    FAILED = "failed"


class IssueSeverity(StrEnum):
    """Severity of a structured collection issue."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Checkpoint:
    """Opaque, versioned state returned by a previous collection run."""

    value: str
    version: int = 1


@dataclass(frozen=True)
class RequestSpec:
    """A request description interpreted by the shared transport layer."""

    source_id: str
    url: str
    purpose: str
    method: str = "GET"
    headers: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.method != "GET":
            raise ValueError("Collectors may only issue GET requests in schema v1")
        if not self.source_id or not self.url or not self.purpose:
            raise ValueError("source_id, url, and purpose are required")


@dataclass(frozen=True)
class RawSnapshot:
    """Immutable bytes and response metadata observed by a transport."""

    source_id: str
    url: str
    observed_at: datetime
    status_code: int
    content_type: str | None
    content: bytes
    content_sha256: str
    etag: str | None = None
    last_modified: str | None = None

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        expected_hash = hashlib.sha256(self.content).hexdigest()
        if self.content_sha256 != expected_hash:
            raise ValueError("content_sha256 does not match snapshot content")

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        url: str,
        status_code: int,
        content_type: str | None,
        content: bytes,
        observed_at: datetime | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> "RawSnapshot":
        """Create a snapshot while calculating its content hash consistently."""
        timestamp = observed_at or datetime.now(timezone.utc)
        return cls(
            source_id=source_id,
            url=url,
            observed_at=timestamp,
            status_code=status_code,
            content_type=content_type,
            content=content,
            content_sha256=hashlib.sha256(content).hexdigest(),
            etag=etag,
            last_modified=last_modified,
        )


@dataclass(frozen=True)
class SourcePosting:
    """A source-faithful record produced before normalization and deduplication."""

    source_id: str
    source_record_id: str
    snapshot_url: str
    snapshot_sha256: str
    canonical_url: str
    official_title: str
    source_category_text: str | None = None
    institution_text: str | None = None
    department_text: str | None = None
    location_text: str | None = None
    posted_at_text: str | None = None
    deadline_text: str | None = None
    contract_text: str | None = None
    salary_text: str | None = None
    employment_fraction_text: str | None = None
    start_date_text: str | None = None
    work_mode_text: str | None = None
    language_texts: tuple[str, ...] = field(default_factory=tuple)
    requirement_texts: tuple[str, ...] = field(default_factory=tuple)
    skill_texts: tuple[str, ...] = field(default_factory=tuple)
    international_eligibility_text: str | None = None
    positions_text: str | None = None
    extension_text: str | None = None
    reference_code_text: str | None = None
    official_announcement_url: str | None = None
    raw_fields: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.source_id or not self.source_record_id:
            raise ValueError("source_id and source_record_id are required")
        if not self.snapshot_url or not self.canonical_url or not self.official_title:
            raise ValueError("snapshot_url, canonical_url, and official_title are required")
        if len(self.snapshot_sha256) != 64:
            raise ValueError("snapshot_sha256 must be a SHA-256 hex digest")


@dataclass(frozen=True)
class ParseIssue:
    """A machine-readable warning or error that must survive collection."""

    severity: IssueSeverity
    code: str
    message: str
    source_record_id: str | None = None
    locator: str | None = None


@dataclass(frozen=True)
class CollectionBatch:
    """Complete output of one source collection run."""

    source_id: str
    status: CollectionStatus
    snapshots: tuple[RawSnapshot, ...]
    records: tuple[SourcePosting, ...]
    issues: tuple[ParseIssue, ...]
    next_checkpoint: Checkpoint | None = None

    def __post_init__(self) -> None:
        if any(snapshot.source_id != self.source_id for snapshot in self.snapshots):
            raise ValueError("All snapshots must belong to the batch source")
        if any(record.source_id != self.source_id for record in self.records):
            raise ValueError("All records must belong to the batch source")
        if self.status is CollectionStatus.FAILED and self.records:
            raise ValueError("A failed batch cannot expose records for persistence")
        if self.status is CollectionStatus.SUCCESS and any(
            issue.severity is IssueSeverity.ERROR for issue in self.issues
        ):
            raise ValueError("A successful batch cannot contain errors")


@runtime_checkable
class Transport(Protocol):
    """Network boundary shared by collectors and replaced by fakes in tests."""

    def fetch(self, request: RequestSpec) -> RawSnapshot:
        """Execute one approved request and return an immutable snapshot."""
        ...


@runtime_checkable
class Collector(Protocol):
    """A source adapter that never writes directly to the database."""

    source_id: str

    def collect(
        self,
        transport: Transport,
        checkpoint: Checkpoint | None = None,
    ) -> CollectionBatch:
        """Collect one batch from the source through the shared transport."""
        ...
