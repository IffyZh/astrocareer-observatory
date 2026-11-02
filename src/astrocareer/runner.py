"""Orchestrate collection, persistence, and reviewable normalization."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from astrocareer.collectors import Checkpoint, CollectionStatus, Collector, Transport
from astrocareer.database import persist_collection_batch, persist_normalization_candidate
from astrocareer.normalization import normalize_source_posting
from astrocareer.sources import SourceDefinition


class CollectionBlocked(RuntimeError):
    """Raised when safety policy prevents a collection run."""


@dataclass(frozen=True)
class RunReport:
    source_id: str
    collection_status: CollectionStatus
    record_count: int
    issue_count: int
    candidate_count: int
    persisted: bool
    run_id: str | None


def _parse_database_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _previous_checkpoint(connection: sqlite3.Connection, source_id: str) -> str | None:
    row = connection.execute(
        """
        SELECT checkpoint_after
        FROM collection_runs
        WHERE source_id = ? AND checkpoint_after IS NOT NULL
        ORDER BY finished_at DESC
        LIMIT 1
        """,
        (source_id,),
    ).fetchone()
    return str(row[0]) if row else None


def _enforce_minimum_interval(
    connection: sqlite3.Connection,
    source: SourceDefinition,
    now: datetime,
) -> None:
    row = connection.execute(
        """
        SELECT finished_at
        FROM collection_runs
        WHERE source_id = ?
        ORDER BY finished_at DESC
        LIMIT 1
        """,
        (source.source_id,),
    ).fetchone()
    if not row:
        return
    next_allowed = _parse_database_time(str(row[0])) + timedelta(
        seconds=source.minimum_interval_seconds
    )
    if now < next_allowed:
        raise CollectionBlocked(
            f"Source {source.source_id} is rate-limited until {next_allowed.isoformat()}"
        )


def run_collection(
    connection: sqlite3.Connection,
    *,
    source: SourceDefinition,
    collector: Collector,
    transport: Transport,
    collector_version: str,
    normalizer_version: str,
    dry_run: bool = False,
    allow_disabled: bool = False,
    enforce_interval: bool = True,
    now: datetime | None = None,
) -> RunReport:
    """Run one source safely and optionally persist its reviewable output."""
    if collector.source_id != source.source_id:
        raise CollectionBlocked(
            f"Collector source {collector.source_id} does not match {source.source_id}"
        )
    if not source.enabled and not allow_disabled:
        raise CollectionBlocked(f"Source is disabled: {source.source_id}")

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise ValueError("Runner time must be timezone-aware")
    if enforce_interval:
        _enforce_minimum_interval(connection, source, current_time)

    checkpoint_value = _previous_checkpoint(connection, source.source_id)
    checkpoint = Checkpoint(checkpoint_value) if checkpoint_value else None
    batch = collector.collect(transport, checkpoint)
    candidates = tuple(normalize_source_posting(record) for record in batch.records)

    if dry_run:
        return RunReport(
            source_id=source.source_id,
            collection_status=batch.status,
            record_count=len(batch.records),
            issue_count=len(batch.issues),
            candidate_count=len(candidates),
            persisted=False,
            run_id=None,
        )

    with connection:
        run_id = persist_collection_batch(
            connection,
            batch,
            collector_version=collector_version,
            checkpoint_before=checkpoint_value,
            manage_transaction=False,
        )
        observation_ids = {
            row["source_record_id"]: row["source_record_observation_id"]
            for row in connection.execute(
                """
                SELECT source_record_id, source_record_observation_id
                FROM source_record_observations
                WHERE run_id = ?
                """,
                (run_id,),
            )
        }
        for record, candidate in zip(batch.records, candidates, strict=True):
            persist_normalization_candidate(
                connection,
                source_record_observation_id=observation_ids[record.source_record_id],
                candidate=candidate,
                normalizer_version=normalizer_version,
                manage_transaction=False,
            )

    return RunReport(
        source_id=source.source_id,
        collection_status=batch.status,
        record_count=len(batch.records),
        issue_count=len(batch.issues),
        candidate_count=len(candidates),
        persisted=True,
        run_id=run_id,
    )

