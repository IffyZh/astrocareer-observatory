# Source review: AAS Job Register

[简体中文](aas-job-register.zh-CN.md)

## 1. Identity and purpose

- Source ID: `aas-job-register`
- Public name: AAS Job Register
- Owning organization: American Astronomical Society (AAS)
- Homepage: <https://aas.org/jobregister>
- Proposed use: discover astronomy and astrophysics vacancies and preserve source provenance
- Proposed maintainer: AstroCareer Observatory contributors
- Review date: 2026-11-01
- Next mandatory review date: before requesting permission or implementing automated access

## 2. Supported access methods

- [ ] Official API
- [ ] RSS or Atom feed
- [ ] Email subscription
- [ ] Downloadable dataset
- [ ] Public HTML pages
- [x] Manual collection only

The public listing is useful for people, but no official machine-readable access method was identified during this review.

## 3. Robots and terms

- Robots URL reviewed: <https://aas.org/robots.txt>
- Terms: <https://aas.org/policies/terms-use-conditions-service>
- Copyright and permissions: <https://aas.org/policies/copyright-permissions>
- Job Register publication policy: <https://aas.org/jobregister/Job_Register_publication_policy>
- Review date: 2026-11-01

The AAS copyright and permissions policy expressly prohibits spidering, screen scraping, database scraping, harvesting, and other automatic means of obtaining site information. It also restricts reposting, mirroring, redistribution, derivative use, and commercial use. Research and educational permissions do not override the automated-access prohibition.

Public browsing does not require an account. Posting an advertisement does require an account and payment, but AstroCareer Observatory must not authenticate or submit content.

## 4. Explicit access decision

- [ ] `approved`
- [ ] `manual_only`
- [ ] `api_only`
- [x] `permission_required`
- [ ] `prohibited`
- [ ] `pending_review`

Automated access is not permitted under the reviewed policy. A collector must not be implemented or run unless the AAS gives express written permission covering the proposed request frequency, storage, and publication. Limited manual recording of minimal facts should still be reviewed against the applicable terms before publication.

Reviewer: AstroCareer Observatory project review

Decision date: 2026-11-01

## 5. Technical boundaries

No automated technical boundary is approved. The source is disabled. The allowlisted homepage host exists only for registry validation and does not authorize network access.

## 6. Evidence retention and publication

- Full responses: do not retain through automated collection
- Full advertisements: do not republish
- Normalized facts: not approved for automated publication under this review
- URLs and source attribution: may be used when manually citing a source, subject to applicable terms
- Required process: obtain and archive express written permission before changing the decision

## 7. Personal-data assessment

Advertisements can contain named contacts, email addresses, and other professional personal data. These fields are unnecessary for the initial market model and must not be copied into the public dataset.

## 8. Failure and monitoring plan

Not applicable while automated access is blocked. Any attempted automated run must fail before making a request.

## 9. Approval checklist

- [x] Access method is the least intrusive supported option.
- [x] Robots and terms have been reviewed and linked.
- [x] Access decision is explicit.
- [x] Retention and redistribution restrictions are recorded.
- [x] Personal-data handling is documented.
- [x] Source remains disabled.
- [ ] Written permission has been obtained.
- [ ] Automated collection is approved.

## 10. Final notes

The Job Register is a high-value source, but value does not override its access policy. Revisit only after an official API/feed is introduced or written permission is received.
