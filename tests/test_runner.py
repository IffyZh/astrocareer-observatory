"""Tests for collection orchestration and safety gates."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from astrocareer.collectors.demo import DemoCollector
from astrocareer.collectors.fixture import FixtureTransport
from astrocareer.database import connect_database, initialize_database
from astrocareer.runner import CollectionBlocked, run_collection
from astrocareer.sources import SourceDefinition, sync_source_registry

FIXTURES = Path(__file__).parent / "fixtures" / "demo_source"
NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


def _source(*, enabled: bool = True) -> SourceDefinition:
    return SourceDefinition(
        source_id="demo-html-source",
        name="Demo",
        organization="Example Observatory",
        homepage_url="https://careers.example-observatory.test/",
        source_type="employer",
        authority_level="a",
        collection_method="html",
        enabled=enabled,
        access_status="approved",
        robots_reviewed_at="2026-11-01",
        terms_reviewed_at="2026-11-01",
        allowed_hosts=("careers.example-observatory.test",),
        allowed_path_prefixes=("/jobs/",),
        minimum_interval_seconds=3600,
        redistribution_notes="Fictional fixture.",
    )


def _transport(name: str = "normal.html") -> FixtureTransport:
    return FixtureTransport(FIXTURES / name, observed_at=NOW)


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        report = run_collection(
            connection,
            source=_source(),
            collector=DemoCollector(),
            transport=_transport(),
            collector_version="demo-1",
            normalizer_version="rules-1",
            dry_run=True,
            enforce_interval=False,
        )
        run_count = connection.execute("SELECT count(*) FROM collection_runs").fetchone()[0]

    assert report.persisted is False
    assert report.record_count == 2
    assert report.candidate_count == 2
    assert run_count == 0


def test_persisted_run_is_atomic_and_creates_pending_candidates(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)
    source = _source()

    with connect_database(database_path) as connection:
        sync_source_registry(connection, {source.source_id: source})
        report = run_collection(
            connection,
            source=source,
            collector=DemoCollector(),
            transport=_transport(),
            collector_version="demo-1",
            normalizer_version="rules-1",
            enforce_interval=False,
        )
        snapshot_count = connection.execute("SELECT count(*) FROM snapshots").fetchone()[0]
        observation_count = connection.execute(
            "SELECT count(*) FROM source_record_observations"
        ).fetchone()[0]
        candidate_count = connection.execute(
            "SELECT count(*) FROM normalization_candidates WHERE review_status='pending'"
        ).fetchone()[0]

    assert report.persisted is True
    assert report.run_id is not None
    assert snapshot_count == 1
    assert observation_count == 2
    assert candidate_count == 2


def test_disabled_source_is_blocked_by_default(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        with pytest.raises(CollectionBlocked, match="disabled"):
            run_collection(
                connection,
                source=_source(enabled=False),
                collector=DemoCollector(),
                transport=_transport(),
                collector_version="demo-1",
                normalizer_version="rules-1",
                dry_run=True,
            )


def test_source_identity_mismatch_is_blocked(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        with pytest.raises(CollectionBlocked, match="does not match"):
            run_collection(
                connection,
                source=replace(_source(), source_id="different-source"),
                collector=DemoCollector(),
                transport=_transport(),
                collector_version="demo-1",
                normalizer_version="rules-1",
                dry_run=True,
            )


def test_minimum_interval_blocks_repeated_run(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)
    source = _source()

    with connect_database(database_path) as connection:
        sync_source_registry(connection, {source.source_id: source})
        run_collection(
            connection,
            source=source,
            collector=DemoCollector(),
            transport=_transport(),
            collector_version="demo-1",
            normalizer_version="rules-1",
            now=NOW,
        )
        with pytest.raises(CollectionBlocked, match="rate-limited"):
            run_collection(
                connection,
                source=source,
                collector=DemoCollector(),
                transport=_transport(),
                collector_version="demo-1",
                normalizer_version="rules-1",
                now=NOW + timedelta(minutes=1),
            )


def test_network_dry_run_records_access_and_blocks_repeat(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)
    source = _source()

    with connect_database(database_path) as connection:
        sync_source_registry(connection, {source.source_id: source})
        report = run_collection(
            connection,
            source=source,
            collector=DemoCollector(),
            transport=_transport(),
            collector_version="demo-1",
            normalizer_version="rules-1",
            dry_run=True,
            record_network_access=True,
            contact_url="https://example.test/astrocareer",
            now=NOW,
        )
        access = connection.execute(
            """
            SELECT mode, contact_url
            FROM source_access_attempts
            WHERE source_id = ?
            """,
            (source.source_id,),
        ).fetchone()
        with pytest.raises(CollectionBlocked, match="rate-limited"):
            run_collection(
                connection,
                source=source,
                collector=DemoCollector(),
                transport=_transport(),
                collector_version="demo-1",
                normalizer_version="rules-1",
                dry_run=True,
                record_network_access=True,
                contact_url="https://example.test/astrocareer",
                now=NOW + timedelta(minutes=1),
            )

    assert report.persisted is False
    assert access["mode"] == "dry_run"
    assert access["contact_url"] == "https://example.test/astrocareer"
