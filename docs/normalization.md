# Normalization and review

[简体中文](normalization.zh-CN.md)

Normalization converts a source-faithful `SourcePosting` into a reviewable `NormalizedPostingCandidate`. It never edits a formal posting directly.

## Safety model

- Original text remains attached to every normalized value.
- Only deterministic, documented rules produce normalized values.
- Missing source text becomes `not_reported`.
- Present but unsupported or conflicting text becomes `ambiguous`.
- Reproducible calculations, such as converting two years to 24 months, become `derived`.
- Candidates enter the database with `review_status = pending`.
- Acceptance into formal posting tables requires a separate review action that has not yet been implemented.

## Currently supported rules

The current MVP rule set recognizes:

- ISO dates, ISO date-times, and source-provided month/year start dates;
- a small title- and reviewed source-category-based job-family vocabulary;
- explicit permanent, fixed-term, fellowship, and temporary contract wording;
- unambiguous contract durations stated in months or years;
- an explicitly stated number of positions and conservative extension indicators;
- explicit FTE values and unambiguous full-time wording;
- common currency markers and salary amounts with a stated pay period; a bare `$`
  is treated as USD only when the same posting explicitly locates the job in the
  United States;
- gross or net salary wording;
- onsite, hybrid, remote, and flexible work wording;
- English, Portuguese, Spanish, French, and German when explicitly named.

The vocabulary is intentionally small. Unsupported wording is retained for review rather than guessed.

For the Planetary Research Jobs feed, the MVP also preserves the feed's category,
department, reference code, canonical listing URL, and official-announcement URL.
The official-announcement URL is data only: the collector does not request or
follow it. Requirements, skills, applicant counts, hiring counts, and
international eligibility remain `not_reported` because this feed does not
provide them in the reviewed summary fields.

## Review states

| State | Meaning |
|---|---|
| `pending` | Awaiting review; it has no effect on formal postings. |
| `accepted` | Approved by a future review workflow. |
| `rejected` | Reviewed and intentionally not accepted. |
| `superseded` | Replaced by a newer candidate or rule version. |

The normalizer version and candidate SHA-256 are stored so that rerunning the same rules is idempotent and rule changes remain auditable.
