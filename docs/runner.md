# Collection runner

[简体中文](runner.zh-CN.md)

The runner is the only supported path from a collector to persisted source records and normalization candidates.

## Pipeline

```text
validate source and collector identity
-> check enabled state and minimum interval
-> restore the latest checkpoint
-> collect through a Transport
-> normalize valid source records
-> persist the batch and pending candidates in one transaction
-> return a structured report
```

The runner never accepts candidates into formal posting tables.

## Safety gates

- Collector and source registry IDs must match.
- Disabled sources are blocked by default.
- The source-specific minimum interval is enforced from persisted run history.
- Failed batches contain no records or normalization candidates.
- Batch persistence and candidate persistence share one transaction.
- A timezone-aware clock is required.
- Fixture-only overrides are explicit and are not production defaults.

## Offline dry run

The current CLI can exercise the demo collector against a local fixture:

```bash
PYTHONPATH=src python3 -m astrocareer collect-fixture \
  demo-html-source tests/fixtures/demo_source/normal.html \
  --database data/local/astrocareer.sqlite3 \
  --registry data/sources.toml \
  --dry-run
```

Dry-run mode parses and normalizes records but does not create collection runs, snapshots, source-record observations, or candidates.

Omitting `--dry-run` persists the offline fixture result. This command still uses `FixtureTransport`, which only reads the named local file and cannot access the network.

## Production boundary

No production network transport or real-source collector is enabled yet. A future production command must not expose the fixture-only disabled-source override.

