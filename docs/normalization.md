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

The first rule set recognizes:

- ISO dates and ISO date-times;
- a small title-based job-family vocabulary;
- explicit permanent, fixed-term, fellowship, and temporary contract wording;
- contract durations stated in months or years;
- explicit FTE values and unambiguous full-time wording;
- ISO currency salary amounts with a stated pay period;
- gross or net salary wording;
- onsite, hybrid, remote, and flexible work wording;
- English, Portuguese, Spanish, French, and German when explicitly named.

The vocabulary is intentionally small. Unsupported wording is retained for review rather than guessed.

## Review states

| State | Meaning |
|---|---|
| `pending` | Awaiting review; it has no effect on formal postings. |
| `accepted` | Approved by a future review workflow. |
| `rejected` | Reviewed and intentionally not accepted. |
| `superseded` | Replaced by a newer candidate or rule version. |

The normalizer version and candidate SHA-256 are stored so that rerunning the same rules is idempotent and rule changes remain auditable.

