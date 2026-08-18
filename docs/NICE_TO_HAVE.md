# Nice-to-have ideas (not an active backlog)

This document records product ideas that are deliberately outside the current
Essentials+ Freelancer scope. An entry is not planned work, a commitment, or a
feature flag. None of these ideas has a stub, dependency, database table, or
inactive implementation in the repository.

During the first internal pilot, every new product idea belongs here rather
than in implementation work. The binding pilot boundary and hard non-goals are
defined in [`PILOT_SCOPE.md`](PILOT_SCOPE.md). Recording an idea here does not
authorize a stub, empty API, schema object, hidden route, or disabled UI.

## Optional AI support in the quote assistant

- **Benefit:** Suggests descriptions or candidate positions while retaining the
  deterministic calculation and human decision.
- **Rough scope:** Explicit opt-in provider adapter, prompt/version audit,
  redaction, cost controls, and suggestions that never approve or send quotes.
- **Prerequisites:** Approved provider, data-processing assessment, retention
  policy, budget, evaluation set, and a provider-independent fallback.
- **Risks:** Confidential-data disclosure, hallucinated scope/prices, variable
  costs, provider outages, and automation bias.
- **Why not now:** The deterministic assistant already covers the required flow;
  no provider or governance decision exists.
- **Re-evaluation trigger:** An approved provider and evaluation set demonstrate
  measurable drafting benefit without weakening approval or privacy boundaries.

## Receipt OCR

- **Benefit:** Reduces manual entry of receipt date, description, category, and
  amount.
- **Rough scope:** OCR extraction, confidence values, field-level review, and
  retention/error handling for PNG, JPEG, and PDF receipts.
- **Prerequisites:** Representative synthetic/licensed evaluation corpus and an
  approved local or external OCR engine.
- **Risks:** Incorrect amounts, sensitive-data processing, poor scans, and users
  treating extraction as accounting validation.
- **Why not now:** Upload integrity is implemented, but no suitable corpus or
  accuracy threshold is available.
- **Re-evaluation trigger:** A reviewed corpus and acceptance threshold show a
  useful error rate with mandatory human confirmation.

## Recurring invoices

- **Benefit:** Reduces repetitive drafting for stable periodic services.
- **Rough scope:** Versioned schedules and templates, deterministic occurrence
  creation, idempotent jobs, pause/resume, and explicit review before sending.
- **Prerequisites:** Reliable scheduler operations, timezone policy, retry
  semantics, and invoice-template versioning.
- **Risks:** Duplicate or premature invoices, outdated prices, and unnoticed job
  failures.
- **Why not now:** Current invoicing is intentionally explicit and no production
  scheduler has been proven.
- **Re-evaluation trigger:** Repeated manual periodic invoices become a measured
  workload and scheduler recovery is operationally verified.

## Automatic payment reminders

- **Benefit:** Makes follow-up on genuinely overdue invoices more consistent.
- **Rough scope:** Configurable reminder stages, preview, opt-in delivery,
  suppression, audit trail, and delivery failure handling.
- **Prerequisites:** Validated due-date semantics, production SMTP evidence,
  approved wording, and reliable payment-status maintenance.
- **Risks:** Inappropriate reminders, stale payment state, deliverability issues,
  and legal/business-policy mistakes.
- **Why not now:** Real SMTP delivery and deployment-specific reminder policy are
  externally unverified.
- **Re-evaluation trigger:** Production delivery is proven and an operator-owned
  reminder policy with review rules is approved.

## Customer portal

- **Benefit:** Gives customers controlled access to their quotes, invoices, and
  documents.
- **Rough scope:** Separate customer authentication, expiring access, document
  authorization, acceptance records, and privacy/audit controls.
- **Prerequisites:** Threat model, identity/recovery design, public deployment
  hardening, and support process.
- **Risks:** Cross-customer data exposure, account takeover, increased public
  attack surface, and support burden.
- **Why not now:** The product is a single-administrator installation without a
  customer identity boundary.
- **Re-evaluation trigger:** A funded portal requirement has an approved security
  model and dedicated end-to-end test plan.

## Calendar and contact synchronization

- **Benefit:** Avoids duplicate scheduling and customer-contact maintenance.
- **Rough scope:** Explicit connector manifests, OAuth, scoped sync directions,
  conflict resolution, revocation, and audit.
- **Prerequisites:** Selected providers, approved OAuth applications, field
  ownership rules, and synthetic connector test environments.
- **Risks:** Duplicate/overwritten records, token leakage, provider API drift,
  and unintended personal-data propagation.
- **Why not now:** No provider, source-of-truth policy, or product account is in
  scope.
