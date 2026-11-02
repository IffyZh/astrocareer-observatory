"""Database initialization and small domain calculations."""

import sqlite3
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

SCHEMA_VERSION = 7

MIGRATION_FILES = {
    1: "0001_initial.sql",
    2: "0002_collection_runs.sql",
    3: "0003_employment_terms.sql",
    4: "0004_normalization_candidates.sql",
    5: "0005_source_access_policies.sql",
    6: "0006_source_allowed_paths.sql",
    7: "0007_ror_institution_registry.sql",
}


@dataclass(frozen=True)
class SelectionMetrics:
    """Selection measures derived from reported recruitment counts."""

    selection_rate: float | None
    applicants_per_hire: float | None


def calculate_selection_metrics(
    applications_submitted: int,
    hires_final: int,
) -> SelectionMetrics:
    """Calculate selection measures without inventing undefined values."""
    if applications_submitted < 0 or hires_final < 0:
        raise ValueError("Recruitment counts cannot be negative")
    if hires_final > applications_submitted:
        raise ValueError("Final hires cannot exceed submitted applications")
    if applications_submitted == 0:
        return SelectionMetrics(selection_rate=None, applicants_per_hire=None)
    if hires_final == 0:
        return SelectionMetrics(selection_rate=0.0, applicants_per_hire=None)
    return SelectionMetrics(
        selection_rate=hires_final / applications_submitted,
        applicants_per_hire=applications_submitted / hires_final,
    )


def connect_database(path: str | Path) -> sqlite3.Connection:
    """Open a database with integrity safeguards enabled."""
    connection = sqlite3.connect(Path(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _migration_sql(version: int) -> str:
    try:
        filename = MIGRATION_FILES[version]
    except KeyError as error:
        raise RuntimeError(f"No migration file registered for version {version}") from error
    resource = files("astrocareer.database.migrations").joinpath(filename)
    return resource.read_text(encoding="utf-8")


def initialize_database(path: str | Path) -> int:
    """Create or validate an AstroCareer database and return its schema version."""
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with connect_database(database_path) as connection:
        has_migrations = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
        ).fetchone()
        if not has_migrations:
            connection.executescript(_migration_sql(1))

        version = get_schema_version(connection)
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Unsupported schema version {version}; latest supported is {SCHEMA_VERSION}"
            )
        for next_version in range(version + 1, SCHEMA_VERSION + 1):
            connection.executescript(_migration_sql(next_version))
        version = get_schema_version(connection)
        if version != SCHEMA_VERSION:
            raise RuntimeError(
                f"Unsupported schema version {version}; expected {SCHEMA_VERSION}"
            )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Database integrity check failed: {integrity}")
        return version


def get_schema_version(connection: sqlite3.Connection) -> int:
    """Return the most recently applied schema version."""
    row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("Database has no schema version")
    return int(row[0])
