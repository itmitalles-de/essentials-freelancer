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
