"""Persist reviewable normalization candidates without modifying postings."""

import hashlib
import json
import sqlite3
from contextlib import nullcontext
from uuid import uuid4

from astrocareer.normalization import NormalizedPostingCandidate


def persist_normalization_candidate(
    connection: sqlite3.Connection,
    *,
    source_record_observation_id: str,
    candidate: NormalizedPostingCandidate,
    normalizer_version: str,
    manage_transaction: bool = True,
) -> str:
    """Persist a pending candidate and return its stable row ID."""
    document = json.dumps(
        candidate.as_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(document.encode("utf-8")).hexdigest()
    existing = connection.execute(
        """
        SELECT candidate_id
        FROM normalization_candidates
        WHERE source_record_observation_id = ?
          AND normalizer_version = ?
          AND candidate_sha256 = ?
        """,
        (source_record_observation_id, normalizer_version, digest),
    ).fetchone()
    if existing:
        return str(existing[0])

    candidate_id = str(uuid4())
    transaction = connection if manage_transaction else nullcontext()
    with transaction:
        connection.execute(
            """
            INSERT INTO normalization_candidates (
                candidate_id, source_record_observation_id, normalizer_version,
                candidate_json, candidate_sha256
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                source_record_observation_id,
                normalizer_version,
                document,
                digest,
            ),
        )
    return candidate_id
