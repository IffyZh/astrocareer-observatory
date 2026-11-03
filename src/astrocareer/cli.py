"""Command-line interface for AstroCareer Observatory."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from astrocareer import __version__
from astrocareer.collectors.capture import CaptureError, CaptureTransport, ReplayTransport
from astrocareer.collectors.demo import DemoCollector
from astrocareer.collectors.fixture import FixtureTransport
from astrocareer.collectors.http import HTTPTransport, TransportError
from astrocareer.collectors.planetary_research import PlanetaryResearchFeedCollector
from astrocareer.database import connect_database, initialize_database, seed_demo_data
from astrocareer.importers import import_ror_dump
from astrocareer.runner import CollectionBlocked, run_collection
from astrocareer.sources import load_source_registry, sync_source_registry


PROJECT_CONTACT_URL = "https://github.com/IffyZh/astrocareer-observatory"


def _fixture_collector(source_id: str):
    collectors = {
        DemoCollector.source_id: (DemoCollector(), "text/html; charset=utf-8", "demo-1"),
        PlanetaryResearchFeedCollector.source_id: (
            PlanetaryResearchFeedCollector(),
            "application/atom+xml; charset=utf-8",
            "planetary-research-feed-1",
        ),
    }
    try:
        return collectors[source_id]
    except KeyError as error:
        raise ValueError(f"No fixture collector is registered for {source_id}") from error


def _network_collector(source_id: str):
    collectors = {
        PlanetaryResearchFeedCollector.source_id: (
            PlanetaryResearchFeedCollector(),
            "planetary-research-feed-1",
            2_000_000,
        ),
    }
    try:
        return collectors[source_id]
    except KeyError as error:
        raise ValueError(f"No production collector is registered for {source_id}") from error


def build_parser() -> argparse.ArgumentParser:
    """Build the project command-line parser."""
    parser = argparse.ArgumentParser(
        prog="astrocareer",
        description="Observe the astronomy and astrophysics job market.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    database_parser = subparsers.add_parser("db", help="Manage a local database.")
    database_subparsers = database_parser.add_subparsers(dest="database_command")
    init_parser = database_subparsers.add_parser("init", help="Initialize a database.")
    init_parser.add_argument("path", type=Path, help="Path to the SQLite database.")
    seed_parser = database_subparsers.add_parser(
        "seed-demo", help="Load the fictional demonstration dataset."
    )
    seed_parser.add_argument("path", type=Path, help="Path to the SQLite database.")
    sync_parser = database_subparsers.add_parser(
        "sync-sources", help="Synchronize a reviewed TOML source registry."
    )
    sync_parser.add_argument("path", type=Path, help="Path to the SQLite database.")
    sync_parser.add_argument("registry", type=Path, help="Path to sources.toml.")
    ror_parser = database_subparsers.add_parser(
        "import-ror", help="Import an official local ROR Schema 2.x JSON data dump."
    )
    ror_parser.add_argument("path", type=Path, help="Path to the SQLite database.")
    ror_parser.add_argument("dump", type=Path, help="Path to the extracted ROR JSON dump.")
    ror_parser.add_argument("--dataset-version", required=True)
    ror_parser.add_argument("--registry", required=True, type=Path)
    fixture_parser = subparsers.add_parser(
        "collect-fixture",
        help="Run a collector against a local fixture without network access.",
    )
    fixture_parser.add_argument("source_id", help="Registered source ID.")
    fixture_parser.add_argument("fixture", type=Path, help="Local source fixture.")
    fixture_parser.add_argument("--database", required=True, type=Path)
    fixture_parser.add_argument("--registry", required=True, type=Path)
    fixture_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and normalize without writing collection data.",
    )
    collect_parser = subparsers.add_parser(
        "collect",
        help="Collect one reviewed and enabled network source.",
    )
    collect_parser.add_argument("source_id", help="Registered source ID.")
    collect_parser.add_argument("--database", required=True, type=Path)
    collect_parser.add_argument("--registry", required=True, type=Path)
    collect_parser.add_argument(
        "--contact-url",
        default=PROJECT_CONTACT_URL,
        help="Public HTTPS project contact URL sent in the User-Agent.",
    )
    collect_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch, parse, and normalize without writing collection data.",
    )
    collect_parser.add_argument(
        "--capture-local",
        type=Path,
        help="Save the response in an immutable local capture for offline replay.",
    )
    replay_parser = subparsers.add_parser(
        "replay-capture",
        help="Replay a local response capture without network access.",
    )
    replay_parser.add_argument("source_id", help="Registered source ID.")
    replay_parser.add_argument("capture", type=Path, help="Local .capture.zip file.")
    replay_parser.add_argument("--database", required=True, type=Path)
    replay_parser.add_argument("--registry", required=True, type=Path)
    replay_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and normalize without writing collection data.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "db" and args.database_command == "init":
        version = initialize_database(args.path)
        print(f"Initialized {args.path} with schema version {version}.")
    elif args.command == "db" and args.database_command == "seed-demo":
        initialize_database(args.path)
        with connect_database(args.path) as connection:
            inserted = seed_demo_data(connection)
        if inserted:
            print(f"Loaded fictional demonstration data into {args.path}.")
        else:
            print(f"Fictional demonstration data already exists in {args.path}.")
    elif args.command == "db" and args.database_command == "sync-sources":
        initialize_database(args.path)
        registry = load_source_registry(args.registry)
        with connect_database(args.path) as connection:
            count = sync_source_registry(connection, registry)
        print(f"Synchronized {count} source definition(s) into {args.path}.")
    elif args.command == "db" and args.database_command == "import-ror":
        initialize_database(args.path)
        registry = load_source_registry(args.registry)
        with connect_database(args.path) as connection:
            sync_source_registry(connection, registry)
            report = import_ror_dump(
                connection,
                args.dump,
                dataset_version=args.dataset_version,
            )
        disposition = "reused" if report.reused_existing_run else "imported"
        print(
            f"ROR {disposition}: version={report.dataset_version} "
            f"records={report.record_count} inserted={report.inserted_count} "
            f"updated={report.updated_count} sha256={report.content_sha256}"
        )
    elif args.command == "collect-fixture":
        try:
            collector, content_type, collector_version = _fixture_collector(args.source_id)
        except ValueError as error:
            parser.error(str(error))
        initialize_database(args.database)
        registry = load_source_registry(args.registry)
        source = registry[args.source_id]
        transport = FixtureTransport(args.fixture, content_type=content_type)
        with connect_database(args.database) as connection:
            if not args.dry_run:
                sync_source_registry(connection, registry)
            report = run_collection(
                connection,
                source=source,
                collector=collector,
                transport=transport,
                collector_version=collector_version,
                normalizer_version="rules-1",
                dry_run=args.dry_run,
                allow_disabled=True,
                enforce_interval=False,
            )
        mode = "dry-run" if args.dry_run else "persisted"
        print(
            f"{mode}: status={report.collection_status.value} "
            f"records={report.record_count} issues={report.issue_count} "
            f"candidates={report.candidate_count}"
        )
    elif args.command == "collect":
        try:
            collector, collector_version, max_response_bytes = _network_collector(
                args.source_id
            )
        except ValueError as error:
            parser.error(str(error))
        initialize_database(args.database)
        registry = load_source_registry(args.registry)
        try:
            source = registry[args.source_id]
        except KeyError:
            parser.error(f"Source is not registered: {args.source_id}")
        try:
            transport = HTTPTransport(
                source,
                contact_url=args.contact_url,
                max_response_bytes=max_response_bytes,
            )
            if args.capture_local is not None:
                transport = CaptureTransport(transport, args.capture_local)
        except (CaptureError, ValueError) as error:
            parser.error(str(error))
        with connect_database(args.database) as connection:
            sync_source_registry(connection, registry)
            try:
                report = run_collection(
                    connection,
                    source=source,
                    collector=collector,
                    transport=transport,
                    collector_version=collector_version,
                    normalizer_version="rules-1",
                    dry_run=args.dry_run,
                    record_network_access=True,
                    contact_url=args.contact_url,
                )
            except (CaptureError, CollectionBlocked, TransportError) as error:
                parser.error(str(error))
        mode = "dry-run" if args.dry_run else "persisted"
        print(
            f"{mode}: source={report.source_id} "
            f"status={report.collection_status.value} "
            f"records={report.record_count} issues={report.issue_count} "
            f"candidates={report.candidate_count}"
        )
        if args.capture_local is not None:
            print(f"capture={args.capture_local}")
    elif args.command == "replay-capture":
        try:
            collector, collector_version, _ = _network_collector(args.source_id)
        except ValueError as error:
            parser.error(str(error))
        initialize_database(args.database)
        registry = load_source_registry(args.registry)
        try:
            source = registry[args.source_id]
        except KeyError:
            parser.error(f"Source is not registered: {args.source_id}")
        transport = ReplayTransport(args.capture)
        with connect_database(args.database) as connection:
            if not args.dry_run:
                sync_source_registry(connection, registry)
            try:
                report = run_collection(
                    connection,
                    source=source,
                    collector=collector,
                    transport=transport,
                    collector_version=collector_version,
                    normalizer_version="rules-1",
                    dry_run=args.dry_run,
                    allow_disabled=True,
                    enforce_interval=False,
                )
            except CaptureError as error:
                parser.error(str(error))
        mode = "dry-run" if args.dry_run else "persisted"
        print(
            f"replay-{mode}: source={report.source_id} "
            f"status={report.collection_status.value} "
            f"records={report.record_count} issues={report.issue_count} "
            f"candidates={report.candidate_count}"
        )
    return 0
