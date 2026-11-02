"""Tests for the SQLite data model."""

import sqlite3
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

import pytest

from astrocareer.database import (
    DEMO_POSTING_ID,
    DEMO_ROUND_ID,
    calculate_selection_metrics,
    connect_database,
    get_schema_version,
    initialize_database,
    persist_collection_batch,
    persist_normalization_candidate,
    seed_demo_data,
)
from astrocareer.collectors import CollectionBatch, CollectionStatus, RawSnapshot, SourcePosting
from astrocareer.normalization import normalize_source_posting


def test_initialize_database_creates_expected_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"

    assert initialize_database(database_path) == 7

    with connect_database(database_path) as connection:
        assert get_schema_version(connection) == 7
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {
        "postings",
        "observations",
        "evidence",
        "eligibility_requirements",
        "skill_requirements",
        "recruitment_metrics",
        "international_eligibility",
        "international_access_assessments",
        "collection_runs",
        "snapshots",
        "source_record_observations",
        "collection_issues",
        "employment_terms",
        "compensations",
        "posting_languages",
        "normalization_candidates",
        "source_access_policies",
    } <= tables


def test_initialize_database_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)

    assert initialize_database(database_path) == 7


def test_initialize_database_migrates_schema_v1(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    migration = files("astrocareer.database.migrations").joinpath("0001_initial.sql")
    with sqlite3.connect(database_path) as connection:
        connection.executescript(migration.read_text(encoding="utf-8"))

    assert initialize_database(database_path) == 7

    with connect_database(database_path) as connection:
        assert get_schema_version(connection) == 7
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='snapshots'"
        ).fetchone()


def test_initialize_database_migrates_schema_v2(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    migration_v1 = files("astrocareer.database.migrations").joinpath("0001_initial.sql")
    migration_v2 = files("astrocareer.database.migrations").joinpath(
        "0002_collection_runs.sql"
    )
    with sqlite3.connect(database_path) as connection:
        connection.executescript(migration_v1.read_text(encoding="utf-8"))
        connection.executescript(migration_v2.read_text(encoding="utf-8"))

    assert initialize_database(database_path) == 7

    with connect_database(database_path) as connection:
        assert get_schema_version(connection) == 7
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='employment_terms'"
        ).fetchone()


def test_initialize_database_migrates_schema_v3(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    migration_names = (
        "0001_initial.sql",
        "0002_collection_runs.sql",
        "0003_employment_terms.sql",
    )
    with sqlite3.connect(database_path) as connection:
        for name in migration_names:
            migration = files("astrocareer.database.migrations").joinpath(name)
            connection.executescript(migration.read_text(encoding="utf-8"))

    assert initialize_database(database_path) == 7

    with connect_database(database_path) as connection:
        assert get_schema_version(connection) == 7
        assert connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='normalization_candidates'
            """
        ).fetchone()


def test_initialize_database_migrates_schema_v4(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    migration_names = (
        "0001_initial.sql",
        "0002_collection_runs.sql",
        "0003_employment_terms.sql",
        "0004_normalization_candidates.sql",
    )
    with sqlite3.connect(database_path) as connection:
        for name in migration_names:
            migration = files("astrocareer.database.migrations").joinpath(name)
            connection.executescript(migration.read_text(encoding="utf-8"))

    assert initialize_database(database_path) == 7

    with connect_database(database_path) as connection:
        assert get_schema_version(connection) == 7
        assert connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='source_access_policies'
            """
        ).fetchone()


