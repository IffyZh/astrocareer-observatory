# Source review template

[简体中文](source-review-template.zh-CN.md)

Copy this document for each proposed real source. Reviewing a page is not approval to collect it. Set an explicit access decision and keep the source disabled until every required item is complete.

## 1. Identity and purpose

- Source ID:
- Public name:
- Owning organization:
- Homepage:
- Proposed use in AstroCareer Observatory:
- Proposed maintainer:
- Review date:
- Next mandatory review date:

## 2. Supported access methods

- [ ] Official API
- [ ] RSS or Atom feed
- [ ] Email subscription
- [ ] Downloadable dataset
- [ ] Public HTML pages
- [ ] Manual collection only

Preferred method and reason:

## 3. Robots and terms

- Robots URL:
- Robots retrieval date:
- Relevant robots rules:
- Terms URL:
- Terms review date:
- Relevant collection restrictions:
- Relevant storage restrictions:
- Relevant redistribution restrictions:
- Does access require an account, authentication, or acceptance of additional terms?

Do not paste credentials, session cookies, or private correspondence into this review.

## 4. Explicit access decision

Select exactly one:

- [ ] `approved`
- [ ] `manual_only`
- [ ] `api_only`
- [ ] `permission_required`
- [ ] `prohibited`
- [ ] `pending_review`

Decision rationale:

Reviewer:

Decision date:

## 5. Technical boundaries

- Exact allowed hosts:
- Allowed path scope:
- Minimum interval between requests:
- Maximum expected requests per run:
- Expected response types:
- Expected maximum response size:
- Pagination behavior:
- Stable source-record identifier:
- Project contact URL for the User-Agent:

## 6. Evidence retention and publication

- May full responses be retained privately?
- Retention period:
- May short evidence excerpts be stored?
- May normalized facts be published?
- May source URLs and hashes be published?
- Required attribution:
- Required deletion or correction process:

## 7. Personal-data assessment

- Does the source contain named applicants or candidates?
- Does it contain personal contact information?
- Which personal fields, if any, are necessary for the project purpose?
- Which fields must be discarded before persistence?
- Does the source require a separate privacy or legal review?

Default decision: discard applicant identities and personal contact data unless a documented project purpose and lawful publication basis exist.

## 8. Failure and monitoring plan

- Marker that distinguishes an explicit empty listing:
- Expected minimum and typical record count:
- Conditions that must fail the collector:
- Conditions that require automatic source suspension:
- Maintainer notification route:
- Manual shutdown procedure:

## 9. Approval checklist

- [ ] Access method is the least intrusive supported option.
- [ ] Robots and terms have been reviewed and linked.
- [ ] Access decision is explicit.
- [ ] Allowed hosts and request interval are recorded.
- [ ] Retention and redistribution rules are recorded.
- [ ] Personal-data handling is documented.
- [ ] Normal, empty, malformed, and layout-change fixtures exist.
- [ ] No production credential is required by the collector.
- [ ] Source remains disabled until the implementation review is complete.

## 10. Final notes

Unresolved questions:

Implementation review result:

