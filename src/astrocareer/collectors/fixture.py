"""Explicitly offline transport for fixtures and manual parser inspection."""

from datetime import datetime, timezone
from pathlib import Path

from astrocareer.collectors.base import RawSnapshot, RequestSpec


class FixtureTransport:
    """Return one local file for every request without accessing a network."""

    def __init__(
        self,
        path: str | Path,
        *,
        status_code: int = 200,
        content_type: str = "text/html; charset=utf-8",
        observed_at: datetime | None = None,
    ) -> None:
        self.path = Path(path)
        self.status_code = status_code
        self.content_type = content_type
        self.observed_at = observed_at
        self.requests: list[RequestSpec] = []

    def fetch(self, request: RequestSpec) -> RawSnapshot:
        """Read the configured fixture and preserve the collector request URL."""
        self.requests.append(request)
        return RawSnapshot.create(
            source_id=request.source_id,
            url=request.url,
            observed_at=self.observed_at or datetime.now(timezone.utc),
            status_code=self.status_code,
            content_type=self.content_type,
            content=self.path.read_bytes(),
        )

