# Source review: Planetary Research Jobs Atom feed

[简体中文](planetary-research-jobs.zh-CN.md)

## 1. Identity and purpose

- Source ID: `planetary-research-jobs-feed`
- Public name: Planetary Research Jobs
- Owning organization: Planetary Research Cooperative
- Homepage: <https://jobs.planetary-research.org/>
- Proposed use: discover planetary-science jobs through the site's supported Atom feed
- Proposed maintainer: AstroCareer Observatory contributors
- Review date: 2026-11-01
- Next mandatory review date: 2027-05-01, or earlier if the feed, policy, or ownership changes

## 2. Supported access methods

- [ ] Official API
- [x] RSS or Atom feed
- [x] Email subscription
- [ ] Downloadable dataset
- [x] Public HTML pages
- [ ] Manual collection only

Preferred method: the official all-jobs Atom feed at <https://jobs.planetary-research.org/feed>. The site's FAQ explicitly offers it for use in feed readers, so it is less intrusive and more stable than HTML scraping.

## 3. Robots and terms

- Robots URL: <https://jobs.planetary-research.org/robots.txt>
- Robots retrieval date: 2026-11-01
- Robots result: no robots file was served; the application returned its ordinary “Job announcement not found” page
- Feed documentation: <https://jobs.planetary-research.org/faq#feeds>
- Privacy policy: <https://jobs.planetary-research.org/privacy>
- Review date: 2026-11-01

No separate terms-of-use or dataset license was identified in the public site navigation during this review. Absence of a license is not permission to republish feed content. The approval below covers restrained access to the explicitly offered feed, not wholesale redistribution.

The feed and public listings require no account. Authentication is not permitted for this collector.

## 4. Explicit access decision

- [x] `approved`
- [ ] `manual_only`
- [ ] `api_only`
- [ ] `permission_required`
- [ ] `prohibited`
- [ ] `pending_review`

One unauthenticated GET of the documented all-jobs Atom feed is approved, no more frequently than every six hours. HTML listing and detail pages are outside this approval. The source remains disabled in the registry until implementation review and a public project contact URL are complete.

Reviewer: AstroCareer Observatory project review

Decision date: 2026-11-01

## 5. Technical boundaries

- Exact allowed host: `jobs.planetary-research.org`
- Allowed path: `/feed` only
- Minimum interval: 21,600 seconds (six hours)
- Maximum requests per run: one
- Expected type: `application/atom+xml` or another XML media type
- Observed response size on 2026-11-01: approximately 1.25 MB
- Maximum accepted response size: 2 MB
- Pagination: none observed; the feed represents current visible announcements
- Stable identifier: the Atom entry `id`, matching the site's announcement URL
- Project contact URL: required before enabling live requests

Conditional GET validators should be used when the server provides `ETag` or `Last-Modified`.

## 6. Evidence retention and publication

- Full responses: may be held transiently for parsing; raw bytes are not committed or stored by the current database layer
- Public fixtures: synthetic only
- Full job descriptions: do not publish or commit
- Short evidence excerpts: only when necessary and separately reviewed
- Normalized facts: title, institution, location, dates, category, employment terms, source URL, and observation metadata may be retained with attribution
- Source URLs and hashes: may be published
- Required attribution: name Planetary Research Jobs and link to the original announcement
- Deletion/correction: stop publishing a disputed record while reviewing a request; retain an internal provenance event rather than silently rewriting history

The feed's “Inquiries” contact details and “Posted by” ORCID identifiers are deliberately discarded. Official external announcement URLs may be retained as provenance, but following those URLs requires a separate source review.

## 7. Personal-data assessment

Feed content can contain contact names, email addresses, ORCID identifiers, and names embedded in descriptions. None is required for the initial market database. The collector parses only an allowlist of non-contact summary fields and must not copy the full description into a normalized record.

## 8. Failure and monitoring plan

- Explicit empty marker: a structurally valid Atom feed with identity metadata and zero entries
- Expected count: zero or more current announcements; establish a normal range after initial monitored runs
- Fail on: wrong root namespace, wrong feed identity, malformed XML, response over 2 MB, unexpected media type, unsafe redirect, or every entry being malformed
- Partial result: retain valid entries and emit structured errors for malformed or duplicate entries
- Suspend automatically on: policy change, repeated structure failures, unexpected authentication, or host/path change
- Manual shutdown: set `enabled = false` in `data/sources.toml`

## 9. Approval checklist

- [x] Access method is the least intrusive supported option.
- [x] Robots, FAQ, and privacy policy have been reviewed and linked.
- [x] Access decision is explicit.
- [x] Allowed host, path, request count, and interval are recorded.
- [x] Retention and redistribution rules are recorded.
- [x] Personal-data handling is documented.
- [x] Normal, empty, malformed, and layout-change fixtures pass.
- [x] No credential is required.
- [x] Source remains disabled until implementation review is complete.
- [ ] A public project contact URL is configured.

## 10. Final notes

This review approves feed access, not republication of feed content and not crawling official employer links. Re-review before expanding the collected fields or request surface.

Implementation review result, 2026-11-01: the collector passed synthetic normal, empty, malformed, partial, unsafe-XML, foreign-host, and layout-change tests. A transient snapshot of the live feed parsed successfully with 125 records and no parser issues. The snapshot was stored only under `/tmp` and is not part of the repository or database. The source remains disabled pending a public project contact URL.
