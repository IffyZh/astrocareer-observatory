"""Tests for the scheduled collection summary."""

import runpy
from pathlib import Path

from astrocareer.collectors.demo import DemoCollector
from astrocareer.collectors.fixture import FixtureTransport
from astrocareer.database import connect_database, initialize_database
from astrocareer.runner import run_collection
from astrocareer.sources import load_source_registry, sync_source_registry


def test_collection_summary_reports_persisted_aggregates(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    project_root = Path(__file__).parents[1]
    database_path = tmp_path / "astrocareer.sqlite3"
    registry = load_source_registry(project_root / "data" / "sources.toml")
    source = registry["demo-html-source"]
    initialize_database(database_path)
    with connect_database(database_path) as connection:
        sync_source_registry(connection, registry)
        run_collection(
            connection,
            source=source,
            collector=DemoCollector(),
            transport=FixtureTransport(
                project_root / "tests" / "fixtures" / "demo_source" / "normal.html"
            ),
            collector_version="demo-1",
            normalizer_version="rules-2",
            allow_disabled=True,
            enforce_interval=False,
        )
        connection.execute(
            "UPDATE collection_runs SET source_id = 'planetary-research-jobs-feed'"
        )
        connection.execute(
            """
            UPDATE source_record_observations
            SET source_id = 'planetary-research-jobs-feed'
            """
        )

    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("STATE_RESTORED", "true")
    runpy.run_path(
        str(project_root / "scripts" / "write_collection_summary.py"),
        run_name="__main__",
    )

    output = capsys.readouterr().out
    assert "Previous state restored: `true`" in output
    assert "Latest feed records: `2`" in output
    assert "Distinct source record IDs: `2`" in output
    assert "did not follow any official-announcement links" in output
