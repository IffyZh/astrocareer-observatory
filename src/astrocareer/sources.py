"""Validated source registry loaded from the public TOML configuration."""

import tomllib
import sqlite3
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    name: str
    organization: str
    homepage_url: str
    source_type: str
    authority_level: str
    collection_method: str
    enabled: bool
    access_status: str
    robots_reviewed_at: str
    terms_reviewed_at: str
    allowed_hosts: tuple[str, ...]
    allowed_path_prefixes: tuple[str, ...]
    minimum_interval_seconds: int
    redistribution_notes: str

    def __post_init__(self) -> None:
        homepage_host = urlparse(self.homepage_url).hostname
        if not self.source_id or not homepage_host:
            raise ValueError("A source requires an ID and valid homepage URL")
        if self.authority_level not in {"a", "b", "c", "d"}:
            raise ValueError(f"Invalid authority level: {self.authority_level}")
        if self.source_type not in {
            "employer",
            "professional_society",
            "government",
            "job_board",
            "research_dataset",
            "community",
            "other",
        }:
            raise ValueError(f"Invalid source type: {self.source_type}")
        if self.collection_method not in {"api", "feed", "email", "html", "manual", "import"}:
            raise ValueError(f"Invalid collection method: {self.collection_method}")
        if self.access_status not in {
            "approved",
            "manual_only",
            "api_only",
            "permission_required",
            "prohibited",
            "pending_review",
        }:
            raise ValueError(f"Invalid access status: {self.access_status}")
        if homepage_host not in self.allowed_hosts:
            raise ValueError("The homepage host must be included in allowed_hosts")
        if not self.allowed_path_prefixes or any(
            not path.startswith("/") or "?" in path or "#" in path
            for path in self.allowed_path_prefixes
        ):
            raise ValueError("allowed_path_prefixes must contain absolute URL paths")
        if self.minimum_interval_seconds < 0:
            raise ValueError("minimum_interval_seconds cannot be negative")


def load_source_registry(path: str | Path) -> dict[str, SourceDefinition]:
    """Load and validate a source registry without executing external content."""
    with Path(path).open("rb") as handle:
        document = tomllib.load(handle)
    if document.get("schema_version") != 1:
        raise ValueError("Unsupported source registry schema version")

    registry: dict[str, SourceDefinition] = {}
    for raw_source in document.get("sources", []):
        source = SourceDefinition(
            source_id=raw_source["source_id"],
            name=raw_source["name"],
            organization=raw_source["organization"],
            homepage_url=raw_source["homepage_url"],
            source_type=raw_source["source_type"],
            authority_level=raw_source["authority_level"],
            collection_method=raw_source["collection_method"],
            enabled=raw_source["enabled"],
            access_status=raw_source["access_status"],
            robots_reviewed_at=raw_source["robots_reviewed_at"],
            terms_reviewed_at=raw_source["terms_reviewed_at"],
            allowed_hosts=tuple(raw_source["allowed_hosts"]),
            allowed_path_prefixes=tuple(raw_source["allowed_path_prefixes"]),
            minimum_interval_seconds=raw_source["minimum_interval_seconds"],
            redistribution_notes=raw_source["redistribution_notes"],
        )
        if source.source_id in registry:
            raise ValueError(f"Duplicate source ID: {source.source_id}")
        registry[source.source_id] = source
    return registry


def sync_source_registry(
    connection: sqlite3.Connection,
    registry: dict[str, SourceDefinition],
) -> int:
    """Insert or update reviewed source definitions and return the row count."""
    with connection:
        for source in registry.values():
            connection.execute(
                """
                INSERT INTO sources (
                    source_id, name, organization, homepage_url, source_type,
                    authority_level, collection_method, enabled,
                    robots_reviewed_at, terms_reviewed_at, redistribution_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    name = excluded.name,
                    organization = excluded.organization,
                    homepage_url = excluded.homepage_url,
                    source_type = excluded.source_type,
                    authority_level = excluded.authority_level,
                    collection_method = excluded.collection_method,
                    enabled = excluded.enabled,
                    robots_reviewed_at = excluded.robots_reviewed_at,
                    terms_reviewed_at = excluded.terms_reviewed_at,
                    redistribution_notes = excluded.redistribution_notes,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                """,
                (
                    source.source_id,
                    source.name,
                    source.organization,
                    source.homepage_url,
                    source.source_type,
                    source.authority_level,
                    source.collection_method,
                    int(source.enabled),
                    source.robots_reviewed_at,
                    source.terms_reviewed_at,
                    source.redistribution_notes,
                ),
            )
            connection.execute(
                """
                INSERT INTO source_access_policies (
                    source_id, access_status, allowed_hosts_json, allowed_path_prefixes_json,
                    minimum_interval_seconds
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    access_status = excluded.access_status,
                    allowed_hosts_json = excluded.allowed_hosts_json,
                    allowed_path_prefixes_json = excluded.allowed_path_prefixes_json,
                    minimum_interval_seconds = excluded.minimum_interval_seconds,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                """,
                (
                    source.source_id,
                    source.access_status,
                    json.dumps(source.allowed_hosts, separators=(",", ":")),
                    json.dumps(source.allowed_path_prefixes, separators=(",", ":")),
                    source.minimum_interval_seconds,
                ),
            )
    return len(registry)
