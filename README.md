# Essentials+ Freelancer

Focused single-user time tracking, quoting, invoicing, and expense management
for solo professionals. The product consists of a FastAPI/PostgreSQL backend, a
React web application, an Android client for the established mobile flows, and
an optional Homer dashboard.

Essentials+ Freelancer remains a single installation with one administrator. It is not a
multi-tenant SaaS, shop system, inventory tool, or collaboration suite.

The canonical private repository is
`itmitalles-de/essentials-freelancer`. Visible product and repository naming is
separate from deliberately retained persistence identifiers; see
[`docs/COMPATIBILITY_IDENTIFIERS.md`](docs/COMPATIBILITY_IDENTIFIERS.md).
The controlled first-internal-use boundary and its exit criteria are frozen in
[`docs/PILOT_SCOPE.md`](docs/PILOT_SCOPE.md).

## Verified product scope

- clients with private/business/custom billing profiles, standard rates, and
  optional service-mode defaults;
- projects linked to exactly one client, with tariff/rate overrides, default
  remote/onsite mode, and individual-project classification;
- manual time entries and one global start/stop timer, with separate actual and
  billable work/travel minutes and applied-policy evidence;
- traceable client → project → time → invoice relationships;
- quotes with line items, PDF, controlled status transitions, and one-time
  conversion of an accepted quote into a draft invoice;
- a deterministic, optional quote assistant with versioned catalog prices,
  packages, templates, transparent Decimal calculations, immutable snapshots,
  and mandatory human approval;
- invoices generated from unbilled time or an accepted fixed-price quote only
  after a visible billing preview and explicit confirmation, with
  immutable line snapshots, PDF, explicit tax selection, manual delivery
  confirmation, and controlled draft/sent/paid/cancelled states;
- expenses with PNG, JPEG, or PDF receipts up to 5 MiB;
- company settings, logo, numbering prefixes, and a configurable invoice
  footer;
- a server-enforced Essentials+ module catalog and grouped Admin Center with
  dependencies, configuration/health states, idempotent audited transitions,
  navigation guards, and non-destructive deactivation;
- filtered operational reporting for time, quote conversion, invoice status and
  amounts, and expenses, including CSV exports without tax or legal advice;
- Android login, time tracking, read-only clients, invoice list/PDF, and paid
  status handling;
- consistent PostgreSQL/document export and empty-target restore tooling.

The application does not infer tax status. The operator can explicitly select
0 percent and enable operator-approved § 19 UStG text; the notice is never
inferred. Existing PDFs and custom footer text remain unchanged. The exact
billing rules and migration behavior are documented in
[`docs/BILLING_POLICY.md`](docs/BILLING_POLICY.md). Defaults and checklists are
not tax or legal advice; see
[`docs/operations/INVOICE_OPERATOR_CHECKLIST.md`](docs/operations/INVOICE_OPERATOR_CHECKLIST.md).

## Architecture and persistence

- Backend: FastAPI, SQLAlchemy, Alembic, ReportLab; dormant SMTP compatibility code is pilot-locked
- Frontend: React, Vite, TypeScript
- Android: Kotlin, Jetpack Compose
- Database: PostgreSQL 16
- Deployment: Docker Compose

Existing internal identifiers remain intentionally stable:

- PostgreSQL database/user: `tracker`
- database volume: `tracker_db_data`
- document volume: `tracker_invoices`
- Android package: `de.itmitalles.tracker`

The database volume stores all relational business data. The document volume
stores invoice PDFs, quote PDFs, company logos, and expense receipts. A valid
backup must contain both.

## Setup

```bash
cp .env.example .env
# Replace every change-me secret and every replace-with provenance placeholder.
docker network inspect proxy_net >/dev/null 2>&1 || docker network create proxy_net
docker compose up -d --build
```

The web application defaults to `http://localhost:8080`; the optional Homer
dashboard defaults to `http://localhost:8081`. Port values are configurable in
`.env`. Dashboard/Caddy details are in
[`dashboard/README.md`](dashboard/README.md).

The backend runs additive Alembic migrations before accepting traffic. Migration
`0001_existing_mvp` safely baselines a complete legacy database and creates the
legacy schema only for a new empty database. Later migrations add projects and
quotes (`0002`), module state/audit data (`0003`), versioned quote-assistant
snapshots (`0004`), and operational constraints, indexes, and idempotency keys
(`0005`). Pilot safety migration `0006` adds invoice-send attempt evidence and
removes the known inferred tax footer without renaming compatibility objects.
Billing migration `0007` adds configurable 50/75/30 deployment tariffs,
minimum/increment rules, explicit tax-profile settings, legacy-profile
confirmation gates, and immutable invoice snapshots without recalculating old
rows or documents. Take a verified business-data export before deploying a
migration.

