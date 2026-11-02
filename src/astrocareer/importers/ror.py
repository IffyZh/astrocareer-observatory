"""Import an official ROR Schema 2.x JSON data dump into SQLite."""

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from math import isfinite
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

ROR_SOURCE_ID = "ror-data-dump"
ROR_ID_PATTERN = re.compile(r"^https://ror\.org/[0-9a-z]{9}$")
ALLOWED_STATUSES = {"active", "inactive", "withdrawn"}
ALLOWED_TYPES = {
    "archive",
    "company",
    "education",
    "facility",
    "funder",
    "government",
    "healthcare",
    "nonprofit",
    "other",
}


@dataclass(frozen=True)
class RORImportReport:
    import_run_id: str
    dataset_version: str
    content_sha256: str
    record_count: int
    inserted_count: int
    updated_count: int
    reused_existing_run: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_records(path: Path) -> Iterator[dict[str, Any]]:
    """Stream a top-level JSON array when ijson is available, with a stdlib fallback."""
    try:
        import ijson  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
        if not isinstance(document, list):
            raise ValueError("ROR data dump must be a top-level JSON array")
        for record in document:
            if not isinstance(record, dict):
                raise ValueError("Every ROR record must be a JSON object")
            yield record
        return

    with path.open("rb") as handle:
        for record in ijson.items(handle, "item"):
            if not isinstance(record, dict):
                raise ValueError("Every ROR record must be a JSON object")
            yield record


def _required_string(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"ROR record has invalid required field: {field}")
    return value.strip()


def _display_name(record: dict[str, Any]) -> str:
    names = record.get("names")
    if not isinstance(names, list):
        raise ValueError("ROR record names must be an array")
    display = [
        item.get("value")
        for item in names
        if isinstance(item, dict)
        and isinstance(item.get("types"), list)
        and "ror_display" in item["types"]
        and isinstance(item.get("value"), str)
        and item["value"].strip()
    ]
    if len(display) != 1:
        raise ValueError("ROR record must contain exactly one ror_display name")
    return display[0].strip()


def _normalize_domain(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("ROR domain must be a non-empty string")
    domain = value.strip().rstrip(".").casefold()
    if "://" in domain or "/" in domain or any(character.isspace() for character in domain):
        raise ValueError(f"Invalid ROR domain: {value!r}")
    try:
        ascii_domain = domain.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError(f"Invalid internationalized ROR domain: {value!r}") from error
    if "." not in ascii_domain or ascii_domain.startswith(".") or ascii_domain.endswith("."):
        raise ValueError(f"Invalid ROR domain: {value!r}")
    return ascii_domain


def _website(record: dict[str, Any]) -> str | None:
    links = record.get("links", [])
    if not isinstance(links, list):
        raise ValueError("ROR links must be an array")
    for link in links:
        if (
            isinstance(link, dict)
            and link.get("type") == "website"
            and isinstance(link.get("value"), str)
            and link["value"].strip()
        ):
            return link["value"].strip()
    return None


def _admin_date(record: dict[str, Any], key: str) -> str | None:
    admin = record.get("admin", {})
    if not isinstance(admin, dict):
        raise ValueError("ROR admin must be an object")
    value = admin.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"ROR admin.{key} must be an object")
    date = value.get("date")
    if date is None:
        return None
    if not isinstance(date, str):
        raise ValueError(f"ROR admin.{key}.date must be a string")
    return date


def _schema_versions(record: dict[str, Any]) -> set[str]:
    versions: set[str] = set()
    admin = record.get("admin", {})
    if isinstance(admin, dict):
        for key in ("created", "last_modified"):
            value = admin.get(key, {})
            if isinstance(value, dict) and isinstance(value.get("schema_version"), str):
                versions.add(value["schema_version"])
    if not versions or any(not version.startswith("2.") for version in versions):
        raise ValueError("ROR import requires Schema 2.x records")
    return versions


