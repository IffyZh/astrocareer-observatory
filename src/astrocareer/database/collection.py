"""Persist collector batches without normalizing source claims."""

import hashlib
import json
import sqlite3
from contextlib import nullcontext
from dataclasses import asdict
from datetime import timezone
from uuid import uuid4

from astrocareer.collectors import CollectionBatch


def _isoformat_utc(value: object) -> str:
    if not hasattr(value, "astimezone"):
        raise TypeError("Expected a datetime value")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def persist_collection_batch(
    connection: sqlite3.Connection,
    batch: CollectionBatch,
    *,
    collector_version: str,
    checkpoint_before: str | None = None,
    manage_transaction: bool = True,
) -> str:
    """Store one immutable collection batch and return its run ID.

    Snapshot bytes are intentionally not written by this function. A future raw
    evidence store may provide ``storage_path`` values under source-specific
    retention and redistribution rules.
    """
    source_exists = connection.execute(
        "SELECT 1 FROM sources WHERE source_id = ?", (batch.source_id,)
    ).fetchone()
    if not source_exists:
        raise ValueError(f"Source is not registered: {batch.source_id}")
    if not batch.snapshots:
        raise ValueError("A collection batch must contain at least one snapshot")

    run_id = str(uuid4())
    observed_times = [snapshot.observed_at for snapshot in batch.snapshots]
    started_at = _isoformat_utc(min(observed_times))
    finished_at = _isoformat_utc(max(observed_times))
    checkpoint_after = batch.next_checkpoint.value if batch.next_checkpoint else None

    snapshot_ids: dict[tuple[str, str], str] = {}
    transaction = connection if manage_transaction else nullcontext()
    with transaction:
        connection.execute(
            """
            INSERT INTO collection_runs (
                run_id, source_id, collector_version, started_at, finished_at,
                status, checkpoint_before, checkpoint_after, record_count, issue_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                batch.source_id,
                collector_version,
                started_at,
                finished_at,
                batch.status.value,
                checkpoint_before,
                checkpoint_after,
                len(batch.records),
                len(batch.issues),
            ),
        )
        for snapshot in batch.snapshots:
            snapshot_id = str(uuid4())
            snapshot_ids[(snapshot.url, snapshot.content_sha256)] = snapshot_id
            connection.execute(
                """
                INSERT INTO snapshots (
                    snapshot_id, run_id, source_id, url, observed_at, status_code,
                    content_type, content_sha256, byte_count, etag, last_modified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    run_id,
                    snapshot.source_id,
                    snapshot.url,
                    _isoformat_utc(snapshot.observed_at),
                    snapshot.status_code,
                    snapshot.content_type,
                    snapshot.content_sha256,
                    len(snapshot.content),
                    snapshot.etag,
                    snapshot.last_modified,
                ),
            )

        for record in batch.records:
            snapshot_id = snapshot_ids.get((record.snapshot_url, record.snapshot_sha256))
            if snapshot_id is None:
                raise ValueError(
                    f"Record {record.source_record_id} references a snapshot outside its batch"
                )
            record_json = _canonical_json(asdict(record))
            connection.execute(
                """
                INSERT INTO source_record_observations (
                    source_record_observation_id, run_id, snapshot_id, source_id,
                    source_record_id, canonical_url, observed_at,
                    record_json, record_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    run_id,
                    snapshot_id,
                    record.source_id,
                    record.source_record_id,
                    record.canonical_url,
                    finished_at,
                    record_json,
                    hashlib.sha256(record_json.encode("utf-8")).hexdigest(),
                ),
            )

        default_snapshot_id = next(iter(snapshot_ids.values()))
        for issue in batch.issues:
            connection.execute(
                """
                INSERT INTO collection_issues (
                    issue_id, run_id, snapshot_id, severity, code, message,
                    source_record_id, locator
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    run_id,
                    default_snapshot_id,
                    issue.severity.value,
                    issue.code,
                    issue.message,
                    issue.source_record_id,
                    issue.locator,
                ),
            )
    return run_id
