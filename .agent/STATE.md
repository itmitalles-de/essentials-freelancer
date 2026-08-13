# Current State

## Product boundary

Essentials+ Freelancer is a focused single-installation product for exactly one
administrator. It manages clients, projects, time, quotes, invoices, expenses,
operational reports, and complete business-data recovery. It is not a
multi-tenant service, team system, shop, inventory tool, or groupware suite.

The legacy PostgreSQL database/user `tracker`, volumes `tracker_db_data` and
`tracker_invoices`, browser storage keys, and Android package
`de.itmitalles.tracker` remain compatibility identifiers. Visible branding is
`Essentials+ Freelancer`.

## Baseline and workstream

- Baseline/default branch at work start: `master` at
  `31421a8b6a56f19dc4b45bb75ff3cf548544c809` (agent-context documentation),
  based on product stabilization merge `ed28b555cd6e521fd96eb19ab6e2100f90d1e63f`
  (PR #1, 2026-08-13).
- Baseline evidence: the existing focused backend, frontend, Compose/static and
  Android checks were green locally and in the GitHub CI run for that revision.
- No open issue or pull request existed when this workstream started.
- Active implementation branch: `agent/essentials-freelancer-autonomous`.
- Production data, `.env`, backups, receipts, PDFs, and production accounts were
  deliberately not read.

## Implemented on the active branch

- Repository-local Essentials+ module manifests with stable IDs, manifest
  schema versions, product/schema compatibility, type/group/required/default
  state, dependencies/conflicts, configuration and secret requirements,
  API/navigation/job boundaries, health, data ownership, and lifecycle/export/
  backup/restore behavior.
- Persisted module states `not_installed`, `needs_configuration`, `disabled`,
  `enabled`, and `degraded`; server-side route guards; dependency enforcement;
  idempotent audited state changes; data-preserving deactivation; navigation
  guards; grouped Admin Center; secret-status-only API responses; and host job
  enforcement for export/offsite backup.
- Optional deterministic quote assistant with versioned service/material/travel
  prices, units, validity, taxes, packages, templates, guided inputs, complete
  Decimal calculation steps, surcharge/discount/tax breakdown, immutable
  snapshots, explicit approval, and one-time transfer into the existing quote
  model. It has no AI/provider/OCR/GAEB/procurement behavior.
- Operational reporting by period/client/project/category for captured and
  unbilled time, quote conversion, invoice states/open/paid amounts, and
  expenses, with matching filtered CSV exports and no tax/legal conclusions.
- Operational hardening: additive constraints/indexes, idempotency keys for
  timer/invoice/assistant commands, global timer concurrency handling,
  pagination/filtering, structured errors, liveness/readiness/meta endpoints,
  request IDs/security headers, route-template logs without bodies/query data,
  login/SMTP rate limits, and signature-aware PNG/JPEG/PDF validation.
- Visible web/Android/dashboard/API branding is Essentials+ Freelancer while
  legacy persistence/package identifiers remain unchanged.
- `make full-check` builds random disposable source and restore stacks, uses
  generated secrets/data, runs every focused suite/build/static check, exercises
  API/PDF/SMTP and Playwright/axe flows, creates/verifies an encrypted local
  restic snapshot, restores into an empty target, compares database counts,
  checksums and revisions, and cleans stacks/volumes/networks/images/artifacts.
- CI retains focused jobs and adds the same full acceptance target; Android CI
  now runs the committed JVM test before debug assembly.

## Schema and data compatibility

- `0001_existing_mvp`: safe legacy baseline/new-database schema.
- `0002_projects_quotes`: projects, quotes, line items, and source links.
- `0003_modules`: module installations and audit events.
- `0004_quote_assistant`: catalog/package/template versions and immutable draft
  snapshots.
- `0005_operational_hardening`: idempotency columns/uniques, reporting indexes,
  timer uniqueness, and business constraints.

All new migrations are additive on upgrade. Existing business data and legacy
names are preserved. Downgrades of post-baseline migrations can discard newer
state and are not the production rollback mechanism; use a verified complete
database/document restore.

## Automated evidence

The final handoff revision passes `make full-check` with:

- 36 backend tests and migration/schema regression;
- 8 frontend tests, TypeScript production build, and zero moderate-or-higher
  npm audit findings;
- Android JVM unit test and debug APK assembly;
- Compose configuration, shell syntax, ShellCheck, Python compile, and tracked
  secret scan;
- complete generated API flow, machine-readable quote/invoice PDF assertions,
  SMTP success/repeat/reject/timeout/disconnect behavior, and failed-send state
  preservation;
- Playwright authenticated navigation/restored-data checks and serious/critical
  axe scans;
- business export, checksums/revision manifest, local encrypted restic check and
  restore, empty-target application restore, and source/target count/API/browser
  comparison.

The local SMTP fixture and local restic repository are simulators, not external
production proof. The detailed boundary is in `docs/VERIFICATION_MATRIX.md`.

## External unknowns

- The actual production revision, health, volume state, public proxy/DNS/TLS,
  and deployment configuration were not inspected.
- Real SMTP authentication, provider acceptance, routing, reputation, spam
  handling, and recipient delivery are unproved.
- No real remote restic/rclone/S3 provider, retention policy, credential path,
  scheduled service, or remote restore has been verified.
- Android device/emulator behavior and release signing are not covered by the
  JVM/build checks.

## Relevant commits

- `a1464f8` — Essentials+ module contract and Admin Center.
- `d93d997` — deterministic versioned quote assistant.
- `59245b0` — operational reporting and hardening.
- `d9fc645` — disposable full product acceptance and CI integration.

See the active branch log and Draft PR for subsequent acceptance/documentation
commits and CI status.

## Primary references

- `README.md`: product scope, compatibility, setup, and full-check entry point.
- `docs/VERIFICATION_MATRIX.md`: evidence by test layer and external gaps.
- `docs/BACKUP_RESTORE.md`: complete recovery unit and restore procedure.
- `docs/NICE_TO_HAVE.md`: deferred ideas only; not an active backlog.
- `backend/app/module_registry.py`: module contract source of truth.
- `backend/migrations/versions/`: additive schema history.
- `scripts/full-check.sh`: disposable acceptance orchestration.
- `.agent/TODO.md`: only actionable continuation and externally blocked work.
