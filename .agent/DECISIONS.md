# Decisions

## 2026-08-12 - Keep Freelancer focused and single-user

**Decision:** Freelancer remains one installation for one administrator and
owns client, project, time, quote, invoice, expense, and simple export flows.
Shop/inventory and groupware capabilities stay outside this repository.

**Reason:** This is the established product boundary and avoids turning the MVP
into a multi-tenant platform or unrelated suite.

**Alternatives considered:** Multi-tenant SaaS, shop features, groupware, and a
framework rewrite were explicitly rejected unless separately requested.

**Consequences:** New features must fit the focused solo-professional workflow;
cross-product capabilities belong in their owning repositories.

## 2026-08-13 - Preserve legacy identifiers and migrate additively

**Decision:** Keep the `tracker` PostgreSQL database/user, `tracker_db_data` and
`tracker_invoices` volumes, and `de.itmitalles.tracker` Android package stable.
Use additive Alembic migrations for compatible schema evolution.

**Reason:** These names are deployed compatibility and persistence boundaries,
not harmless branding strings.

**Alternatives considered:** Opportunistic renaming was rejected because it can
disconnect deployed data, clients, and automation.

**Consequences:** A rename requires its own tested migration. The legacy
baseline migration refuses downgrade; production rollback uses a verified
business-data restore, not destructive schema reversal.

## 2026-08-13 - Treat database and documents as one recovery unit

**Decision:** A recoverable backup must contain both the PostgreSQL business
database and the complete document volume holding PDFs, logos, and receipts.
Offsite copies use explicit encrypted restic/rclone configuration outside Git.

**Reason:** Relational records and referenced business documents are jointly
authoritative; either half alone is incomplete.

**Alternatives considered:** Database-only backup and committing deployment
credentials were rejected.

**Consequences:** Export briefly stops the backend writer, validates both
artifacts and checksums, and restore refuses non-empty targets. Timer success is
not evidence of recoverability without a restore rehearsal.

## 2026-08-13 - Preserve billing and traceability invariants

**Decision:** Money uses fixed-precision database values and Decimal arithmetic;
number counters are locked during allocation; billed time and invoice links
change atomically; an accepted quote converts at most once; invoice and quote
statuses follow explicit transitions.

**Reason:** Concurrent or partial billing changes can duplicate numbers,
double-bill time, lose traceability, or misstate document status.

**Alternatives considered:** Client-calculated totals, unrestricted status
updates, and unlinking source records were rejected.

**Consequences:** Changes to invoice, quote, time, PDF, or deletion paths must
retain rollback behavior and receive focused tests for these invariants.

Accepted fixed-price quotes use a dedicated invoice preview token, an explicit
service date, and operator confirmation. Facts that do not exist for a fixed
quote (actual/billable minutes, work minimum, increment, and service mode) are
stored as null and shown as not applicable; they are never invented as zero.

## 2026-08-13 - Keep the Essentials+ module contract repository-local

**Decision:** Module manifests, persisted state, dependency/conflict checks,
health/configuration status, API guards, navigation guards, audit events, and
host-job enforcement live in this repository. Required core modules cannot be
disabled; optional-module deactivation retains all existing business data.

**Reason:** The product needs one enforceable contract across server, browser,
and host jobs without creating an unneeded cross-product framework.

**Alternatives considered:** Frontend-only feature flags and a shared plugin
framework were rejected because the former is not authorization and the latter
would exceed this product boundary.

**Consequences:** Every protected router declares its owning module, optional
navigation follows server state, and export/offsite jobs honor persisted state
once the module schema exists. Manifests expose secret requirements/status only,
never secret values, and the Admin Center cannot execute arbitrary commands.

## 2026-08-13 - Snapshot deterministic quote inputs before approval

**Decision:** Catalog items, material/service/travel prices, packages, and
templates are versioned. An assistant draft stores immutable Decimal-based line
and calculation snapshots, requires explicit human approval, and transfers at
most once into the established quote model.

**Reason:** Reproducible commercial documents must not change when a catalog is
edited later, and suggestions must not bypass human release.

**Alternatives considered:** Binary floats, mutable catalog references,
automatic approval, and an external AI dependency were rejected.

**Consequences:** Later catalog versions affect only new calculations. Existing
drafts/quotes retain their snapshots. Any future AI feature may suggest inputs
only and remains outside the deterministic calculation/approval authority.

## 2026-08-13 - Separate automated local evidence from external proof

**Decision:** `make full-check` is the single disposable automated acceptance
entry point. Local SMTP and restic fixtures are explicitly classified as
simulators; production SMTP delivery, remote offsite recovery, proxy/DNS/TLS,
and deployed revision require separate external evidence.

