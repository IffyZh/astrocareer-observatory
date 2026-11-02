# Data model v0.1

[简体中文](data-model.zh-CN.md)

This document defines the first conceptual data model. It is intentionally independent of a particular database implementation. Names may change before the first schema migration is created.

## General rules

1. Preserve the official statement separately from normalized values.
2. Attach provenance to claims that do not originate in this project.
3. Never use a bare null when the reason for absence is known.
4. Store counts, not manually calculated rates. Rates are derived from counts.
5. Do not infer a requirement, skill, contract condition, or competition metric from a job title alone.
6. Record when a fact was published, observed, and verified as separate timestamps.

## Availability values

Optional factual values use an `availability` field. A value is populated only when `availability` is `reported` or, where applicable, `derived`.

| Value | Meaning |
|---|---|
| `reported` | Explicitly stated by an identified source. |
| `derived` | Calculated reproducibly from reported values. |
| `not_reported` | The reviewed source does not state the value. |
| `not_applicable` | The field does not apply to this posting or process. |
| `not_yet_available` | The value may exist later, but the process is not complete. |
| `inaccessible` | The source is known but could not be accessed. |
| `ambiguous` | The source contains relevant information, but it cannot be normalized reliably. |
| `redacted` | The source explicitly withholds or redacts the value. |
| `not_collected` | The project has not attempted to collect this field yet. |
| `parsing_failed` | Collection was attempted, but automated parsing failed. |

`unknown` is deliberately excluded: it does not explain why a value is absent. Legacy imports that cannot establish a reason should use `not_collected` and document the import limitation.

## Time fields

All timestamps use ISO 8601. Instants are stored in UTC. A source-provided date without a time remains a date and must not be given an invented time zone.

| Field | Type | Meaning |
|---|---|---|
| `posted_at` | datetime or date | Publication time stated by the source. |
| `application_deadline_at` | datetime or date | Official application deadline. |
| `first_seen_at` | datetime | First time this project observed the posting. |
| `last_seen_at` | datetime | Most recent successful observation of the posting. |
| `observed_at` | datetime | Time of one particular observation or snapshot. |
| `source_updated_at` | datetime or date | Update time stated by the source, if any. |
| `verified_at` | datetime | Time a claim was last manually or automatically verified. |
| `closed_at` | datetime or date | Confirmed closure or withdrawal time, when available. |

`posted_at` and `first_seen_at` are not interchangeable. If the source only says “three days ago,” the original expression should be preserved and any normalized date marked as derived.

## Posting

A `Posting` is the project's stable identity for one recruitment opportunity. It may be observed through multiple sources and snapshots.

Core fields:

| Field | Type | Notes |
|---|---|---|
| `posting_id` | UUID | Project-controlled stable identifier. |
| `title` | text | Normalized display title. |
| `official_title` | text | Title exactly as stated by the authoritative source. |
| `institution_id` | UUID | Link to a normalized institution. |
| `location` | structured value | Country, region, city, and remote status where available. |
| `job_family` | controlled value | For example postdoc, faculty, research software, technical staff, or research support. |
| `positions_available` | non-negative integer | Number of openings, only when stated. |
| `status` | controlled value | Observed lifecycle state, not a prediction. |

Optional posting fields use the availability values defined above.

## Institution registry

`Institution` is the canonical organization identity referenced by postings. Reviewed ROR Schema 2.x dumps can populate its ROR ID, display name, status, country, homepage, establishment year, and source dates.

Related tables preserve multilingual names, official domains, organization types, and GeoNames-based locations. Domains have first-seen, last-seen, and active fields so that a changed domain is not silently erased. Every imported row retains the ROR source ID, while each import run records the dataset version, file hash, importer version, schema versions, and insert/update counts.

Presence in ROR does not make an institution relevant to astronomy and does not authorize crawling its domain. Relevance classification and career-endpoint review are separate later stages.

## Employment terms

`EmploymentTerms` preserves the official working conditions separately from the normalized values.

