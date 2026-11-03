"""Network-free tests for GitHub Actions database synchronization."""

import hashlib
import io
import json
import zipfile
from pathlib import Path
from urllib.request import Request

import pytest

from astrocareer.collectors.fixture import FixtureTransport
from astrocareer.collectors.planetary_research import PlanetaryResearchFeedCollector
from astrocareer.database import connect_database, initialize_database
from astrocareer.database.github_sync import (
    GitHubArtifactSyncError,
    _SafeRedirect,
    sync_github_database,
)
from astrocareer.runner import run_collection
from astrocareer.sources import load_source_registry, sync_source_registry


class FakeResponse(io.BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.headers = {"Content-Length": str(len(content))}

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class FakeOpener:
    def __init__(self, metadata: bytes, archive: bytes) -> None:
        self.metadata = metadata
        self.archive = archive
        self.requests = []

    def __call__(self, request, timeout: int):  # noqa: ANN001
        self.requests.append((request, timeout))
        if request.full_url.endswith("/download"):
            return FakeResponse(self.archive)
        return FakeResponse(self.metadata)


def _artifact(tmp_path: Path) -> tuple[bytes, bytes]:
    project_root = Path(__file__).parents[1]
    database_path = tmp_path / "source.sqlite3"
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
    archive_file = io.BytesIO()
    with zipfile.ZipFile(archive_file, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(database_path, "astrocareer.sqlite3")
    archive = archive_file.getvalue()
    metadata = json.dumps(
        {
            "artifacts": [
                {
                    "id": 1234,
                    "name": "collector-state",
                    "expired": False,
                    "created_at": "2026-11-03T17:39:50Z",
                    "archive_download_url": "https://api.example.test/download",
                    "digest": f"sha256:{hashlib.sha256(archive).hexdigest()}",
                }
            ]
        }
    ).encode()
    return metadata, archive


def test_sync_downloads_validates_and_manages_future_replacements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata, archive = _artifact(tmp_path)
    opener = FakeOpener(metadata, archive)
    destination = tmp_path / "github.sqlite3"
    monkeypatch.setenv("GH_TOKEN", "test-token")

    first = sync_github_database(destination, opener=opener)
    second = sync_github_database(destination, opener=opener)

    assert first.artifact_id == 1234
    assert first.distinct_record_count == 2
    assert second.distinct_record_count == 2
    assert destination.is_file()
    sidecar = destination.with_name("github.sqlite3.sync.json")
    sync_metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    assert sync_metadata["artifact_id"] == 1234
    assert sync_metadata["repository"] == "IffyZh/astrocareer-observatory"
    assert opener.requests[0][0].headers["Authorization"] == "Bearer test-token"


def test_sync_refuses_to_replace_an_unmanaged_database(tmp_path: Path) -> None:
    destination = tmp_path / "personal.sqlite3"
    destination.write_bytes(b"personal data")

    with pytest.raises(GitHubArtifactSyncError, match="unmanaged"):
        sync_github_database(destination, opener=lambda *_args, **_kwargs: None)

    assert destination.read_bytes() == b"personal data"


def test_sync_rejects_a_digest_mismatch_before_installing(tmp_path: Path) -> None:
    metadata, archive = _artifact(tmp_path)
    document = json.loads(metadata)
    document["artifacts"][0]["digest"] = f"sha256:{'0' * 64}"
    opener = FakeOpener(json.dumps(document).encode(), archive)
    destination = tmp_path / "github.sqlite3"

    with pytest.raises(GitHubArtifactSyncError, match="digest"):
        sync_github_database(destination, opener=opener)

    assert not destination.exists()


def test_cross_host_redirect_does_not_forward_github_token() -> None:
    request = Request(
        "https://api.github.com/repos/example/project/actions/artifacts/1/zip",
        headers={"Authorization": "Bearer secret"},
    )

    redirected = _SafeRedirect().redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        "https://signed-artifacts.example.test/download",
    )

    assert redirected is not None
    assert redirected.get_header("Authorization") is None
