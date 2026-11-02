# Source review: Research Organization Registry data dump

[简体中文](ror-data-dump.zh-CN.md)

## 1. Identity and purpose

- Source ID: `ror-data-dump`
- Public name: Research Organization Registry (ROR) data dump
- Owning initiative: Research Organization Registry
- Registry: <https://ror.org/registry>
- Data dump documentation: <https://ror.readme.io/docs/data-dump>
- Proposed use: seed stable identities, names, domains, organization types, and locations for research organizations
- Review date: 2026-11-01
- Next mandatory review date: 2027-05-01 or before adopting a new major ROR schema

## 2. Supported access method

ROR publishes versioned full JSON data dumps through Zenodo and a REST API for individual lookup. ROR documentation explicitly recommends the data dump when the full registry is required. AstroCareer Observatory imports a user-supplied, extracted JSON dump; automatic downloading is outside this initial approval.

## 3. Rights and terms

- ROR terms: <https://ror.org/about/terms/>
- Schema fields: <https://ror.readme.io/docs/fields>
- Review date: 2026-11-01

ROR IDs and registry metadata are dedicated to the public domain under CC0 1.0. ROR website content and logos have separate terms; the importer does not collect logos or copy website prose.

## 4. Explicit decision

- [x] `approved`
- [ ] `manual_only`
- [ ] `api_only`
- [ ] `permission_required`
- [ ] `prohibited`
- [ ] `pending_review`

Approved scope: offline import of official ROR Schema 2.x JSON data dumps. The import must retain the stated dataset version and a SHA-256 hash. It does not authorize crawling the organizations listed in ROR.

## 5. Imported fields

- ROR ID and record status;
- display name, labels, aliases, and acronyms;
- official domains and website link;
- organization types;
- establishment year;
- GeoNames-based location metadata;
- ROR record creation and modification dates.

Relationships and external identifiers are not imported in the first implementation. Their absence must not be interpreted as absence in ROR.

## 6. Safety and update behavior

- Only Schema 2.x records are accepted.
- An import is atomic: one invalid record rolls back the entire snapshot.
- Duplicate ROR IDs fail the import.
- Re-importing identical bytes reuses the recorded import run.
- Removed domains are retained as inactive history rather than deleted.
- A record is never marked inactive merely because it is absent from a later input file; only explicit ROR status values are trusted.
- Import collection sources are blocked from using the HTTP transport.

## 7. Personal data

ROR describes organizations rather than applicants. The selected fields do not contain applicant profiles or contact information. No email addresses or named contacts are imported.

## 8. Implementation result

The importer is validated with synthetic Schema 2.1 fixtures for initial import, repeat import, record updates, domain retirement, and atomic rollback. A full official ROR dump has not yet been downloaded or imported.
