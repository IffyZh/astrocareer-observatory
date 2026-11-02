# Documentation

[简体中文](README.zh-CN.md)

AstroCareer Observatory documentation will grow alongside the implementation. Planned topics include:

- the data model and data dictionary;
- provenance and evidence rules;
- source review and collector development;
- collection ethics, copyright, and privacy;
- local usage and public data exports;
- methodology, coverage, and known limitations.

The repository root [README](../README.md) is the current project contract.

Project-wide governance documents live at the repository root:

- [Security policy](../SECURITY.md)
- [Data rights and publication policy](../DATA_RIGHTS.md)
- [Apache License 2.0](../LICENSE)

## Current design documents

- [Data model v0.1](data-model.md)
- [Collector contract](collectors.md)
- [Normalization and review](normalization.md)
- [Collection runner](runner.md)
- [Restricted HTTP transport](http-transport.md)
- [Source review template](source-review-template.md)

## Reviewed real sources

- [AAS Job Register](source-reviews/aas-job-register.md) — permission required; automated access blocked
- [Planetary Research Jobs Atom feed](source-reviews/planetary-research-jobs.md) — feed adapter validated; disabled pending a project contact URL
- [Research Organization Registry data dump](source-reviews/ror-data-dump.md) — CC0 offline institution import approved and implemented
