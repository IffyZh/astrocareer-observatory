"""Immutable local captures for repeatable, offline collector development."""

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from astrocareer.collectors.base import RawSnapshot, RequestSpec, Transport

_CAPTURE_SCHEMA_VERSION = 1
_MANIFEST_NAME = "manifest.json"
_RESPONSE_NAME = "response.bin"


class CaptureError(RuntimeError):
    """A local capture could not be written or replayed safely."""


class CaptureTransport:
    """Wrap a transport and save its first response as an immutable ZIP file."""

    def __init__(self, delegate: Transport, path: str | Path) -> None:
        self.delegate = delegate
        self.path = Path(path)
        if self.path.exists():
            raise CaptureError(f"Capture already exists and will not be overwritten: {self.path}")

    def fetch(self, request: RequestSpec) -> RawSnapshot:
        if self.path.exists():
            raise CaptureError(f"Capture already exists and will not be overwritten: {self.path}")
        snapshot = self.delegate.fetch(request)
        self._write(snapshot)
        return snapshot

    def _write(self, snapshot: RawSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": _CAPTURE_SCHEMA_VERSION,
            "source_id": snapshot.source_id,
            "url": snapshot.url,
            "observed_at": snapshot.observed_at.isoformat(),
            "status_code": snapshot.status_code,
            "content_type": snapshot.content_type,
            "content_sha256": snapshot.content_sha256,
            "etag": snapshot.etag,
            "last_modified": snapshot.last_modified,
        }
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED) as archive:
                archive.writestr(
                    _MANIFEST_NAME,
                    json.dumps(manifest, ensure_ascii=False, sort_keys=True),
                )
                archive.writestr(_RESPONSE_NAME, snapshot.content)
            if self.path.exists():
                raise CaptureError(
                    f"Capture already exists and will not be overwritten: {self.path}"
                )
            os.link(temporary_path, self.path)
        except FileExistsError as error:
            raise CaptureError(
                f"Capture already exists and will not be overwritten: {self.path}"
            ) from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


class ReplayTransport:
    """Replay one validated local capture without network access."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def fetch(self, request: RequestSpec) -> RawSnapshot:
        try:
            with ZipFile(self.path) as archive:
                if set(archive.namelist()) != {_MANIFEST_NAME, _RESPONSE_NAME}:
                    raise CaptureError("Capture contains unexpected or missing files")
                manifest = json.loads(archive.read(_MANIFEST_NAME))
                content = archive.read(_RESPONSE_NAME)
        except (BadZipFile, FileNotFoundError, json.JSONDecodeError, OSError) as error:
            raise CaptureError(f"Invalid local capture: {self.path}") from error

        if not isinstance(manifest, dict):
            raise CaptureError("Capture manifest must be a JSON object")
        if manifest.get("schema_version") != _CAPTURE_SCHEMA_VERSION:
            raise CaptureError("Unsupported capture schema version")
        if manifest.get("source_id") != request.source_id:
            raise CaptureError("Capture source does not match the collector request")
        if manifest.get("url") != request.url:
            raise CaptureError("Capture URL does not match the collector request")
        digest = hashlib.sha256(content).hexdigest()
        if manifest.get("content_sha256") != digest:
            raise CaptureError("Capture response hash does not match its manifest")
        try:
            observed_at = datetime.fromisoformat(str(manifest["observed_at"]))
            status_code = int(manifest["status_code"])
        except (KeyError, TypeError, ValueError) as error:
            raise CaptureError("Capture manifest has invalid response metadata") from error

        def optional_text(name: str) -> str | None:
            value = manifest.get(name)
            if value is not None and not isinstance(value, str):
                raise CaptureError(f"Capture manifest field {name!r} must be text or null")
            return value

        try:
            return RawSnapshot.create(
                source_id=request.source_id,
                url=request.url,
                observed_at=observed_at,
                status_code=status_code,
                content_type=optional_text("content_type"),
                content=content,
                etag=optional_text("etag"),
                last_modified=optional_text("last_modified"),
            )
        except ValueError as error:
            raise CaptureError("Capture manifest contains invalid snapshot values") from error
