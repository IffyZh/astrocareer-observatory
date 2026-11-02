"""Tests for the reviewed ROR Schema 2.x institution import."""

from pathlib import Path

import pytest

from astrocareer.database import connect_database, initialize_database
from astrocareer.importers.ror import import_ror_dump
from astrocareer.sources import load_source_registry, sync_source_registry

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "ror"


def _database(tmp_path: Path):
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)
    connection = connect_database(database_path)
    registry = load_source_registry(PROJECT_ROOT / "data" / "sources.toml")
    sync_source_registry(connection, registry)
    return connection


def test_imports_ror_institutions_and_related_metadata(tmp_path: Path) -> None:
    with _database(tmp_path) as connection:
        report = import_ror_dump(
            connection,
            FIXTURES / "schema-v2.1.json",
            dataset_version="v-test-2026-11-01",
        )
        institution = connection.execute(
            """
            SELECT name, country_code, homepage_url, ror_id, status, established_year
            FROM institutions WHERE institution_id = ?
            """,
            ("https://ror.org/01abcde12",),
        ).fetchone()
        names = connection.execute(
            "SELECT name FROM institution_names WHERE institution_id = ? ORDER BY name",
            ("https://ror.org/01abcde12",),
        ).fetchall()
        domains = connection.execute(
            "SELECT domain, active FROM institution_domains WHERE institution_id = ?",
            ("https://ror.org/01abcde12",),
        ).fetchall()
        types = connection.execute(
            "SELECT organization_type FROM institution_types WHERE institution_id = ? ORDER BY 1",
            ("https://ror.org/01abcde12",),
        ).fetchall()
        location = connection.execute(
            """
            SELECT name, country_code, continent_code, latitude, longitude
            FROM institution_locations WHERE institution_id = ?
            """,
            ("https://ror.org/01abcde12",),
        ).fetchone()

    assert report.record_count == 2
    assert report.inserted_count == 2
    assert report.updated_count == 0
    assert report.reused_existing_run is False
    assert dict(institution) == {
        "name": "Example Observatory",
        "country_code": "EX",
        "homepage_url": "https://www.observatory.example/",
        "ror_id": "https://ror.org/01abcde12",
        "status": "active",
        "established_year": 1965,
    }
    assert [row[0] for row in names] == ["EO", "Example Observatory"]
    assert [(row[0], row[1]) for row in domains] == [("observatory.example", 1)]
    assert [row[0] for row in types] == ["education", "facility"]
    assert dict(location) == {
        "name": "Example City",
        "country_code": "EX",
        "continent_code": "EU",
        "latitude": 42.5,
        "longitude": -1.25,
    }


def test_same_snapshot_is_idempotent(tmp_path: Path) -> None:
    with _database(tmp_path) as connection:
        first = import_ror_dump(
            connection,
            FIXTURES / "schema-v2.1.json",
            dataset_version="v-test",
        )
        second = import_ror_dump(
            connection,
            FIXTURES / "schema-v2.1.json",
            dataset_version="ignored-because-content-is-identical",
        )
        run_count = connection.execute(
            "SELECT count(*) FROM institution_import_runs"
        ).fetchone()[0]

    assert second.import_run_id == first.import_run_id
    assert second.reused_existing_run is True
    assert run_count == 1


def test_new_snapshot_updates_records_and_retires_old_domain(tmp_path: Path) -> None:
    with _database(tmp_path) as connection:
        import_ror_dump(connection, FIXTURES / "schema-v2.1.json", dataset_version="v1")
        report = import_ror_dump(
            connection,
            FIXTURES / "schema-v2.1-updated.json",
            dataset_version="v2",
        )
        institution = connection.execute(
            "SELECT name, status FROM institutions WHERE ror_id = ?",
            ("https://ror.org/01abcde12",),
        ).fetchone()
        domains = connection.execute(
            """
            SELECT domain, active FROM institution_domains
            WHERE institution_id = ? ORDER BY domain
            """,
            ("https://ror.org/01abcde12",),
        ).fetchall()

    assert report.record_count == 1
    assert report.inserted_count == 0
    assert report.updated_count == 1
    assert tuple(institution) == ("Example Observatory and Archive", "inactive")
    assert [(row[0], row[1]) for row in domains] == [
        ("new-observatory.example", 1),
        ("observatory.example", 0),
    ]


def test_invalid_dump_rolls_back_all_records(tmp_path: Path) -> None:
    with _database(tmp_path) as connection:
        with pytest.raises(ValueError, match="Invalid ROR domain"):
            import_ror_dump(
                connection,
                FIXTURES / "invalid.json",
                dataset_version="invalid",
            )
        institution_count = connection.execute(
            "SELECT count(*) FROM institutions"
        ).fetchone()[0]
        run_count = connection.execute(
            "SELECT count(*) FROM institution_import_runs"
        ).fetchone()[0]

    assert institution_count == 0
    assert run_count == 0