**Reason:** Repeatable local tests provide strong regression evidence but cannot
prove accounts, infrastructure, credentials, or state outside the repository.

**Alternatives considered:** Manual browser sign-off and describing successful
simulators as production verification were rejected.

**Consequences:** New product behavior needs automated coverage, the matrix in
`docs/VERIFICATION_MATRIX.md` records evidence boundaries, and external-only
requirements remain `Blocked` in `.agent/TODO.md` rather than becoming
nice-to-have ideas.

## 2026-08-19 - Freeze features for the first internal pilot

**Decision:** The pilot is limited to the existing single-administrator
customer/project/time/quote/invoice/expense/report/export/restore workflow.
Every new idea is recorded only in `docs/NICE_TO_HAVE.md`; no stub API, table,
feature flag, or disabled UI is created for it.

**Reason:** Additional surface area is currently a larger pilot risk than a
missing feature.

**Consequences:** Work may improve safety, evidence, or an existing pilot flow,
but may not introduce multi-user/SaaS, commerce, tax-automation, AI/OCR,
payments, portal, Kubernetes, or other-module scope. The deterministic quote
assistant remains versioned, traceable, and human-approved.

## 2026-08-19 - Make invoice tax and external delivery operator decisions

**Decision:** The application never infers tax status or injects a tax-law
statement on a fresh installation. Time invoices and quote lines require an
explicit tax rate. External delivery requires the operator to open the PDF,
confirm recipient/number/amount and an external-email warning, then use a
unique idempotency key; resends are separately explicit and auditable.

**Reason:** A syntactically valid PDF or configured SMTP connection does not
establish legal correctness, operator intent, or safe delivery.

**Consequences:** SMTP may be absent without blocking drafts/PDFs. Success sets
`sent` but never `paid`; failures preserve the prior invoice state. Send
attempts store safe operational evidence, successful-key replay performs no
second SMTP call, and full message identifiers/secrets are never exposed.

## 2026-08-19 - Treat deployment and external-service claims as evidence gates

**Decision:** Desired Compose/configuration is not deployed-state evidence. A
read-only inspector collects secret-redacted JSON/Markdown for revision, dirty
state, images, health, volumes, schema, app metadata, backup/restore evidence,
and explicitly authorized proxy/TLS observations. Real SMTP and real offsite
status close only through their dedicated operator acceptance procedures.

**Reason:** CI and local fixtures cannot prove which code/data runs elsewhere,
provider delivery, remote durability, or recovery from a remote target.

**Consequences:** Missing access or credentials remains an external gate, not a
reason to invent configuration or infrastructure. Backup retention is dry-run
by default, restoration uses different empty volumes, and evidence language
must distinguish implemented/local/CI/emulator/real-external/deployed/unknown.

## 2026-08-20 - Make billing decisions explicit, configurable, and immutable

**Decision:** Billing rules live in one versioned policy service backed by
operator settings. Tim's profile is private 50 EUR/hour, business/individual
project 75 EUR/hour, travel 30 EUR/hour, 60-minute first/onsite work minima,
15-minute remote-follow-up increments, and a 30-minute travel minimum with no
default travel increment. Time stores the resolved decision; invoice creation
requires an exact visible preview and snapshots every relevant input/result.

**Reason:** A mutable client rate or rounded display quantity cannot explain a
historic invoice. The operator must see and confirm every minimum, increment,
travel amount, tax status and total before number/PDF creation.

**Consequences:** Later settings/project/client changes affect only newly
calculated decisions. Existing invoice rows/PDFs remain unchanged. Migrated
profiles and unbilled time are unconfirmed until explicit review. Quote
creation never creates billable time. Unknown historical snapshot facts remain
null rather than being invented.

## 2026-08-20 - Lock SMTP off for the first internal pilot

**Decision:** This supersedes the 2026-08-19 SMTP activation path for the first
pilot. `communication.smtp` is forced disabled and cannot be enabled. The
operator reviews/downloads the PDF, sends it through the normal external mail
account, then explicitly records manual delivery.

**Reason:** The existing SMTP call can succeed externally before the local
transaction commits. Without durable pre-send state and `send_unknown`, a
process failure can make delivery ambiguous and an automatic retry unsafe.

**Consequences:** Runtime SMTP configuration does not activate delivery; the
fixture must observe zero messages and no new send-attempt row. Future SMTP
work is one complete hardening contract, including crash injection before/after
acceptance and no automatic retry from `send_unknown`; partial hardening cannot
unlock the module.
