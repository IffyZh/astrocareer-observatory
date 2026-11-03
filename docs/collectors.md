# Collector contract

[简体中文](collectors.zh-CN.md)

Collectors translate one external source into source-faithful records. They do not write to SQLite, deduplicate records across sources, infer missing facts, or assess immigration difficulty.

## Boundary

The shared flow is:

```text
Collector -> RequestSpec -> Transport -> RawSnapshot
          -> SourcePosting + ParseIssue -> CollectionBatch
          -> normalization and persistence (separate components)
```

`Transport` is the only permitted network boundary. Tests replace it with an in-memory implementation, so collector tests never access the internet.

## Required behavior

Every collector must:

- expose a stable `source_id`;
- issue requests through `Transport` only;
- preserve source record IDs, URLs, original date text, requirements, and skills;
- return immutable snapshots with verified SHA-256 hashes;
- distinguish explicit empty listings from unrecognized page structures;
- report structured issues instead of silently dropping malformed records;
- return no persistable records when the batch status is `failed`;
- produce deterministic output for the same snapshot.

## Batch statuses

| Status | Meaning |
|---|---|
| `success` | The source was understood and every returned record is valid. An explicitly empty source may be successful. |
| `partial` | At least one valid record and at least one record-level error were found. |
| `not_modified` | The transport confirms that the source has not changed. |
| `failed` | The response or page structure cannot be trusted. No records may be persisted. |

## Adding a source

1. Register and review the source before enabling collection.
2. Implement a built-in or external collector plugin using the [plugin development guide](plugin-development.md).
3. Add minimized local fixtures under `tests/fixtures/<source_id>/`.
4. Test a normal page, an explicit empty page, malformed records, and layout drift.
5. Verify stable source IDs and canonical URLs.
6. Document any fields that cannot be extracted reliably.
7. Keep the source disabled until robots, terms, rate limits, and redistribution constraints are recorded.

## Parser rules

- Preserve official text before normalization.
- Do not turn “preferred” into “required.”
- Do not invent dates, time zones, applicant counts, sponsorship, or contract conditions.
- A missing statement is `not_reported`, not a negative statement.
- A temporary listing disappearance is not proof that a posting was withdrawn.
- A zero-result parse is an error unless the source explicitly communicates that its listing is empty.

## Current implementation

`DemoCollector` and `PlanetaryResearchFeedCollector` are built-in plugins using the same API exposed to external packages. `DemoCollector` and its `.test` fixtures prove the contract without making network requests. `PlanetaryResearchFeedCollector` is the first reviewed real-source adapter. It reads only the official Atom feed, accepts at most 1,000 entries, validates feed and entry identity, rejects DTD/entity declarations, and discards full descriptions, contact details, and poster ORCID identifiers.

The real source is enabled for explicit command-line runs and uses the public repository as its contact URL. Its parser has been validated against synthetic fixtures and a local live-feed capture; live responses are not committed to the repository.
