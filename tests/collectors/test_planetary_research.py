"""Parser tests for the Planetary Research Jobs Atom collector."""

from datetime import datetime, timezone
from pathlib import Path

from astrocareer.collectors import CollectionStatus, Collector, RawSnapshot, RequestSpec
from astrocareer.collectors.planetary_research import PlanetaryResearchFeedCollector

FIXTURES = Path(__file__).parents[1] / "fixtures" / "planetary_research_feed"


class MemoryTransport:
    def __init__(
        self,
        fixture_name: str,
        *,
        status_code: int = 200,
        content_type: str = "application/atom+xml; charset=utf-8",
    ) -> None:
        self.fixture_name = fixture_name
        self.status_code = status_code
        self.content_type = content_type
        self.requests: list[RequestSpec] = []

    def fetch(self, request: RequestSpec) -> RawSnapshot:
        self.requests.append(request)
        content = b"" if self.status_code == 304 else (FIXTURES / self.fixture_name).read_bytes()
        return RawSnapshot.create(
            source_id=request.source_id,
            url=request.url,
            observed_at=datetime(2026, 11, 1, 12, tzinfo=timezone.utc),
            status_code=self.status_code,
            content_type=self.content_type,
            content=content,
        )


def test_collector_satisfies_runtime_contract() -> None:
    assert isinstance(PlanetaryResearchFeedCollector(), Collector)


def test_normal_feed_produces_minimal_source_records() -> None:
    transport = MemoryTransport("normal.xml")

    batch = PlanetaryResearchFeedCollector().collect(transport)

    assert batch.status is CollectionStatus.SUCCESS
    assert len(batch.records) == 2
    assert not batch.issues
    assert len(transport.requests) == 1
    assert transport.requests[0].url == "https://jobs.planetary-research.org/feed"
    first = batch.records[0]
    assert first.source_record_id == "demo-1001"
    assert first.official_title == "Planetary Data Research Software Engineer"
    assert first.source_category_text == "Scientific and technical staff"
    assert first.institution_text == "Example Planetary Institute"
    assert first.department_text == "Data Systems"
    assert first.location_text == "Example City, Exampleland"
    assert first.posted_at_text == "2026-10-30"
    assert first.deadline_text == "2026-12-15"
    assert first.contract_text == "36 months"
    assert first.salary_text == "EUR 70,000 per year"
    assert first.start_date_text == "2027-03-01"
    assert first.work_mode_text == "Hybrid"
    assert first.positions_text == "1"
    assert first.reference_code_text == "RSE-1001"
    assert first.official_announcement_url == "https://careers.example.test/rse-1001"
    assert dict(first.raw_fields) == {
        "source_category": "Scientific and technical staff",
        "department": "Data Systems",
        "number_of_positions": "1",
        "reference_code": "RSE-1001",
        "official_announcement_url": "https://careers.example.test/rse-1001",
    }
    serialized = repr(first)
    assert "private@example.test" not in serialized
    assert "0000-0000-0000-0000" not in serialized
    assert "Copyrighted description" not in serialized
    assert "Requires Python" not in serialized


def test_valid_empty_feed_is_success() -> None:
    batch = PlanetaryResearchFeedCollector().collect(MemoryTransport("empty.xml"))

    assert batch.status is CollectionStatus.SUCCESS
    assert batch.records == ()
    assert batch.next_checkpoint is not None
    assert batch.next_checkpoint.value == "2026-11-01T12:00:00+00:00"


def test_changed_root_fails_closed() -> None:
    batch = PlanetaryResearchFeedCollector().collect(MemoryTransport("changed-layout.xml"))

    assert batch.status is CollectionStatus.FAILED
    assert batch.issues[0].code == "unexpected_feed_structure"


def test_malformed_xml_fails_closed() -> None:
    batch = PlanetaryResearchFeedCollector().collect(MemoryTransport("malformed.xml"))

    assert batch.status is CollectionStatus.FAILED
    assert batch.issues[0].code == "malformed_xml"


def test_valid_and_broken_entries_produce_partial_batch() -> None:
    batch = PlanetaryResearchFeedCollector().collect(MemoryTransport("partial.xml"))

    assert batch.status is CollectionStatus.PARTIAL
    assert [record.source_record_id for record in batch.records] == ["valid-1001"]
    assert batch.issues[0].code == "malformed_feed_entry"


def test_not_modified_response_produces_no_records() -> None:
    batch = PlanetaryResearchFeedCollector().collect(
        MemoryTransport("normal.xml", status_code=304)
    )

    assert batch.status is CollectionStatus.NOT_MODIFIED
    assert batch.records == ()


def test_unsafe_xml_declaration_is_rejected() -> None:
    snapshot = RawSnapshot.create(
        source_id=PlanetaryResearchFeedCollector.source_id,
        url=PlanetaryResearchFeedCollector.feed_url,
        observed_at=datetime(2026, 11, 1, 12, tzinfo=timezone.utc),
        status_code=200,
        content_type="application/atom+xml",
        content=b'<?xml version="1.0"?><!DOCTYPE feed [<!ENTITY x "unsafe">]><feed/>',
    )

    batch = PlanetaryResearchFeedCollector().parse(snapshot)

    assert batch.status is CollectionStatus.FAILED
    assert batch.issues[0].code == "unsafe_xml_declaration"


def test_entry_outside_reviewed_host_is_rejected() -> None:
    content = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <id>https://jobs.planetary-research.org/feed</id>
      <entry>
        <id>https://unreviewed.example/job-1</id>
        <title>Unsafe link</title>
        <link href="https://unreviewed.example/job-1"/>
      </entry>
    </feed>"""
    snapshot = RawSnapshot.create(
        source_id=PlanetaryResearchFeedCollector.source_id,
        url=PlanetaryResearchFeedCollector.feed_url,
        observed_at=datetime(2026, 11, 1, 12, tzinfo=timezone.utc),
        status_code=200,
        content_type="application/atom+xml",
        content=content,
    )

    batch = PlanetaryResearchFeedCollector().parse(snapshot)

    assert batch.status is CollectionStatus.FAILED
    assert "reviewed source host" in batch.issues[0].message
