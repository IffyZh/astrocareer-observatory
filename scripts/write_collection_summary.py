"""Write a small Markdown summary for a scheduled collection run."""

import os
import sqlite3
from pathlib import Path


def _scalar(connection: sqlite3.Connection, query: str, parameters: tuple[str, ...] = ()) -> int:
    row = connection.execute(query, parameters).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def main() -> None:
    """Print non-sensitive aggregate state as GitHub-flavored Markdown."""
    database_path = Path(os.environ["DATABASE_PATH"])
    source_id = "planetary-research-jobs-feed"
    with sqlite3.connect(database_path) as connection:
        run = connection.execute(
            """
            SELECT finished_at, status, record_count, issue_count
            FROM collection_runs
            WHERE source_id = ?
            ORDER BY finished_at DESC
            LIMIT 1
            """,
            (source_id,),
        ).fetchone()
        observations = _scalar(
            connection,
            "SELECT count(*) FROM source_record_observations WHERE source_id = ?",
            (source_id,),
        )
        distinct_records = _scalar(
            connection,
            """
            SELECT count(DISTINCT source_record_id)
            FROM source_record_observations
            WHERE source_id = ?
            """,
            (source_id,),
        )
        pending_candidates = _scalar(
            connection,
            """
            SELECT count(*)
            FROM normalization_candidates nc
            JOIN source_record_observations sro
              ON sro.source_record_observation_id = nc.source_record_observation_id
            WHERE sro.source_id = ? AND nc.review_status = 'pending'
            """,
            (source_id,),
        )

    if run is None:
        raise RuntimeError("Collection completed without a persisted run")
    finished_at, status, record_count, issue_count = run
    restored = os.environ.get("STATE_RESTORED", "false")
    print("## Scheduled collection")
    print()
    print(f"- Previous state restored: `{restored}`")
    print(f"- Latest run: `{finished_at}` (`{status}`)")
    print(f"- Latest feed records: `{record_count}`")
    print(f"- Latest parser issues: `{issue_count}`")
    print(f"- Stored observations: `{observations}`")
    print(f"- Distinct source record IDs: `{distinct_records}`")
    print(f"- Pending normalization candidates: `{pending_candidates}`")
    print()
    print("The collector did not follow any official-announcement links.")


if __name__ == "__main__":
    main()

