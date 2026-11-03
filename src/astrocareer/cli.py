"""Command-line interface for AstroCareer Observatory."""

import argparse
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from astrocareer import __version__
from astrocareer.browser import serve_database
from astrocareer.collectors.capture import CaptureError, CaptureTransport, ReplayTransport
from astrocareer.collectors.fixture import FixtureTransport
from astrocareer.collectors.http import HTTPTransport, TransportError
from astrocareer.database import (
    connect_database,
    initialize_database,
    renormalize_source_observations,
    seed_demo_data,
)
from astrocareer.importers import import_ror_dump
from astrocareer.plugins import (
    PluginError,
    collector_plugin_references,
    get_collector_plugin,
)
from astrocareer.runner import CollectionBlocked, run_collection
from astrocareer.sources import load_source_registry, sync_source_registry


PROJECT_CONTACT_URL = "https://github.com/IffyZh/astrocareer-observatory"


def _collector_plugin(source_id: str, *, require_network: bool = False):
    plugin = get_collector_plugin(source_id)
    if require_network and not plugin.supports_network:
        raise PluginError(f"Collector plugin does not support network use: {source_id}")
    return plugin


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
    renormalize_parser = database_subparsers.add_parser(
        "renormalize-source",
        help="Rebuild candidates from saved observations without network access.",
    )
    renormalize_parser.add_argument("path", type=Path, help="Path to the SQLite database.")
    renormalize_parser.add_argument("source_id", help="Collector plugin source ID.")
    browse_parser = database_subparsers.add_parser(
        "browse",
        help="Open a local read-only web interface for the database.",
    )
    browse_parser.add_argument("path", type=Path, help="Path to the SQLite database.")
    browse_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Loopback TCP port (default: 8765; use 0 for an automatic port).",
    )
    browse_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Start the service without opening the system browser.",
    )
    plugins_parser = subparsers.add_parser(
        "plugins", help="List and inspect collector plugins."
    )
    plugin_subparsers = plugins_parser.add_subparsers(dest="plugin_command")
    plugin_subparsers.add_parser(
        "list", help="List built-in and installed collector plugin names."
    )
    inspect_parser = plugin_subparsers.add_parser(
        "inspect", help="Load and inspect one collector plugin."
    )
    inspect_parser.add_argument("source_id", help="Registered plugin source ID.")
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
    elif args.command == "db" and args.database_command == "renormalize-source":
        try:
            plugin = _collector_plugin(args.source_id)
        except PluginError as error:
            parser.error(str(error))
        initialize_database(args.path)
        with connect_database(args.path) as connection:
            report = renormalize_source_observations(
                connection,
                source_id=args.source_id,
                normalizer_version=plugin.normalizer_version,
            )
        print(
            f"renormalized: source={report.source_id} "
            f"version={report.normalizer_version} "
            f"observations={report.observation_count} "
            f"inserted={report.inserted_count} reused={report.reused_count} "
            f"superseded={report.superseded_count}"
        )
    elif args.command == "db" and args.database_command == "browse":
        if not 0 <= args.port <= 65535:
            parser.error("Port must be between 0 and 65535")
        try:
            serve_database(
                args.path,
                port=args.port,
                open_browser=not args.no_open,
            )
        except (FileNotFoundError, OSError, sqlite3.Error) as error:
            parser.error(str(error))
    elif args.command == "plugins" and args.plugin_command == "list":
        try:
            references = collector_plugin_references()
        except PluginError as error:
            parser.error(str(error))
        for source_id, reference in references.items():
            print(f"{source_id}\t{reference.origin}")
    elif args.command == "plugins" and args.plugin_command == "inspect":
        try:
            references = collector_plugin_references()
            reference = references[args.source_id]
            plugin = reference.load()
        except (KeyError, PluginError) as error:
            parser.error(str(error))
        print(f"source_id={plugin.source_id}")
        print(f"origin={reference.origin}")
        print(f"api_version={plugin.api_version}")
        print(f"collector_version={plugin.collector_version}")
        print(f"normalizer_version={plugin.normalizer_version}")
        print(f"fixture_content_type={plugin.fixture_content_type}")
        print(f"max_response_bytes={plugin.max_response_bytes}")
        print(f"supports_network={'yes' if plugin.supports_network else 'no'}")
    elif args.command == "collect-fixture":
        try:
            plugin = _collector_plugin(args.source_id)
            collector = plugin.create_collector()
        except PluginError as error:
            parser.error(str(error))
        initialize_database(args.database)
        registry = load_source_registry(args.registry)
        source = registry[args.source_id]
        transport = FixtureTransport(
            args.fixture,
            content_type=plugin.fixture_content_type,
        )
        with connect_database(args.database) as connection:
            if not args.dry_run:
                sync_source_registry(connection, registry)
            report = run_collection(
                connection,
                source=source,
                collector=collector,
                transport=transport,
                collector_version=plugin.collector_version,
                normalizer_version=plugin.normalizer_version,
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
            plugin = _collector_plugin(args.source_id, require_network=True)
            collector = plugin.create_collector()
        except PluginError as error:
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
                max_response_bytes=plugin.max_response_bytes,
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
                    collector_version=plugin.collector_version,
                    normalizer_version=plugin.normalizer_version,
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
            plugin = _collector_plugin(args.source_id, require_network=True)
            collector = plugin.create_collector()
        except PluginError as error:
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
                    collector_version=plugin.collector_version,
                    normalizer_version=plugin.normalizer_version,
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
