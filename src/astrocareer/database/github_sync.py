"""Safely synchronize a collector-state database from GitHub Actions."""

import hashlib
import json
import os
import re
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from astrocareer.database.core import SCHEMA_VERSION, initialize_database

DEFAULT_REPOSITORY = "IffyZh/astrocareer-observatory"
DEFAULT_ARTIFACT = "collector-state"
_API_VERSION = "2022-11-28"
_MAX_ARCHIVE_BYTES = 100_000_000
_MAX_DATABASE_BYTES = 500_000_000
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class GitHubArtifactSyncError(RuntimeError):
    """Raised when a database artifact cannot be synchronized safely."""


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        if urlparse(newurl).scheme != "https":
            raise GitHubArtifactSyncError("GitHub attempted a non-HTTPS artifact redirect")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urlparse(req.full_url).hostname != urlparse(newurl).hostname:
            redirected.remove_header("Authorization")
        return redirected


def _open_url(request: Request, timeout: int):
    return build_opener(_SafeRedirect()).open(request, timeout=timeout)


@dataclass(frozen=True)
class GitHubSyncReport:
    repository: str
    artifact_name: str
    artifact_id: int
    artifact_created_at: str
    archive_sha256: str
    database_bytes: int
    distinct_record_count: int
    destination: str


def _headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": _API_VERSION,
        "User-Agent": "AstroCareerObservatory/0.0.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _read_limited(response: Any, maximum: int) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as error:
            raise GitHubArtifactSyncError("GitHub returned an invalid Content-Length") from error
        if declared_size > maximum:
            raise GitHubArtifactSyncError("GitHub artifact exceeds the download size limit")
    content = response.read(maximum + 1)
    if len(content) > maximum:
        raise GitHubArtifactSyncError("GitHub artifact exceeds the download size limit")
    return content


def _request_bytes(
    url: str,
    *,
    token: str | None,
    opener: Callable[..., Any],
) -> bytes:
    request = Request(url, headers=_headers(token), method="GET")
    try:
        with opener(request, timeout=30) as response:
            return _read_limited(response, _MAX_ARCHIVE_BYTES)
    except HTTPError as error:
        if error.code in {401, 403}:
            raise GitHubArtifactSyncError(
                "GitHub denied artifact access. Set GH_TOKEN or GITHUB_TOKEN to a "
                "fine-grained token with Actions: read permission for the repository."
            ) from error
        raise GitHubArtifactSyncError(f"GitHub returned HTTP {error.code}") from error
    except (TimeoutError, URLError, OSError) as error:
        raise GitHubArtifactSyncError(f"GitHub request failed: {error}") from error


def _latest_artifact(
    repository: str,
    artifact_name: str,
    *,
    token: str | None,
    opener: Callable[..., Any],
) -> dict[str, object]:
    encoded_name = quote(artifact_name, safe="")
    url = (
        f"https://api.github.com/repos/{repository}/actions/artifacts"
        f"?name={encoded_name}&per_page=100"
    )
    try:
        document = json.loads(_request_bytes(url, token=token, opener=opener))
    except json.JSONDecodeError as error:
        raise GitHubArtifactSyncError("GitHub returned invalid artifact metadata") from error
    artifacts = document.get("artifacts") if isinstance(document, dict) else None
    if not isinstance(artifacts, list):
        raise GitHubArtifactSyncError("GitHub artifact metadata has an unexpected shape")
    usable = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, dict)
        and artifact.get("name") == artifact_name
        and artifact.get("expired") is False
    ]
    if not usable:
        raise GitHubArtifactSyncError(
            f"No unexpired {artifact_name!r} artifact was found in {repository}"
        )
    return max(usable, key=lambda item: str(item.get("created_at") or ""))


def _managed_sidecar(
    destination: Path,
    *,
    repository: str,
    artifact_name: str,
    replace_unmanaged: bool,
) -> Path:
    sidecar = destination.with_name(f"{destination.name}.sync.json")
    if not destination.exists() or replace_unmanaged:
        return sidecar
    if not sidecar.is_file():
        raise GitHubArtifactSyncError(
            f"Refusing to replace unmanaged database {destination}. Choose a new path "
            "or pass --replace-unmanaged after making any needed backup."
        )
    try:
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GitHubArtifactSyncError(f"Invalid sync metadata: {sidecar}") from error
    if metadata.get("repository") != repository or metadata.get("artifact_name") != artifact_name:
        raise GitHubArtifactSyncError(
            "The existing database came from a different repository or artifact"
        )
    return sidecar