def _coordinate(
    value: object,
    *,
    field: str,
    minimum: float,
    maximum: float,
    ror_id: str,
) -> float | None:
    """Normalize stdlib JSON floats and ijson Decimal values for SQLite."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"ROR {field} must be numeric for {ror_id}")
    coordinate = float(value)
    if not isfinite(coordinate) or not minimum <= coordinate <= maximum:
        raise ValueError(f"ROR {field} is outside its valid range for {ror_id}")
    return coordinate


def _upsert_record(
    connection: sqlite3.Connection,
    record: dict[str, Any],
    *,
    observed_at: str,
    source_id: str,
) -> bool:
    ror_id = _required_string(record, "id")
    if not ROR_ID_PATTERN.fullmatch(ror_id):
        raise ValueError(f"Invalid ROR ID: {ror_id!r}")
    name = _display_name(record)
    status = _required_string(record, "status").casefold()
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid ROR status for {ror_id}: {status!r}")

    raw_types = record.get("types", [])
    if not isinstance(raw_types, list) or any(not isinstance(item, str) for item in raw_types):
        raise ValueError(f"ROR types must be an array of strings for {ror_id}")
    organization_types = {item.casefold() for item in raw_types}
    if not organization_types <= ALLOWED_TYPES:
        raise ValueError(f"Unsupported ROR organization type for {ror_id}")

    raw_locations = record.get("locations", [])
    if not isinstance(raw_locations, list):
        raise ValueError(f"ROR locations must be an array for {ror_id}")
    country_code: str | None = None
    if raw_locations:
        first_details = raw_locations[0].get("geonames_details", {})
        if isinstance(first_details, dict) and isinstance(first_details.get("country_code"), str):
            country_code = first_details["country_code"].upper()

    established = record.get("established")
    if established is not None and (
        not isinstance(established, int) or isinstance(established, bool)
    ):
        raise ValueError(f"ROR established must be an integer for {ror_id}")

    existed = connection.execute(
        "SELECT 1 FROM institutions WHERE ror_id = ? OR institution_id = ?",
        (ror_id, ror_id),
    ).fetchone()
    connection.execute(
        """
        INSERT INTO institutions (
            institution_id, name, country_code, homepage_url, ror_id, status,
            established_year, source_created_at, source_updated_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(institution_id) DO UPDATE SET
            name = excluded.name,
            country_code = excluded.country_code,
            homepage_url = excluded.homepage_url,
            ror_id = excluded.ror_id,
            status = excluded.status,
            established_year = excluded.established_year,
            source_created_at = excluded.source_created_at,
            source_updated_at = excluded.source_updated_at,
            updated_at = excluded.updated_at
        """,
        (
            ror_id,
            name,
            country_code,
            _website(record),
            ror_id,
            status,
            established,
            _admin_date(record, "created"),
            _admin_date(record, "last_modified"),
            observed_at,
        ),
    )

    connection.execute("DELETE FROM institution_names WHERE institution_id = ?", (ror_id,))
    for item in record.get("names", []):
        if not isinstance(item, dict) or not isinstance(item.get("value"), str):
            raise ValueError(f"Invalid ROR name entry for {ror_id}")
        types = item.get("types")
        if not isinstance(types, list) or any(not isinstance(value, str) for value in types):
            raise ValueError(f"Invalid ROR name types for {ror_id}")
        language = item.get("lang")
        if language is not None and not isinstance(language, str):
            raise ValueError(f"Invalid ROR name language for {ror_id}")
        connection.execute(
            """
            INSERT INTO institution_names (
                institution_id, name, language_code, name_types_json, source_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                ror_id,
                item["value"].strip(),
                language,
                json.dumps(sorted(set(types)), separators=(",", ":")),
                source_id,
            ),
        )

    connection.execute(
        "UPDATE institution_domains SET active = 0 WHERE institution_id = ?", (ror_id,)
    )
    raw_domains = record.get("domains", [])
    if not isinstance(raw_domains, list):
        raise ValueError(f"ROR domains must be an array for {ror_id}")
    for domain in sorted({_normalize_domain(value) for value in raw_domains}):
        connection.execute(
            """
            INSERT INTO institution_domains (
                institution_id, domain, source_id, first_seen_at, last_seen_at, active
            ) VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(institution_id, domain) DO UPDATE SET
                source_id = excluded.source_id,
                last_seen_at = excluded.last_seen_at,
                active = 1
            """,
            (ror_id, domain, source_id, observed_at, observed_at),
        )

    connection.execute("DELETE FROM institution_types WHERE institution_id = ?", (ror_id,))
    for organization_type in sorted(organization_types):
        connection.execute(
            "INSERT INTO institution_types VALUES (?, ?, ?)",
            (ror_id, organization_type, source_id),
        )

    connection.execute("DELETE FROM institution_locations WHERE institution_id = ?", (ror_id,))
    for location in raw_locations:
        if not isinstance(location, dict) or not isinstance(location.get("geonames_id"), int):
            raise ValueError(f"Invalid ROR location for {ror_id}")
        details = location.get("geonames_details", {})
        if not isinstance(details, dict):
            raise ValueError(f"Invalid ROR geonames details for {ror_id}")
        connection.execute(
            """
            INSERT INTO institution_locations (
                institution_id, geonames_id, name, country_code, country_name,
                subdivision_code, subdivision_name, continent_code,
                latitude, longitude, source_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ror_id,
                location["geonames_id"],
                details.get("name"),
                details.get("country_code"),
                details.get("country_name"),
                details.get("country_subdivision_code"),
                details.get("country_subdivision_name"),
                details.get("continent_code"),
                _coordinate(
                    details.get("lat"),
                    field="latitude",
                    minimum=-90.0,
                    maximum=90.0,
                    ror_id=ror_id,
                ),
                _coordinate(
                    details.get("lng"),
                    field="longitude",
                    minimum=-180.0,
                    maximum=180.0,
                    ror_id=ror_id,
                ),
                source_id,
            ),
        )
    return existed is None


def import_ror_dump(
    connection: sqlite3.Connection,
    path: str | Path,
    *,
    dataset_version: str,
    importer_version: str = "ror-v2-1",
    source_id: str = ROR_SOURCE_ID,
) -> RORImportReport:
    """Atomically import one official, local ROR Schema 2.x JSON dump."""
    dump_path = Path(path)
    if not dump_path.is_file():
        raise ValueError(f"ROR data dump does not exist: {dump_path}")
    if not dataset_version.strip():
        raise ValueError("dataset_version is required")
    source = connection.execute(
        "SELECT collection_method FROM sources WHERE source_id = ?", (source_id,)
    ).fetchone()
    if source is None:
        raise ValueError(f"ROR source is not registered: {source_id}")
    if source[0] != "import":
        raise ValueError("ROR source must use the import collection method")

    content_sha256 = _file_sha256(dump_path)
    previous = connection.execute(
        """
        SELECT import_run_id, dataset_version, record_count, inserted_count, updated_count
        FROM institution_import_runs WHERE content_sha256 = ?
        """,
        (content_sha256,),
    ).fetchone()
    if previous:
        return RORImportReport(
            import_run_id=previous[0],
            dataset_version=previous[1],
            content_sha256=content_sha256,
            record_count=previous[2],
            inserted_count=previous[3],
            updated_count=previous[4],
            reused_existing_run=True,
        )

    started_at = _utc_now()
    import_run_id = str(uuid4())
    record_count = 0
    inserted_count = 0
    updated_count = 0
    schema_versions: set[str] = set()
    seen_ids: set[str] = set()
    with connection:
        for record in _iter_records(dump_path):
            ror_id = _required_string(record, "id")
            if ror_id in seen_ids:
                raise ValueError(f"Duplicate ROR ID in data dump: {ror_id}")
            seen_ids.add(ror_id)
            schema_versions.update(_schema_versions(record))
            inserted = _upsert_record(
                connection,
                record,
                observed_at=started_at,
                source_id=source_id,
            )
            record_count += 1
            inserted_count += int(inserted)
            updated_count += int(not inserted)
        if record_count == 0:
            raise ValueError("ROR data dump contains no records")
        finished_at = _utc_now()
        connection.execute(
            """
            INSERT INTO institution_import_runs (
                import_run_id, source_id, dataset_version, content_sha256,
                started_at, finished_at, record_count, inserted_count,
                updated_count, importer_version, schema_versions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                import_run_id,
                source_id,
                dataset_version.strip(),
                content_sha256,
                started_at,
                finished_at,
                record_count,
                inserted_count,
                updated_count,
                importer_version,
                json.dumps(sorted(schema_versions), separators=(",", ":")),
            ),
        )

    return RORImportReport(
        import_run_id=import_run_id,
        dataset_version=dataset_version.strip(),
        content_sha256=content_sha256,
        record_count=record_count,
        inserted_count=inserted_count,
        updated_count=updated_count,
        reused_existing_run=False,
    )
