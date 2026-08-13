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
