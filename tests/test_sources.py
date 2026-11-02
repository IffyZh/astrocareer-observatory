"""Tests for the public source registry."""

from pathlib import Path

import pytest

from astrocareer.database import connect_database, initialize_database
from astrocareer.sources import load_source_registry, sync_source_registry


def test_repository_source_registry_is_valid_and_disabled() -> None:
    registry_path = Path(__file__).parents[1] / "data" / "sources.toml"

    registry = load_source_registry(registry_path)

    demo = registry["demo-html-source"]
    assert demo.enabled is False
    assert demo.allowed_hosts == ("careers.example-observatory.test",)
    assert demo.minimum_interval_seconds == 3600
    aas = registry["aas-job-register"]
    assert aas.enabled is False
    assert aas.access_status == "permission_required"
    planetary = registry["planetary-research-jobs-feed"]
    assert planetary.enabled is False
    assert planetary.access_status == "approved"
    assert planetary.collection_method == "feed"
    assert planetary.allowed_path_prefixes == ("/feed",)
    assert planetary.minimum_interval_seconds == 21600
    ror = registry["ror-data-dump"]
    assert ror.enabled is True
    assert ror.access_status == "approved"
    assert ror.collection_method == "import"


def test_registry_rejects_homepage_outside_allowed_hosts(tmp_path: Path) -> None:
    registry_path = tmp_path / "sources.toml"
    registry_path.write_text(
        """
schema_version = 1

[[sources]]
source_id = "unsafe"
name = "Unsafe"
organization = "Unsafe"
homepage_url = "https://outside.example/"
source_type = "other"
authority_level = "d"
collection_method = "html"
enabled = false
access_status = "pending_review"
robots_reviewed_at = "2026-11-01"
terms_reviewed_at = "2026-11-01"
allowed_hosts = ["allowed.example"]
allowed_path_prefixes = ["/"]
minimum_interval_seconds = 1
redistribution_notes = "test"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="allowed_hosts"):
        load_source_registry(registry_path)


def test_sync_source_registry_is_idempotent(tmp_path: Path) -> None:
    registry_path = Path(__file__).parents[1] / "data" / "sources.toml"
    database_path = tmp_path / "astrocareer.sqlite3"
    registry = load_source_registry(registry_path)
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        assert sync_source_registry(connection, registry) == 4
        assert sync_source_registry(connection, registry) == 4
        row = connection.execute(
            "SELECT enabled, collection_method FROM sources WHERE source_id = ?",
            ("demo-html-source",),
        ).fetchone()
        policy = connection.execute(
            """
            SELECT access_status, minimum_interval_seconds
            FROM source_access_policies
            WHERE source_id = ?
            """,
            ("demo-html-source",),
        ).fetchone()

    assert row["enabled"] == 0
    assert row["collection_method"] == "html"
    assert policy["access_status"] == "pending_review"
    assert policy["minimum_interval_seconds"] == 3600
