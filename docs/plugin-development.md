# Collector plugin development

[简体中文](plugin-development.zh-CN.md)

Collector plugins adapt one reviewed source to the stable `SourcePosting` contract. Core code retains control of network policy, rate limits, local capture, normalization orchestration, database transactions, and review status.

## Package shape

An external adapter can live in its own installable Python package:

```text
astrocareer-collector-example/
├── pyproject.toml
├── src/astrocareer_collector_example/
│   ├── __init__.py
│   ├── collector.py
│   └── plugin.py
├── tests/
│   └── test_collector.py
├── fixtures/
└── SOURCE_REVIEW.md
```

The collector implements the shared protocol and uses only the supplied `Transport` for network requests:

```python
from astrocareer.collectors import CollectionBatch, RequestSpec, Transport


class ExampleCollector:
    source_id = "example-source"

    def collect(self, transport: Transport, checkpoint=None) -> CollectionBatch:
        snapshot = transport.fetch(
            RequestSpec(
                source_id=self.source_id,
                url="https://jobs.example.org/feed",
                purpose="job_listing_feed",
            )
        )
        return self.parse(snapshot)
```

Expose one versioned descriptor from `plugin.py`:

```python
from astrocareer.plugins import CollectorPlugin

from .collector import ExampleCollector


plugin = CollectorPlugin(
    source_id=ExampleCollector.source_id,
    collector_factory=ExampleCollector,
    collector_version="example-feed-1",
    normalizer_version="rules-1",
    fixture_content_type="application/atom+xml; charset=utf-8",
    max_response_bytes=2_000_000,
    supports_network=True,
)
```

Register that object through a Python entry point:

```toml
[project.entry-points."astrocareer.collectors"]
example-source = "astrocareer_collector_example.plugin:plugin"
```

The entry-point name, descriptor `source_id`, collector `source_id`, and reviewed `sources.toml` ID must be identical. Duplicate IDs, API mismatches, and identity mismatches fail closed.

## Source policy remains separate

Installing a plugin does not authorize collection. Add and review a matching source definition separately, including its allowed hosts and paths, access status, minimum interval, and redistribution notes. Both `supports_network=True` and an enabled, approved source definition are required for production HTTP access.

Plugins receive the restricted core `Transport`; they should never call `urllib`, `requests`, sockets, browser automation, or subprocesses directly. Python plugins are executable code and are not sandboxed, so automated deployments must install only reviewed packages at pinned versions.

## Versions and tests

- Increment `collector_version` when extraction behavior changes in a way that affects stored source records.
- Change `normalizer_version` only when the selected normalization rules change.
- Keep fixtures minimized and free of unnecessary personal or copyrighted text.
- Test a normal response, an explicitly empty response, malformed records, duplicate source IDs, and layout drift.
- Parsing the same immutable snapshot must always produce the same batch.
- Do not make network requests in tests.

Inspect installed registrations with:

```bash
PYTHONPATH=src python3 -m astrocareer plugins list
PYTHONPATH=src python3 -m astrocareer plugins inspect example-source
```

`plugins list` discovers entry-point names without importing external plugin modules. `plugins inspect`, collection, and replay load only the selected plugin.
