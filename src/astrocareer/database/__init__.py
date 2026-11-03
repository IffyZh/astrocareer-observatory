"""SQLite storage for AstroCareer Observatory."""

from astrocareer.database.access import record_source_access_attempt
from astrocareer.database.core import (
    SelectionMetrics,
    calculate_selection_metrics,
    connect_database,
    get_schema_version,
    initialize_database,
)
from astrocareer.database.collection import persist_collection_batch
from astrocareer.database.demo import DEMO_POSTING_ID, DEMO_ROUND_ID, seed_demo_data
from astrocareer.database.github_sync import (
    DEFAULT_ARTIFACT,
    DEFAULT_REPOSITORY,
    GitHubArtifactSyncError,
    GitHubSyncReport,
    sync_github_database,
)
from astrocareer.database.normalization import persist_normalization_candidate
from astrocareer.database.renormalization import (
    RenormalizationReport,
    renormalize_source_observations,
)

__all__ = [
    "DEFAULT_ARTIFACT",
    "DEFAULT_REPOSITORY",
    "SelectionMetrics",
    "DEMO_POSTING_ID",
    "DEMO_ROUND_ID",
    "calculate_selection_metrics",
    "connect_database",
    "get_schema_version",
    "GitHubArtifactSyncError",
    "GitHubSyncReport",
    "initialize_database",
    "persist_collection_batch",
    "persist_normalization_candidate",
    "RenormalizationReport",
    "renormalize_source_observations",
    "record_source_access_attempt",
    "seed_demo_data",
    "sync_github_database",
]
