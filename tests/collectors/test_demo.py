"""Contract and parser tests for the fictional demo collector."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from astrocareer.collectors import (
    CollectionStatus,
    Collector,
    RawSnapshot,
    RequestSpec,
)
from astrocareer.collectors.demo import DemoCollector

FIXTURES = Path(__file__).parents[1] / "fixtures" / "demo_source"


class MemoryTransport:
    """A deterministic transport that cannot access the network."""

    def __init__(self, fixture_name: str, *, status_code: int = 200) -> None:
        self.fixture_name = fixture_name
        self.status_code = status_code
        self.requests: list[RequestSpec] = []

    def fetch(self, request: RequestSpec) -> RawSnapshot:
        self.requests.append(request)
        content = (FIXTURES / self.fixture_name).read_bytes()
        return RawSnapshot.create(
            source_id=request.source_id,
            url=request.url,
            observed_at=datetime(2026, 11, 1, 12, tzinfo=timezone.utc),
            status_code=self.status_code,
            content_type="text/html; charset=utf-8",
            content=content,
        )


def test_demo_collector_satisfies_runtime_contract() -> None:
    assert isinstance(DemoCollector(), Collector)


def test_normal_listing_produces_source_faithful_records() -> None:
    collector = DemoCollector()
    transport = MemoryTransport("normal.html")

    batch = collector.collect(transport)

    assert batch.status is CollectionStatus.SUCCESS
    assert not batch.issues
    assert len(batch.records) == 2
    assert len(batch.snapshots) == 1
    assert len(transport.requests) == 1
    first = batch.records[0]
    assert first.source_record_id == "DEMO-RSE-001"
    assert first.canonical_url.endswith("/jobs/DEMO-RSE-001")
    assert first.posted_at_text == "2026-01-15"
    assert first.deadline_text == "2026-03-01T23:59:00Z"
    assert first.contract_text == "Fixed-term contract for 36 months."
    assert first.salary_text == "USD 70000-85000 per year, gross."
    assert first.employment_fraction_text == "Full-time, 1.0 FTE."
    assert first.start_date_text == "Expected start date: 2026-07-01."
    assert first.work_mode_text == "Hybrid work."
    assert first.language_texts == (
        "Professional working proficiency in English is required.",
    )
    assert first.skill_texts == (
        "Python is required.",
        "Experience with SQL is preferred.",
        "HPC experience is desirable.",
    )
    assert "visa sponsorship" in (first.international_eligibility_text or "")


def test_explicit_empty_listing_is_a_successful_zero_result() -> None:
    batch = DemoCollector().collect(MemoryTransport("empty.html"))

    assert batch.status is CollectionStatus.SUCCESS
    assert batch.records == ()
    assert batch.issues == ()


def test_changed_layout_fails_instead_of_silently_returning_zero() -> None:
    batch = DemoCollector().collect(MemoryTransport("changed-layout.html"))

    assert batch.status is CollectionStatus.FAILED
    assert batch.records == ()
    assert batch.issues[0].code == "unexpected_page_structure"


def test_http_error_fails_without_exposing_records() -> None:
    batch = DemoCollector().collect(MemoryTransport("normal.html", status_code=503))

    assert batch.status is CollectionStatus.FAILED
    assert batch.records == ()
    assert batch.issues[0].code == "unexpected_http_status"


def test_one_malformed_record_produces_a_partial_batch() -> None:
    batch = DemoCollector().collect(MemoryTransport("partial.html"))

    assert batch.status is CollectionStatus.PARTIAL
    assert [record.source_record_id for record in batch.records] == ["VALID-001"]
    assert batch.issues[0].code == "missing_required_field"
    assert batch.issues[0].source_record_id == "BROKEN-002"


def test_snapshot_rejects_incorrect_hash() -> None:
    with pytest.raises(ValueError, match="content_sha256"):
        RawSnapshot(
            source_id="demo-html-source",
            url="https://example.test/",
            observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
            status_code=200,
            content_type="text/html",
            content=b"content",
            content_sha256="0" * 64,
        )
