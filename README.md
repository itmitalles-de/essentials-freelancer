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

- clients with contact data and individual hourly rates;
- projects linked to exactly one client, with an optional project rate;
- manual time entries and one global start/stop timer;
- traceable client → project → time → invoice relationships;
- quotes with line items, PDF, controlled status transitions, and one-time
  conversion of an accepted quote into a draft invoice;
- a deterministic, optional quote assistant with versioned catalog prices,
  packages, templates, transparent Decimal calculations, immutable snapshots,
  and mandatory human approval;
- invoices generated from unbilled time or an accepted quote, with PDF,
  SMTP delivery, and controlled draft/sent/paid/cancelled states;
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

The default invoice footer retains the deployment's existing small-business
wording. It is configurable and is not tax or legal advice; operators are
responsible for validating their own invoice requirements.

## Architecture and persistence

- Backend: FastAPI, SQLAlchemy, Alembic, ReportLab, SMTP
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
# Replace every change-me value with a strong local secret.
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
(`0005`) without renaming legacy compatibility objects. Take a verified
business-data export before deploying a migration.

SMTP is optional. Without `SMTP_HOST` and `SMTP_FROM`, invoice creation and PDF
download remain available while the send endpoint returns a clear configuration
error and leaves the invoice in draft state.

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
before creating and checking an encrypted offsite snapshot.

## Reproducible verification

The primary acceptance entry point is:

```bash
make full-check
```

It creates random synthetic credentials, Compose project names, ports, volumes,
and an isolated proxy network. It runs backend and migration tests, frontend
tests/build/audit, Android JVM tests/debug assembly, Compose/static/secret
checks, the complete API/PDF/SMTP flow, Playwright navigation and axe checks,
business export, an encrypted local restic snapshot, and restore into a second
empty Compose installation. Database counts, document checksums, schema and
repository revisions, restored APIs, and restored browser views are compared.
The trap removes the temporary stacks, volumes, networks, images, credentials,
and artifacts on success or failure.

Required host tools are Docker with Compose, Bash, Python 3, Node.js/npm, JDK 17
plus an Android SDK, `restic`, `pdftotext`, and Chrome/Chromium. CI runs this
same target in addition to the focused jobs.

SMTP and offsite storage in `make full-check` are local simulators. A green run
does not prove delivery by a real SMTP provider, recoverability from a real
remote restic target, public proxy/DNS/TLS, or the revision deployed in
production. See [`docs/VERIFICATION_MATRIX.md`](docs/VERIFICATION_MATRIX.md).
