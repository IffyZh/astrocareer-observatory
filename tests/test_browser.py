"""Tests for the local read-only database browser."""

from pathlib import Path

from astrocareer.browser import load_browser_records
from astrocareer.collectors.demo import DemoCollector
from astrocareer.collectors.fixture import FixtureTransport
from astrocareer.collectors.planetary_research import PlanetaryResearchFeedCollector
from astrocareer.database import connect_database, initialize_database
from astrocareer.runner import run_collection
from astrocareer.sources import load_source_registry, sync_source_registry


def _database(tmp_path: Path) -> Path:
    project_root = Path(__file__).parents[1]
    database_path = tmp_path / "astrocareer.sqlite3"
    registry = load_source_registry(project_root / "data" / "sources.toml")
    source = registry["planetary-research-jobs-feed"]
    initialize_database(database_path)
    with connect_database(database_path) as connection:
        sync_source_registry(connection, registry)
        run_collection(
            connection,
            source=source,
            collector=PlanetaryResearchFeedCollector(),
            transport=FixtureTransport(
                project_root
                / "tests"
                / "fixtures"
                / "planetary_research_feed"
                / "normal.xml",
                content_type="application/atom+xml; charset=utf-8",
            ),
            collector_version="planetary-research-feed-2",
            normalizer_version="rules-2",
            enforce_interval=False,
        )
    return database_path


def test_browser_returns_latest_structured_records(tmp_path: Path) -> None:
    records = load_browser_records(_database(tmp_path))

    assert len(records) == 2
    first = next(record for record in records if record["source_record_id"] == "demo-1001")
    assert first["title"] == "Planetary Data Research Software Engineer"
    assert first["institution"] == "Example Planetary Institute"
    assert first["department"] == "Data Systems"
    assert first["positions"] == 1
    assert first["official_announcement_url"] == "https://careers.example.test/rse-1001"


def test_browser_collapses_repeated_observations(tmp_path: Path) -> None:
    database_path = _database(tmp_path)
    project_root = Path(__file__).parents[1]
    registry = load_source_registry(project_root / "data" / "sources.toml")
    source = registry["planetary-research-jobs-feed"]
    with connect_database(database_path) as connection:
        run_collection(
            connection,
            source=source,
            collector=PlanetaryResearchFeedCollector(),
            transport=FixtureTransport(
                project_root
                / "tests"
                / "fixtures"
                / "planetary_research_feed"
                / "normal.xml",
                content_type="application/atom+xml; charset=utf-8",
            ),
            collector_version="planetary-research-feed-2",
            normalizer_version="rules-2",
            enforce_interval=False,
        )

    records = load_browser_records(database_path)
    assert len(records) == 2


def test_browser_excludes_disabled_fixture_sources(tmp_path: Path) -> None:
    database_path = _database(tmp_path)
    project_root = Path(__file__).parents[1]
    registry = load_source_registry(project_root / "data" / "sources.toml")
    demo_source = registry["demo-html-source"]
    with connect_database(database_path) as connection:
        run_collection(
            connection,
            source=demo_source,
            collector=DemoCollector(),
            transport=FixtureTransport(
                project_root / "tests" / "fixtures" / "demo_source" / "normal.html"
            ),
            collector_version="demo-1",
            normalizer_version="rules-2",
            allow_disabled=True,
            enforce_interval=False,
        )

    records = load_browser_records(database_path)
    assert len(records) == 2
    assert {record["source_id"] for record in records} == {
        "planetary-research-jobs-feed"
    }


def test_browser_requires_an_existing_database(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sqlite3"

    try:
        load_browser_records(missing)
    except FileNotFoundError as error:
        assert str(missing) in str(error)
    else:
        raise AssertionError("Expected a missing database to fail")
