"""SQLite storage for AstroCareer Observatory."""

from astrocareer.database.core import (
    SelectionMetrics,
    calculate_selection_metrics,
    connect_database,
    get_schema_version,
    initialize_database,
)
from astrocareer.database.collection import persist_collection_batch
from astrocareer.database.demo import DEMO_POSTING_ID, DEMO_ROUND_ID, seed_demo_data
from astrocareer.database.normalization import persist_normalization_candidate

__all__ = [
    "SelectionMetrics",
    "DEMO_POSTING_ID",
    "DEMO_ROUND_ID",
    "calculate_selection_metrics",
    "connect_database",
    "get_schema_version",
    "initialize_database",
    "persist_collection_batch",
    "persist_normalization_candidate",
    "seed_demo_data",
]