SMTP is server-locked off for this pilot even when runtime SMTP variables are
present. Invoice creation, PDF review, and download remain available; the
operator sends the reviewed PDF through the normal external mail account and
then explicitly records manual delivery. The application performs no SMTP call
and creates no send-attempt row. Future activation requires the complete
crash-safe contract in
[`docs/operations/SMTP_ACCEPTANCE.md`](docs/operations/SMTP_ACCEPTANCE.md).

## Backup and restore

`scripts/export-business-data.sh` briefly stops the backend writer, exports a
custom-format PostgreSQL dump plus the complete document volume, validates both,
and writes checksums and a repository-revision manifest. It never exports
`.env`. Detailed empty-target restore and encrypted-offsite guidance is in
[`docs/BACKUP_RESTORE.md`](docs/BACKUP_RESTORE.md).

Local exports are written below ignored `backups/` by default. They contain
business data and must not be committed. Offsite encryption, retention, and
credential management use the explicitly configured restic/rclone target. The
optional systemd service and timer in `deploy/` run the same verified export
before creating and checking an encrypted offsite snapshot. Retention/pruning
is opt-in; read-only inventory and the pilot RPO/RTO/restore cadence are defined
in the recovery guide.

## Pilot operations

- [`docs/PILOT_RUNBOOK.md`](docs/PILOT_RUNBOOK.md) is the controlled 22-step
  synthetic and first-use flow.
- [`docs/INTERNAL_DEPLOYMENT_PLAN.md`](docs/INTERNAL_DEPLOYMENT_PLAN.md) is the
  exact-SHA Compose deployment/backup/restore plan and records the missing-host
  stop condition.
- [`docs/operations/SMTP_ACCEPTANCE.md`](docs/operations/SMTP_ACCEPTANCE.md)
  separates the local fixture from the externally gated real-provider test.
- `scripts/collect-deployment-state.sh` writes secret-safe JSON and Markdown
  evidence for the checkout, redacted Compose model, images, containers,
  volumes, schema/application metadata, backup age, restore evidence, and an
  explicitly authorized proxy/TLS endpoint. It never emits Compose environment
  values.
- `make pilot-sbom` generates a CycloneDX SBOM from Python pins, npm lock
  integrity, Gradle verification metadata, image digests, and action SHAs.
- [`docs/GITHUB_REPOSITORY_SETTINGS.md`](docs/GITHUB_REPOSITORY_SETTINGS.md)
  records observed governance and the external branch-protection plan gate.

## Reproducible verification

The primary acceptance entry point is:

```bash
make full-check
```

It creates random synthetic credentials, Compose project names, ports, volumes,
and an isolated proxy network. It runs backend and migration tests, frontend
tests/build/audit, Android JVM tests and app/instrumentation APK assembly,
Python/npm dependency audits, Compose/static/full-history secret checks, SBOM
and deployment-evidence checks, the complete API/PDF/billing/SMTP-lock flow,
an upgrade of a populated PostgreSQL `0006` database copy, Playwright navigation and axe checks,
business export, an encrypted local restic snapshot, and restore into a second
empty Compose installation. Database counts, document checksums, schema and
repository revisions, restored APIs, and restored browser views are compared.
The trap removes the temporary stacks, volumes, networks, images, credentials,
and artifacts on success or failure.

Required host tools are Docker with Compose, Bash, Python 3, Node.js/npm, JDK 17
plus an Android SDK, `restic`, `pdftotext`, and Chrome/Chromium. CI runs this
same target in addition to the focused jobs.

CI also runs the committed instrumentation smoke on an API-35 emulator against
an isolated stack containing only `TESTKUNDE`, `TESTPROJEKT`, `TESTANGEBOT`,
`TESTRECHNUNG`, and `NICHT BUCHEN`. Release signing is intentionally external.

The SMTP fixture in `make full-check` is configured only to prove that the pilot
lock emits no message. Local offsite storage is a simulator. A green run does
not prove manual mail delivery, recoverability from a real remote restic target,
public proxy/DNS/TLS, or the revision deployed in production. See
[`docs/VERIFICATION_MATRIX.md`](docs/VERIFICATION_MATRIX.md).
The current truth for the pilot is recorded without promotion claims in
[`docs/PILOT_BASELINE.md`](docs/PILOT_BASELINE.md).