| Field | Type | Meaning |
|---|---|---|
| `contract_type` | controlled value | `permanent`, `fixed_term`, `fellowship`, `temporary`, `casual`, or `other`. |
| `contract_type_availability` | controlled value | Availability of the normalized contract type. |
| `contract_duration_months` | non-negative integer | Explicit or reproducibly derived duration. |
| `contract_duration_availability` | controlled value | Availability of the duration. |
| `employment_fraction` | number from 0 to 1 | Full-time equivalent, where 1.0 is full time. |
| `employment_fraction_availability` | controlled value | Availability of the employment fraction. |
| `start_date` | date or source text | Expected or required start date. |
| `start_date_precision` | controlled value | `date`, `month`, `year`, or `text`. |
| `start_date_availability` | controlled value | Availability of the start date. |
| `work_mode` | controlled value | `onsite`, `hybrid`, `remote`, `flexible`, or `other`. |
| `work_mode_availability` | controlled value | Availability of the work mode. |
| `official_text` | text | Source wording supporting the terms. |
| `evidence_id` | UUID | Supporting evidence. |

“Possibility of extension” does not make a fixed-term contract permanent. Duration derived from years to months must be marked `derived` rather than `reported`.

## Compensation

Each `Compensation` record represents one salary or payment statement. Multiple records may be needed when a posting reports alternatives or separate components.

| Field | Type | Meaning |
|---|---|---|
| `amount_min` / `amount_max` | non-negative number | Exact amount or stated range. |
| `currency` | ISO 4217 code | Currency stated by the source. |
| `pay_period` | controlled value | Annual, monthly, weekly, daily, hourly, or total contract. |
| `gross_net` | controlled value | `gross`, `net`, or `not_stated`. |
| `availability` | controlled value | Availability or missing reason. |
| `official_text` | text | Original salary wording. |
| `evidence_id` | UUID | Supporting evidence. |

The database stores nominal source amounts. Currency conversion, purchasing-power adjustment, and tax estimates belong to later analytical layers and must include their own dates and assumptions.

## Working languages

`PostingLanguage` records each language separately with its official wording and requirement level. A country location alone is not evidence of a language requirement.

## Official eligibility requirements

An `EligibilityRequirement` records a condition stated by an official or otherwise identified source. Requirements are stored as individual records so that contradictory or changing statements can coexist with their provenance.

| Field | Type | Meaning |
|---|---|---|
| `requirement_id` | UUID | Stable identifier. |
| `posting_id` | UUID | Related posting. |
| `requirement_type` | controlled value | Degree, field, experience, citizenship, residence, language, publication record, availability date, security clearance, or other. |
| `level` | controlled value | `required`, `preferred`, `desirable`, or `informational`. |
| `official_text` | text | Exact relevant source wording within quotation limits. |
| `normalized_value` | structured value | Machine-queryable interpretation when reliable. |
| `availability` | controlled value | Availability or missing reason. |
| `evidence_id` | UUID | Evidence supporting the claim. |
| `valid_from` / `valid_to` | datetime | Optional validity interval when a requirement changes. |

The project must not convert “preferred” into “required.” A degree requirement should distinguish degree type, subject, completion status, and any “by start date” condition.

## Skills

A `SkillRequirement` represents a named research or technical capability mentioned in a source.

| Field | Type | Meaning |
|---|---|---|
| `skill_requirement_id` | UUID | Stable identifier. |
| `posting_id` | UUID | Related posting. |
| `skill_id` | UUID | Link to a normalized skill vocabulary. |
| `official_term` | text | Term used in the source, such as “Python” or “HPC.” |
| `level` | controlled value | `required`, `preferred`, `desirable`, or `mentioned`. |
| `experience_minimum` | duration | Minimum experience only when explicitly stated. |
| `official_text` | text | Relevant source context. |
| `availability` | controlled value | Availability or missing reason. |
| `evidence_id` | UUID | Supporting evidence. |

Normalized skills may have aliases, but the official term must be preserved. Keyword occurrence alone does not prove that a skill is required.

## International applicant access and immigration assessment

International accessibility is represented in two layers. Employer statements are observed facts; immigration feasibility is a dated, applicant-specific assessment derived from those facts and official policy sources. The derived assessment must never overwrite the underlying evidence.