- **Re-evaluation trigger:** A concrete provider and one-way sync use case have
  approved ownership and credential-management rules.

## SEPA preparation

- **Benefit:** Could prepare reviewed payment data for downstream banking tools.
- **Rough scope:** Validated creditor/debtor master data and export preparation;
  no unattended bank submission.
- **Prerequisites:** Precise business requirement, banking-format ownership,
  validation fixtures, and external specialist review where required.
- **Risks:** Invalid payment instructions, sensitive banking data, format drift,
  and users assuming bank acceptance.
- **Why not now:** Payment initiation is outside the focused invoicing product
  and no approved format/use case exists.
- **Re-evaluation trigger:** A named bank/tool and reviewed export contract are
  required by actual operations.

## DATEV export profiles

- **Benefit:** May reduce manual transfer into a chosen accounting workflow.
- **Rough scope:** Versioned, configurable export profiles with field mapping,
  validation reports, and reference fixtures.
- **Prerequisites:** Licensed/current format specification, target workflow,
  synthetic conformance fixtures, and professional validation.
- **Risks:** Format incompatibility, semantic/account mapping errors, and false
  claims of accounting correctness.
- **Why not now:** Reporting intentionally avoids accounting claims and no target
  profile has been specified.
- **Re-evaluation trigger:** A concrete receiving system supplies an approved
  versioned profile and conformance test data.

## PWA or offline mode

- **Benefit:** Allows limited work during intermittent connectivity.
- **Rough scope:** Installable shell, carefully bounded offline reads/writes,
  encrypted local storage, conflict resolution, and cache invalidation.
- **Prerequisites:** Offline ownership model, device threat model, conflict UX,
  and browser coverage.
- **Risks:** Stale invoices/module state, duplicated commands, local data
  exposure, and complex synchronization failures.
- **Why not now:** The server-enforced single source of truth and global timer
  need online concurrency guarantees.
- **Re-evaluation trigger:** Measured offline usage justifies a specified subset
  whose conflicts can be deterministically resolved.

## Extended Android functions

- **Benefit:** Brings selected web workflows to the established mobile client.
- **Rough scope:** Product-driven additions such as project/quote/expense flows,
  with JVM and device-level tests for each new boundary.
- **Prerequisites:** Prioritized mobile use case, API compatibility plan, and
  emulator/instrumentation CI capacity.
- **Risks:** Web/mobile behavior drift, insecure document handling, and larger
  maintenance surface.
- **Why not now:** The existing Android core is stable and no missing mobile flow
  was prioritized for this release.
- **Re-evaluation trigger:** A recurring mobile-only workflow has clear acceptance
  criteria and instrumentation coverage can be added with it.

## Multi-user and role operation

- **Benefit:** Would allow several people to work in one installation with
  differentiated permissions.
- **Rough scope:** Identity lifecycle, roles, object authorization, audit,
  invitation/recovery, concurrency policy, and data migration.
- **Prerequisites:** New product decision, complete authorization model, threat
  model, and migration/support plan.
- **Risks:** Authorization flaws, privacy breaches, fundamentally increased
  complexity, and accidental multi-tenancy.
- **Why not now:** Single installation with exactly one administrator is a
  deliberate compatibility and product boundary.
- **Re-evaluation trigger:** The product boundary is explicitly changed and a
  funded security design is approved; this is not an incremental toggle.

## Extended analytics

- **Benefit:** Could expose longer-term operational trends and forecasting.
- **Rough scope:** Explicit metric definitions, drill-down, saved views, and
  privacy-preserving aggregation beyond current factual reports.
- **Prerequisites:** Validated decisions the metrics should support, sufficient
  data quality, and performance budget.
- **Risks:** Misleading small-sample conclusions, metric ambiguity, performance
  cost, and accidental business/advisory claims.
- **Why not now:** Current dashboard covers requested factual operational status
  and filtered CSV export.
- **Re-evaluation trigger:** A repeated decision cannot be answered by current
  reports and has a precise testable metric definition.

## Electronic signature

- **Benefit:** Could collect stronger evidence of customer approval for quotes.
- **Rough scope:** Provider connector, signer flow, immutable evidence package,
  identity/audit metadata, retention, and failure/revocation handling.
- **Prerequisites:** Approved legal/business requirements, selected provider,
  data-processing assessment, and external sandbox.
- **Risks:** Misstated legal effect, identity disputes, vendor lock-in, and
  sensitive evidence handling.
- **Why not now:** Controlled in-product acceptance exists; no provider or
  evidence standard has been approved.
- **Re-evaluation trigger:** A concrete signature assurance requirement and
  approved provider sandbox are available for conformance testing.
