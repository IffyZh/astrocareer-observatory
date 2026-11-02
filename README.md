# AstroCareer Observatory

[简体中文](README.zh-CN.md)

> A traceable, open database for observing the astronomy and astrophysics job market over time.

AstroCareer Observatory is a pre-alpha project for collecting, normalizing, and preserving public information about jobs in astronomy, astrophysics, research software, scientific computing, and research infrastructure.

The project is intended first as a practical tool for personal career research. Its code, methodology, and redistributable datasets will be developed in public so that other people can inspect, use, and maintain them.

## Why this project exists

Job boards are useful for finding current openings, but they rarely preserve a complete and reproducible history. They also use inconsistent terminology for contracts, job families, eligibility, skills, and application deadlines.

This project aims to build a longitudinal dataset that can support questions such as:

- How many relevant positions are advertised over time?
- Which countries and institutions advertise permanent or long-term roles?
- Which technical and research skills occur most often?
- Which positions are open to international applicants or provide visa support?
- Where official evidence exists, how many people applied, interviewed, or were hired?
- How does the observed coverage of each source affect apparent market trends?

## Project principles

### Traceability before quantity

Important facts should retain their source URL, observation time, content hash, parser version, and verification status. Missing information must remain missing rather than being inferred without evidence.

### Preserve history

The database should distinguish publication time from the first and last time the project observed a posting. Updates, withdrawals, expirations, and other state changes should be recorded as events instead of silently overwriting history.

### Separate observations from interpretation

Source text, normalized fields, manual classifications, and analytical conclusions are different things. The data model should preserve those distinctions.

### Be explicit about coverage

The number of observed postings depends on which sources were monitored and whether their collectors were working. Coverage changes must be recorded so that they are not mistaken for changes in the job market.

### Minimize personal data

The public project is about positions and aggregate market evidence, not public profiles of applicants. It will not automatically aggregate named applicant histories. Personal job-search notes, applications, rankings, contacts, and private assessments belong in a separate private layer.

### Collect responsibly

Each source must be reviewed before automated collection. Official APIs, feeds, and other explicitly supported access methods are preferred. Robots policies, terms, rate limits, copyright, and redistribution restrictions must be respected.

## Intended public data

Subject to source-specific permissions, the public dataset may include:

- job title, category, institution, and location;
- publication, deadline, and observation timestamps;
- contract type and duration when explicitly stated;
- salary, language, eligibility, and visa information when available;
- research and technical skill requirements;
- links and provenance metadata;
- documented posting status changes;
- officially supported aggregate competition statistics.

The presence of a value in a source does not automatically mean that its full original text may be republished. Code licensing and third-party data rights will be handled separately.

## Out of scope for the first version

- automated public profiles of named applicants or successful candidates;
- inferred applicant counts based on rumor pages or incomplete public lists;
- a personal probability score presented as an objective prediction;
- high-frequency crawling or bypassing access restrictions;
- claiming comprehensive global coverage.

## Planned first milestone

The first milestone will provide:

1. a documented data model for sources, postings, observations, evidence, and events;
2. a local SQLite database;
3. a command-line workflow that imports a test fixture and exports a small public dataset;
4. automated validation and tests;
5. one reviewed, maintainable real-world collector.

## Status

**Pre-alpha.** There is no released dataset or scheduled collection yet. One reviewed Atom-feed source is enabled for explicit command-line runs, and an offline ROR institution importer is implemented.

Interfaces, schemas, and repository layout may change before the first tagged release.

## Local database quick start

From a source checkout, initialize an empty schema-v8 SQLite database with:

```bash
PYTHONPATH=src python3 -m astrocareer db init data/local/astrocareer.sqlite3
```

The command creates parent directories when needed, enables foreign-key checks, applies packaged migrations, and runs SQLite's integrity check. Local `*.sqlite3` files are ignored by Git by default.

A freshly initialized database is empty by design. Reviewed source definitions and datasets are synchronized or imported explicitly.

Load the explicitly fictional demonstration dataset with:

```bash
PYTHONPATH=src python3 -m astrocareer db seed-demo data/local/astrocareer.sqlite3
```

The command is idempotent. Demo organizations, policies, and `.test` URLs are not real and must not be used for market analysis.

Synchronize reviewed source definitions with:

```bash
PYTHONPATH=src python3 -m astrocareer db sync-sources \
  data/local/astrocareer.sqlite3 data/sources.toml
```

Network collection sources remain disabled until explicitly reviewed and enabled. Approved offline imports may be enabled without granting network access.

After downloading and extracting an official ROR Schema 2.x JSON data dump, import its institution records with:

```bash
PYTHONPATH=src python3 -m astrocareer db import-ror \
  data/local/astrocareer.sqlite3 /path/to/ror-data.json \
  --dataset-version vX.Y-YYYY-MM-DD \
  --registry data/sources.toml
```

The import is idempotent by file hash and records the dataset version. ROR import does not crawl any institution website.

Run the demo collector against a local fixture without writing data:

```bash
PYTHONPATH=src python3 -m astrocareer collect-fixture \
  demo-html-source tests/fixtures/demo_source/normal.html \
  --database data/local/astrocareer.sqlite3 \
  --registry data/sources.toml \
  --dry-run
```

## Documentation languages

Project-facing documentation will be maintained in English and Simplified Chinese. English is the default language for code, schema identifiers, commit messages, and issue labels so that the repository remains accessible to an international contributor community.

## Contributing

Contribution instructions will be added after the initial data model and development workflow are established. Early discussion should focus on scope, data provenance, source permissions, schema design, and reproducible tests.

## License and data rights

Original project software, tests, configuration, schema, and project-authored documentation are licensed under the [Apache License 2.0](LICENSE), unless a file states otherwise. See the [security policy](SECURITY.md) for private vulnerability reporting and [data-rights policy](DATA_RIGHTS.md) for publication restrictions.

No general open-data license is currently granted for collected records or database exports. The software license does not imply ownership of, or permission to relicense, third-party job advertisements and source material.
