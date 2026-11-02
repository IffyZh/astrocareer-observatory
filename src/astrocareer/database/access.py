"""Audit real network access without retaining response content."""

import sqlite3
from datetime import datetime
from uuid import uuid4


def record_source_access_attempt(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    requested_at: datetime,
    mode: str,
    contact_url: str,
) -> str:
    """Persist a minimal access timestamp before a real network request."""
    if requested_at.tzinfo is None:
        raise ValueError("Access attempt time must be timezone-aware")
    if mode not in {"dry_run", "persisted"}:
        raise ValueError(f"Unsupported access mode: {mode}")
    if not contact_url.startswith("https://"):
        raise ValueError("Access contact URL must use HTTPS")
    access_attempt_id = str(uuid4())
    connection.execute(
        """
        INSERT INTO source_access_attempts (
            access_attempt_id, source_id, requested_at, mode, contact_url
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            access_attempt_id,
            source_id,
            requested_at.isoformat(),
            mode,
            contact_url,
        ),
    )
    return access_attempt_id
