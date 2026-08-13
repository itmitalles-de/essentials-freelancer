# Freelancer

Focused single-user time tracking, quoting, invoicing, and expense management
for solo professionals. The product consists of a FastAPI/PostgreSQL backend, a
React web application, an Android client for the established mobile flows, and
an optional Homer dashboard.

Freelancer remains a single installation with one administrator. It is not a
multi-tenant SaaS, shop system, inventory tool, or collaboration suite.

## Verified product scope

- clients with contact data and individual hourly rates;
- projects linked to exactly one client, with an optional project rate;
- manual time entries and one global start/stop timer;
- traceable client → project → time → invoice relationships;
- quotes with line items, PDF, controlled status transitions, and one-time
  conversion of an accepted quote into a draft invoice;
- invoices generated from unbilled time or an accepted quote, with PDF,
  SMTP delivery, and controlled draft/sent/paid/cancelled states;
- expenses with PNG, JPEG, or PDF receipts up to 5 MiB;
- company settings, logo, numbering prefixes, and a configurable invoice
  footer;
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
legacy schema only for a new empty database. Migration `0002_projects_quotes`
adds project, quote, and traceability data without renaming or deleting legacy
objects. Take a verified business-data export before deploying a migration.

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

## Verification

The repository CI and local checks cover:

```bash
docker build --target test -t freelancer-backend-test ./backend
docker run --rm freelancer-backend-test
cd frontend && npm ci && npm test && npm run build && npm audit --audit-level=moderate
cd .. && POSTGRES_PASSWORD=local-check JWT_SECRET=local-check ADMIN_PASSWORD=local-check docker compose config -q
bash -n scripts/*.sh
./scripts/check-secrets.sh
cd android && ./gradlew assembleDebug
```

Host-dependent persistence, export/restore, SMTP, and full API smoke tests are
deliberately not simulated in GitHub Actions. Run `scripts/smoke-test.sh` with
test-only credentials against disposable Compose infrastructure for the
customer → project → time → invoice → PDF and quote-conversion flow.
