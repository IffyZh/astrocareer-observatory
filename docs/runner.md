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

The reviewed Planetary Research Jobs feed can be fetched without writing data:

```bash
PYTHONPATH=src python3 -m astrocareer collect \
  planetary-research-jobs-feed \
  --database data/local/astrocareer.sqlite3 \
  --registry data/sources.toml \
  --dry-run
```

The production command uses the restricted `HTTPTransport`, does not expose the fixture-only disabled-source override, and enforces the source's saved minimum interval. A network dry run writes only the synchronized source registry and a minimal access-audit timestamp, so repeated dry runs cannot bypass that interval; it does not save response snapshots, source records, or normalization candidates. Remove `--dry-run` only after inspecting a successful live result; the persisted run stores provenance and normalization candidates for manual review, not accepted public job records.

## Local capture and offline replay

Save one network response while running a normal collection:

```bash
PYTHONPATH=src python3 -m astrocareer collect \
  planetary-research-jobs-feed \
  --database data/local/astrocareer.sqlite3 \
  --registry data/sources.toml \
  --capture-local data/local/captures/planetary-2026-11-03.capture.zip
```

The capture is an immutable ZIP containing the response bytes and a small manifest with its URL, observation time, HTTP metadata, and SHA-256 digest. Existing captures are never overwritten. Captures may contain third-party text or personal data, so keep them under the Git-ignored `data/local/` directory and do not publish them without a separate rights review.

Replay the captured response as often as needed without network access or source rate-limit accounting:

```bash
PYTHONPATH=src python3 -m astrocareer replay-capture \
  planetary-research-jobs-feed \
  data/local/captures/planetary-2026-11-03.capture.zip \
  --database data/local/replay.sqlite3 \
  --registry data/sources.toml \
  --dry-run
```

Omit `--dry-run` only when a persisted offline replay is intentionally needed. Prefer a separate replay database so parser experiments do not mix with the primary observation history.
