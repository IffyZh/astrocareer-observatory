"""Rebuild normalization candidates from persisted source observations."""

import json
import sqlite3
from dataclasses import dataclass, fields
from datetime import datetime, timezone

from astrocareer.collectors import SourcePosting
from astrocareer.database.normalization import persist_normalization_candidate
from astrocareer.normalization import normalize_source_posting


@dataclass(frozen=True)
class RenormalizationReport:
    source_id: str
    normalizer_version: str
    observation_count: int
    inserted_count: int
    reused_count: int
    superseded_count: int


def _source_posting(document: str) -> SourcePosting:
    data = json.loads(document)
    if not isinstance(data, dict):
        raise ValueError("Stored source record must be a JSON object")
    allowed = {field.name for field in fields(SourcePosting)}
    values = {key: value for key, value in data.items() if key in allowed}
    for name in ("language_texts", "requirement_texts", "skill_texts"):
        values[name] = tuple(values.get(name) or ())
    raw_fields = tuple(tuple(item) for item in values.get("raw_fields") or ())
    values["raw_fields"] = raw_fields
    raw = dict(raw_fields)
    fallback_fields = {
        "source_category_text": "source_category",
        "department_text": "department",
        "positions_text": "number_of_positions",
        "extension_text": "extension_terms",
        "reference_code_text": "reference_code",
        "official_announcement_url": "official_announcement_url",
    }
    for target, legacy_name in fallback_fields.items():
        if not values.get(target):
            values[target] = raw.get(legacy_name)
    return SourcePosting(**values)


def renormalize_source_observations(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    normalizer_version: str,
) -> RenormalizationReport:
    """Create current candidates for existing observations without network access."""
    observations = connection.execute(
        """
        SELECT source_record_observation_id, record_json
        FROM source_record_observations
        WHERE source_id = ?
        ORDER BY observed_at, source_record_id
        """,
        (source_id,),
    ).fetchall()
    before = connection.execute(
        """
        SELECT count(*)
        FROM normalization_candidates nc
        JOIN source_record_observations sro
          ON sro.source_record_observation_id = nc.source_record_observation_id
        WHERE sro.source_id = ? AND nc.normalizer_version = ?
        """,
        (source_id, normalizer_version),
    ).fetchone()[0]
    superseded = 0
    reviewed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with connection:
        for observation in observations:
            candidate = normalize_source_posting(_source_posting(observation["record_json"]))
            persist_normalization_candidate(
                connection,
                source_record_observation_id=observation["source_record_observation_id"],
                candidate=candidate,
                normalizer_version=normalizer_version,
                manage_transaction=False,
            )
            cursor = connection.execute(
                """
                UPDATE normalization_candidates
                SET review_status = 'superseded',
                    review_notes = ?,
                    reviewed_at = ?
                WHERE source_record_observation_id = ?
                  AND normalizer_version != ?
                  AND review_status = 'pending'
                """,
                (
                    f"Superseded by normalizer {normalizer_version}",
                    reviewed_at,
                    observation["source_record_observation_id"],
                    normalizer_version,
                ),
            )
            superseded += cursor.rowcount
    after = connection.execute(
        """
        SELECT count(*)
        FROM normalization_candidates nc
        JOIN source_record_observations sro
          ON sro.source_record_observation_id = nc.source_record_observation_id
        WHERE sro.source_id = ? AND nc.normalizer_version = ?
        """,
        (source_id, normalizer_version),
    ).fetchone()[0]
    inserted = after - before
    return RenormalizationReport(
        source_id=source_id,
        normalizer_version=normalizer_version,
        observation_count=len(observations),
        inserted_count=inserted,
        reused_count=len(observations) - inserted,
        superseded_count=superseded,
    )
