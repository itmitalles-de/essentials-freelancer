# Current state

## Pilot boundary

Essentials+ Freelancer is one Docker Compose installation for exactly one
administrator. The frozen pilot scope is clients, projects, time, quotes,
invoices, expenses, reports, and complete backup/restore. It is not SaaS,
multi-tenant, team-oriented, or Kubernetes-based. `docs/PILOT_SCOPE.md` is the
authoritative boundary.

Visible naming is `Essentials+ Freelancer` and
`itmitalles-de/essentials-freelancer`. Legacy `tracker` database, volume,
browser-storage, Android-package, and migration identifiers remain deliberate
compatibility IDs; see `docs/COMPATIBILITY_IDENTIFIERS.md`.

## Billing-policy release

PR #3 on branch `pilot/freelancer-first-internal-use` is the only pilot PR and
the authoritative GitHub record for exact-head CI, API-35, review, squash merge,
and the resulting `master` commit.

Migration `0007_billing_policy` implements an explicit configurable policy:

- private 50.00 EUR/hour, business/individual project 75.00 EUR/hour, travel
  30.00 EUR/hour in Tim's operator settings;
- 60-minute first-order and onsite/travel-associated work minima;
- 15-minute upward increments only for remote follow-up work without travel;
- separate 30-minute travel minimum and no travel rounding above it unless an
  increment is explicitly configured;
- client/project profiles, resolved time-entry decisions, visible exact-token
  invoice previews, immutable invoice-line/tax/footer snapshots, and stored PDFs;
- quote preparation creates no time and fixed-price conversion has its own
  service-date preview and confirmation gate;
- explicit 0-percent/§ 19 operator configuration without inferred tax status.

The migration is additive. Existing client rates become unconfirmed custom
profiles; project profiles remain unconfirmed; prior time duration/rate is
preserved under neutral legacy markers; old snapshot facts remain null rather
than invented. Invoice numbers, totals, lines, PDF paths, and PDF bytes remain
unchanged. Unbilled legacy time must pass profile review and a new visible
preview before invoicing.

## SMTP safety

`communication.smtp` is forced disabled by migration, registry reconciliation,
module enable guard, send-route guard, and UI. The application does not claim an
email was sent. The first pilot uses PDF generation, manual review/download,
external sending through the operator's normal account, and a deliberate
manual-delivery status. Future SMTP activation requires the complete durable
`pending`/`sent`/`failed`/`send_unknown` crash contract in
`docs/operations/SMTP_ACCEPTANCE.md`; partial hardening is not accepted.

## Verification

On 2026-08-20 the billing-policy candidate passed:

- 67 backend tests and pip audit;
- 9 frontend test files / 11 tests, TypeScript/Vite build and npm audit;
- 3 Android JVM tests plus app/instrumentation APK assembly;
- populated PostgreSQL `0006`-copy upgrade to `0007`;
- API/PDF/billing/tax/quote/SMTP-lock/parallel-number acceptance;
- Playwright and axe on both source and restored stacks;
- history-aware secret scan, SBOM, encrypted Restic backup/check, and restore
  into a separately named empty Compose target.

The independent billing/legacy-data/tax/SMTP/backup review ended with no open
P0 or P1. Final exact-head CI, API-35 and post-merge `master` checks are GitHub
evidence and must be read from PR #3 / Actions, not inferred from local results.

## Deployment boundary

Repository documentation contains only `<NUC-IP>` placeholders and no exact
authorized Docker host or access method. No target address may be guessed.
`docs/INTERNAL_DEPLOYMENT_PLAN.md` is the complete stopped deployment plan.
No real data, SMTP provider, offsite repository, deployment host, or release
signing key was supplied or exercised.

## Primary references

- `docs/BILLING_POLICY.md`
- `docs/PILOT_SCOPE.md` and `docs/PILOT_RUNBOOK.md`
- `docs/VERIFICATION_MATRIX.md` and `docs/PILOT_BASELINE.md`
- `docs/operations/INVOICE_OPERATOR_CHECKLIST.md`
- `docs/operations/SMTP_ACCEPTANCE.md`
- `docs/BACKUP_RESTORE.md`
- `docs/INTERNAL_DEPLOYMENT_PLAN.md`
- `.agent/TODO.md`