def test_compensation_requires_amount_currency_and_period_when_reported(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO postings (
                posting_id, official_title, positions_availability,
                first_seen_at, last_seen_at
            ) VALUES (
                'posting-compensation', 'Example Position', 'not_reported',
                '2026-11-01T12:00:00Z', '2026-11-01T12:00:00Z'
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO compensations (
                    compensation_id, posting_id, availability
                ) VALUES (
                    'compensation-invalid', 'posting-compensation', 'reported'
                )
                """
            )


def test_recruitment_metric_requires_value_when_reported(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO institutions (institution_id, name)
            VALUES ('institution-1', 'Example Observatory')
            """
        )
        connection.execute(
            """
            INSERT INTO postings (
                posting_id, official_title, institution_id, positions_availability,
                first_seen_at, last_seen_at
            ) VALUES (
                'posting-1', 'Example Postdoctoral Position', 'institution-1',
                'not_reported', '2026-11-01T12:00:00Z', '2026-11-01T12:00:00Z'
            )
            """
        )
        connection.execute(
            "INSERT INTO recruitment_rounds (round_id, posting_id) VALUES ('round-1', 'posting-1')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO recruitment_metrics (
                    metric_id, round_id, metric_type, value, availability
                ) VALUES (
                    'metric-1', 'round-1', 'applications_submitted', NULL, 'reported'
                )
                """
            )


@pytest.mark.parametrize(
    ("applications", "hires", "rate", "per_hire"),
    [
        (100, 5, 0.05, 20.0),
        (10, 0, 0.0, None),
        (0, 0, None, None),
    ],
)
def test_selection_metrics(
    applications: int,
    hires: int,
    rate: float | None,
    per_hire: float | None,
) -> None:
    result = calculate_selection_metrics(applications, hires)

    assert result.selection_rate == rate
    assert result.applicants_per_hire == per_hire


def test_selection_metrics_reject_impossible_counts() -> None:
    with pytest.raises(ValueError):
        calculate_selection_metrics(2, 3)


def test_seed_demo_data_builds_complete_evidence_chain(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        assert seed_demo_data(connection) is True
        assert seed_demo_data(connection) is False

        posting = connection.execute(
            "SELECT official_title, status FROM postings WHERE posting_id = ?",
            (DEMO_POSTING_ID,),
        ).fetchone()
        metrics = dict(
            connection.execute(
                """
                SELECT metric_type, value
                FROM recruitment_metrics
                WHERE round_id = ?
                """,
                (DEMO_ROUND_ID,),
            ).fetchall()
        )
        evidence_roles = {
            row[0]
            for row in connection.execute(
                "SELECT evidence_role FROM assessment_evidence"
            )
        }
        employment = connection.execute(
            """
            SELECT contract_type, contract_duration_months, employment_fraction, work_mode
            FROM employment_terms
            WHERE posting_id = ?
            """,
            (DEMO_POSTING_ID,),
        ).fetchone()
        compensation = connection.execute(
            """
            SELECT amount_min, amount_max, currency, pay_period
            FROM compensations
            WHERE posting_id = ?
            """,
            (DEMO_POSTING_ID,),
        ).fetchone()

    assert posting["status"] == "filled"
    assert "Research Software Engineer" in posting["official_title"]
    assert metrics["applications_submitted"] == 37
    assert metrics["hires_final"] == 1
    assert evidence_roles == {"job", "policy"}
    assert employment["contract_type"] == "fixed_term"
    assert employment["contract_duration_months"] == 36
    assert employment["employment_fraction"] == 1.0
    assert employment["work_mode"] == "hybrid"
    assert compensation["amount_min"] == 70000
    assert compensation["amount_max"] == 85000
    assert compensation["currency"] == "USD"
    assert compensation["pay_period"] == "annual"


def test_persist_collection_batch_links_multiple_records_to_one_snapshot(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)
    snapshot = RawSnapshot.create(
        source_id="test-source",
        url="https://jobs.example.test/",
        observed_at=datetime(2026, 11, 1, 12, tzinfo=timezone.utc),
        status_code=200,
        content_type="text/html",
        content=b"<html>two records</html>",
    )
    records = tuple(
        SourcePosting(
            source_id="test-source",
            source_record_id=f"record-{index}",
            snapshot_url=snapshot.url,
            snapshot_sha256=snapshot.content_sha256,
            canonical_url=f"https://jobs.example.test/{index}",
            official_title=f"Position {index}",
        )
        for index in (1, 2)
    )
    batch = CollectionBatch(
        source_id="test-source",
        status=CollectionStatus.SUCCESS,
        snapshots=(snapshot,),
        records=records,
        issues=(),
    )

    with connect_database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO sources (
                source_id, name, homepage_url, source_type,
                authority_level, collection_method
            ) VALUES (
                'test-source', 'Test Source', 'https://jobs.example.test/',
                'employer', 'a', 'html'
            )
            """
        )
        connection.commit()
        run_id = persist_collection_batch(
            connection,
            batch,
            collector_version="test-1",
        )
        snapshot_count = connection.execute(
            "SELECT count(*) FROM snapshots WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        record_count = connection.execute(
            "SELECT count(*) FROM source_record_observations WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]

    assert snapshot_count == 1
    assert record_count == 2


def test_persist_normalization_candidate_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    initialize_database(database_path)
    snapshot = RawSnapshot.create(
        source_id="normalization-source",
        url="https://normalization.example.test/jobs/",
        observed_at=datetime(2026, 11, 1, 12, tzinfo=timezone.utc),
        status_code=200,
        content_type="text/html",
        content=b"<html>record</html>",
    )
    record = SourcePosting(
        source_id="normalization-source",
        source_record_id="record-1",
        snapshot_url=snapshot.url,
        snapshot_sha256=snapshot.content_sha256,
        canonical_url="https://normalization.example.test/jobs/1",
        official_title="Research Software Engineer",
        contract_text="Fixed-term contract for 24 months.",
    )
    batch = CollectionBatch(
        source_id="normalization-source",
        status=CollectionStatus.SUCCESS,
        snapshots=(snapshot,),
        records=(record,),
        issues=(),
    )

    with connect_database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO sources (
                source_id, name, homepage_url, source_type,
                authority_level, collection_method
            ) VALUES (
                'normalization-source', 'Normalization Source',
                'https://normalization.example.test/', 'employer', 'a', 'html'
            )
            """
        )
        connection.commit()
        run_id = persist_collection_batch(connection, batch, collector_version="test-1")
        observation_id = connection.execute(
            """
            SELECT source_record_observation_id
            FROM source_record_observations
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()[0]
        candidate = normalize_source_posting(record)
        first_id = persist_normalization_candidate(
            connection,
            source_record_observation_id=observation_id,
            candidate=candidate,
            normalizer_version="test-1",
        )
        second_id = persist_normalization_candidate(
            connection,
            source_record_observation_id=observation_id,
            candidate=candidate,
            normalizer_version="test-1",
        )

    assert first_id == second_id
