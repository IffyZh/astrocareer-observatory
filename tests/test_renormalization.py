"""Tests for offline candidate rebuilding from saved source observations."""

import hashlib
import json
from pathlib import Path

from astrocareer.collectors.fixture import FixtureTransport
from astrocareer.collectors.planetary_research import PlanetaryResearchFeedCollector
from astrocareer.database import (
    connect_database,
    initialize_database,
    renormalize_source_observations,
)
from astrocareer.runner import run_collection
from astrocareer.sources import load_source_registry, sync_source_registry


def test_renormalize_legacy_observations_is_idempotent(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    database_path = tmp_path / "astrocareer.sqlite3"
    registry = load_source_registry(project_root / "data" / "sources.toml")
    source = registry["planetary-research-jobs-feed"]
    fixture = (
        project_root
        / "tests"
        / "fixtures"
        / "planetary_research_feed"
        / "normal.xml"
    )
    initialize_database(database_path)
    with connect_database(database_path) as connection:
        sync_source_registry(connection, registry)
        run_collection(
            connection,
            source=source,
            collector=PlanetaryResearchFeedCollector(),
            transport=FixtureTransport(
                fixture,
                content_type="application/atom+xml; charset=utf-8",
            ),
            collector_version="planetary-research-feed-1",
            normalizer_version="rules-1",
            enforce_interval=False,
        )
        row = connection.execute(
            """
            SELECT source_record_observation_id, record_json
            FROM source_record_observations
            WHERE source_record_id = 'demo-1001'
            """
        ).fetchone()
        legacy = json.loads(row["record_json"])
        for name in (
            "source_category_text",
            "department_text",
            "positions_text",
            "extension_text",
            "reference_code_text",
            "official_announcement_url",
        ):
            legacy.pop(name)
        document = json.dumps(
            legacy,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        connection.execute(
            """
            UPDATE source_record_observations
            SET record_json = ?, record_sha256 = ?
            WHERE source_record_observation_id = ?
            """,
            (
                document,
                hashlib.sha256(document.encode("utf-8")).hexdigest(),
                row["source_record_observation_id"],
            ),
        )
        first = renormalize_source_observations(
            connection,
            source_id=source.source_id,
            normalizer_version="rules-2",
        )
        second = renormalize_source_observations(
            connection,
            source_id=source.source_id,
            normalizer_version="rules-2",
        )
        candidate_json = connection.execute(
            """
            SELECT candidate_json
            FROM normalization_candidates nc
            JOIN source_record_observations sro
              ON sro.source_record_observation_id = nc.source_record_observation_id
            WHERE sro.source_record_id = 'demo-1001'
              AND nc.normalizer_version = 'rules-2'
            """
        ).fetchone()[0]
        statuses = connection.execute(
            """
            SELECT review_status, count(*)
            FROM normalization_candidates
            GROUP BY review_status
            ORDER BY review_status
            """
        ).fetchall()

    candidate = json.loads(candidate_json)
    assert first.observation_count == 2
    assert first.inserted_count == 2
    assert first.superseded_count == 2
    assert second.inserted_count == 0
    assert second.reused_count == 2
    assert candidate["source_category_text"] == "Scientific and technical staff"
    assert candidate["department_text"] == "Data Systems"
    assert candidate["positions_available"]["value"] == 1
    assert candidate["reference_code_text"] == "RSE-1001"
    assert [(row[0], row[1]) for row in statuses] == [
        ("pending", 2),
        ("superseded", 2),
    ]