def _extract_database(archive: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = [item for item in bundle.infolist() if not item.is_dir()]
            if len(members) != 1 or Path(members[0].filename).name != "astrocareer.sqlite3":
                raise GitHubArtifactSyncError(
                    "collector-state must contain exactly one astrocareer.sqlite3 file"
                )
            member = members[0]
            if member.file_size > _MAX_DATABASE_BYTES:
                raise GitHubArtifactSyncError("SQLite database exceeds the size limit")
            with bundle.open(member) as source, destination.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
    except zipfile.BadZipFile as error:
        raise GitHubArtifactSyncError("GitHub artifact is not a valid ZIP archive") from error


def _validate_database(database_path: Path) -> int:
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        version = connection.execute("SELECT max(version) FROM schema_migrations").fetchone()[0]
        if version != SCHEMA_VERSION:
            raise GitHubArtifactSyncError(
                f"Database schema {version} does not match supported schema {SCHEMA_VERSION}"
            )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise GitHubArtifactSyncError(f"SQLite integrity check failed: {integrity}")
        record_count = int(
            connection.execute(
                """
                SELECT count(DISTINCT source_record_id)
                FROM source_record_observations
                WHERE source_id = 'planetary-research-jobs-feed'
                """
            ).fetchone()[0]
        )
    if record_count == 0:
        raise GitHubArtifactSyncError("Artifact database contains no collected feed records")
    return record_count


def sync_github_database(
    destination: Path,
    *,
    repository: str = DEFAULT_REPOSITORY,
    artifact_name: str = DEFAULT_ARTIFACT,
    token: str | None = None,
    replace_unmanaged: bool = False,
    opener: Callable[..., Any] = _open_url,
) -> GitHubSyncReport:
    """Download, verify, and atomically install the newest database artifact."""
    if not _REPOSITORY.fullmatch(repository):
        raise GitHubArtifactSyncError("Repository must use the OWNER/REPO format")
    if not artifact_name or len(artifact_name) > 128:
        raise GitHubArtifactSyncError("Artifact name must contain 1-128 characters")
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    sidecar = _managed_sidecar(
        destination,
        repository=repository,
        artifact_name=artifact_name,
        replace_unmanaged=replace_unmanaged,
    )
    access_token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    artifact = _latest_artifact(
        repository,
        artifact_name,
        token=access_token,
        opener=opener,
    )
    artifact_id = artifact.get("id")
    download_url = artifact.get("archive_download_url")
    created_at = artifact.get("created_at")
    if not isinstance(artifact_id, int) or not isinstance(download_url, str):
        raise GitHubArtifactSyncError("GitHub artifact metadata is incomplete")
    if not isinstance(created_at, str):
        created_at = "not_reported"

    archive_bytes = _request_bytes(download_url, token=access_token, opener=opener)
    archive_digest = hashlib.sha256(archive_bytes).hexdigest()
    expected_digest = artifact.get("digest")
    if isinstance(expected_digest, str) and expected_digest.startswith("sha256:"):
        if archive_digest != expected_digest.removeprefix("sha256:"):
            raise GitHubArtifactSyncError("Artifact SHA-256 digest does not match metadata")

    with tempfile.TemporaryDirectory(prefix="astrocareer-sync-", dir=destination.parent) as name:
        temporary_directory = Path(name)
        archive_path = temporary_directory / "collector-state.zip"
        database_path = temporary_directory / "astrocareer.sqlite3"
        archive_path.write_bytes(archive_bytes)
        _extract_database(archive_path, database_path)
        distinct_records = _validate_database(database_path)
        database_bytes = database_path.stat().st_size
        metadata = {
            "repository": repository,
            "artifact_name": artifact_name,
            "artifact_id": artifact_id,
            "artifact_created_at": created_at,
            "archive_sha256": archive_digest,
            "database_bytes": database_bytes,
            "distinct_record_count": distinct_records,
            "schema_version": SCHEMA_VERSION,
        }
        temporary_sidecar = temporary_directory / "sync.json"
        temporary_sidecar.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(database_path, destination)
        os.replace(temporary_sidecar, sidecar)

    return GitHubSyncReport(
        repository=repository,
        artifact_name=artifact_name,
        artifact_id=artifact_id,
        artifact_created_at=created_at,
        archive_sha256=archive_digest,
        database_bytes=database_bytes,
        distinct_record_count=distinct_records,
        destination=str(destination),
    )