### Employer-stated international eligibility

An `InternationalEligibility` record captures what the job announcement or employer explicitly says.

| Field | Type | Meaning |
|---|---|---|
| `international_eligibility_id` | UUID | Stable identifier. |
| `posting_id` | UUID | Related posting. |
| `applicant_eligibility` | controlled value | Employer-stated access category. |
| `applicant_eligibility_availability` | controlled value | Availability of the eligibility category. |
| `work_authorization_requirement` | controlled value | Whether existing authorization is required. |
| `work_authorization_availability` | controlled value | Availability of the work-authorization condition. |
| `visa_support` | controlled value | Employer statement about sponsorship or assistance. |
| `visa_support_availability` | controlled value | Availability of the visa-support statement. |
| `official_text` | text | Relevant source wording. |
| `evidence_id` | UUID | Evidence from the announcement or employer. |

Initial `applicant_eligibility` values:

- `explicitly_open`: the source explicitly welcomes or permits international applicants;
- `open_with_conditions`: international applications are allowed subject to stated conditions;
- `citizenship_required`: a specified citizenship is mandatory;
- `residency_required`: a specified residence status is mandatory;
- `existing_work_authorization_required`: the applicant must already have work authorization;
- `restricted_other`: another explicit restriction applies;
- `not_reported`: the reviewed source is silent;
- `ambiguous`: relevant wording exists but cannot be classified reliably.

Initial `visa_support` values:

- `sponsorship_available`;
- `relocation_or_visa_assistance_available`;
- `case_by_case`;
- `sponsorship_unavailable`;
- `not_applicable`;
- `not_reported`;
- `ambiguous`.

Initial `work_authorization_requirement` values:

- `not_required`;
- `required_before_application`;
- `required_before_start`;
- `employer_may_sponsor`;
- `other_condition`.

Silence about nationality or visas must be stored as `not_reported`, not interpreted as either permission or prohibition.

### Derived immigration assessment

An `InternationalAccessAssessment` evaluates one posting for one defined applicant profile at a particular point in time. It is an analytical result, not an official promise of visa approval or legal advice.

| Field | Type | Meaning |
|---|---|---|
| `assessment_id` | UUID | Stable identifier. |
| `posting_id` | UUID | Related posting. |
| `applicant_profile_id` | UUID | Versioned profile containing only factors required for the assessment. |
| `destination_country` | ISO country code | Country whose immigration rules apply. |
| `route_id` | text | Identified visa or work-authorization route, when known. |
| `assessment_level` | controlled value | Overall difficulty category. |
| `eligibility_result` | controlled value | `apparently_eligible`, `conditionally_eligible`, `apparently_ineligible`, or `indeterminate`. |
| `reason_codes` | list of controlled values | Factors supporting the result. |
| `explanation` | text | Human-readable derivation without sensitive personal data. |
| `availability` | controlled value | Availability or missing reason. |
| `policy_as_of_at` | date | Date for which policy sources were checked. |
| `assessed_at` | datetime | Time the assessment was generated or reviewed. |
| `method_version` | text | Version of the assessment rules. |
| `job_evidence_ids` | list of UUIDs | Evidence from the posting or employer. |
| `policy_evidence_ids` | list of UUIDs | Official immigration-policy evidence. |
| `expires_at` | date | Optional date after which reassessment is required. |

Initial `assessment_level` values:

- `low_friction`: no identified immigration barrier beyond routine documentation;
- `moderate`: a known route appears available, with material administrative conditions;
- `high`: eligibility or sponsorship depends on substantial conditions or employer action;
- `very_high`: a route may exist, but major restrictions make access unlikely or unusually burdensome;
- `ineligible`: an explicit rule or posting restriction makes the defined profile ineligible;
- `indeterminate`: available evidence is insufficient or contradictory.

This scale is ordinal, not a probability. `moderate` does not mean a 50% visa approval chance.

Initial reason codes may include:

- `citizenship_restriction`;
- `residency_restriction`;
- `existing_authorization_required`;
- `employer_sponsorship_required`;
- `employer_sponsorship_confirmed`;
- `employer_sponsorship_not_stated`;
- `salary_threshold_met` or `salary_threshold_uncertain`;
- `occupation_or_researcher_route_available`;
- `qualification_recognition_required`;
- `security_clearance_restriction`;
- `contract_too_short_for_route`;
- `policy_source_outdated`;
- `insufficient_job_information`.

### Applicant profile and privacy

The assessment may depend on citizenship, current residence or work authorization, degree level, career stage, and other route-specific facts. Public exports should use non-identifying, versioned scenario profiles such as “non-EEA PhD applicant without existing EU work authorization.” A private personal profile must not be committed to the public repository.

### Assessment rules

- Use official government immigration sources as the primary policy evidence.
- Record the policy date and re-evaluate when policies or the posting change.
- Never infer accessibility from destination country alone.
- Keep employer sponsorship statements separate from legal route eligibility.
- Do not treat `not_reported` sponsorship as `sponsorship_unavailable`.
- Do not calculate an assessment when essential applicant-profile facts are missing; use `indeterminate` with explicit reasons.
- Present results as research guidance, not legal advice or a guarantee of entry, sponsorship, or visa approval.

## Recruitment metrics

Competition data is represented as dated metrics rather than columns on the posting. This allows different stages, definitions, and sources to be recorded without overwriting one another.

| Field | Type | Meaning |
|---|---|---|
| `metric_id` | UUID | Stable identifier. |
| `posting_id` | UUID | Related posting or recruitment round. |
| `metric_type` | controlled value | See below. |
| `value` | non-negative integer | Count when available. |
| `availability` | controlled value | Availability or missing reason. |
| `as_of_at` | datetime or date | Date to which the count applies. |
| `population_definition` | text | Source definition of who was counted. |
| `evidence_id` | UUID | Supporting evidence. |

Initial `metric_type` values:

- `applications_submitted`: all submitted applications, if that is the source definition;
- `applications_eligible`: applications formally accepted as eligible;
- `applications_complete`: complete applications, when separately reported;
- `candidates_shortlisted`: people placed on a shortlist;
- `candidates_interviewed`: people interviewed;
- `offers_made`: offers issued;
- `hires_final`: people ultimately hired or positions formally filled.

These counts are not interchangeable. A public list of eligible candidates must not be stored as `applications_submitted` unless the source explicitly says they are the same population.

## Derived selection measures

The preferred name for “admission ratio” is `selection_rate`:

```text
selection_rate = hires_final / applications_submitted
```

For readability, the reciprocal may also be displayed:

```text
applicants_per_hire = applications_submitted / hires_final
```

Rules:

- The numerator and denominator must refer to the same posting or recruitment round.
- Both counts must have `availability = reported` and compatible population definitions.
- `selection_rate` is `derived`, never manually entered.
- If submitted applications are zero, `selection_rate` is unavailable with reason `not_applicable`.
- If final hires are zero, `selection_rate` is `0`, while `applicants_per_hire` is unavailable with reason `not_applicable`.
- Rates should carry the evidence links and `as_of_at` values of both source counts.
- A published rate may be preserved as source evidence, but the project should calculate its own value from the published counts when possible.

Additional stage-specific rates, such as interview rate or offer rate, must use explicit names and denominators.

## Evidence

An `Evidence` record supports a claim, requirement, skill, or metric.

Minimum fields:

- `evidence_id`;
- source and canonical URL;
- source organization;
- source type and authority level;
- publication date when available;
- `observed_at`;
- content hash;
- parser version;
- verification method and `verified_at`;
- quotation or locator sufficient to find the relevant statement;
- redistribution constraints where known.

An authority level describes how directly the source supports a claim. It is not a probability that the claim is true.

## Open questions before implementation

- Which controlled vocabulary should be used for job families and skills?
- Should date-only values be stored in the same columns as timestamps or in separate fields?
- How should multiple openings under one announcement be represented when their requirements differ?
- Which evidence snippets may be stored or redistributed for each initial source?
- How often should immigration-policy evidence expire and trigger reassessment?
- Which non-identifying applicant scenarios should be included in public exports?
