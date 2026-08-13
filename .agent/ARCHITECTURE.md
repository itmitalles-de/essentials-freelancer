# Architecture

## Overview

Freelancer is a Docker Compose application with a FastAPI/PostgreSQL backend, a
React web client, a Kotlin Android client, and an optional Homer dashboard.
`README.md` is the authoritative product/setup overview and
`docs/BACKUP_RESTORE.md` is the authoritative recovery guide; this file is a
navigation map, not a duplicate specification.

## Components

- **Backend (`backend/`)**: FastAPI routers expose `/api`; SQLAlchemy models and
  Alembic migrations own persistence; ReportLab creates invoice/quote PDFs;
  SMTP sends invoice attachments when configured.
- **Web (`frontend/`)**: React/Vite/TypeScript SPA for all main product areas.
  Its Nginx runtime serves static assets and proxies `/api/` to `backend:8000`.
- **Android (`android/`)**: Compose client using Retrofit. It stores the server
  URL/theme in DataStore and the JWT in encrypted preferences. Its scope is
  smaller than the web UI: login, time, client viewing, and invoice/PDF/status.
- **Dashboard (`dashboard/`)**: optional Homer container configured from
  read-only, browser-visible assets. It is navigation, not application state.
- **Operations (`scripts/`, `deploy/`)**: smoke testing, secret scanning,
  consistent export/restore, encrypted offsite upload, and optional systemd
  scheduling.

## Data flow and responsibilities

The web browser reaches Nginx, which serves the SPA and forwards API requests to
FastAPI. The Android client reaches the same externally published API path.
FastAPI authenticates bearer tokens, applies business rules, writes PostgreSQL,
and writes generated/uploaded files below `/data/invoices`.

Core business relationships are implemented in `backend/app/models.py`:

- each project belongs to one client;
- time entries belong to a client and optionally a project;
- invoices link billed time entries and immutable line-item amounts;
- quotes belong to a client/project and can create one linked draft invoice;
- expenses may reference uploaded receipts;
- singleton company settings own prefixes, counters, defaults, and logo path.

Invoicing from time locks selected entries, rejects running/already-billed or
cross-client entries, computes Decimal amounts, links them to the invoice, and
generates its PDF in one transaction boundary. PDF failure rolls database state
back and removes the expected file. Deleting an unsent draft unbills its time;
sent/paid/cancelled documents cannot follow that path. Quote conversion uses
row locks and unique links to prevent duplicate conversion.

## Runtime and deployment

`docker-compose.yml` defines:

- PostgreSQL 16 on the internal default network;
- FastAPI on the internal network, with migrations run before traffic;
- Nginx/React on the internal network and external `proxy_net`, plus an optional
  configurable host port;
- Homer on `proxy_net` and an optional configurable host port.

The reverse proxy itself and public DNS/TLS lifecycle are outside this
repository. `dashboard/README.md` documents the current Caddy integration
example. Repository manifests describe desired deployment but do not prove the
current production runtime.

## Persistence and recovery

- `tracker_db_data`: all relational users, settings, customers, projects, time,
  quotes, invoices, line items, and expenses.
- `tracker_invoices`: invoice/quote PDFs, company logos, and expense receipts.

Both volumes are required for recovery. `scripts/export-business-data.sh`
creates and verifies a database dump, document archive, checksums, and revision
manifest. `scripts/restore-business-data.sh` accepts only an explicitly
confirmed empty target. Offsite encryption credentials remain in protected host
configuration, never in Git.

## Authentication and security boundaries

Startup seeds the configured administrator when absent. Login issues a JWT used
for protected routes. This is a single-admin system, not tenant isolation.
Secrets enter through `.env` or protected offsite host files. Uploaded receipts
are size/type constrained by the backend, and all business exports are
sensitive. Homer assets are public to the browser and may contain no secrets.

## Testing

- `backend/tests/`: auth/clients, time/invoices, projects/quotes, expenses, and
  migration behavior in the backend test image.
- `frontend/tests/`: API, login, invoice, and quote flows plus TypeScript/Vite
  build validation.
- `.github/workflows/ci.yml`: backend, frontend, Compose/static, and Android
  assembly jobs.
- `scripts/smoke-test.sh`: disposable API/PDF flow through client, project,
  time, invoice, and quote conversion.

CI does not simulate production volumes, SMTP, proxy/DNS, offsite recovery, or
an empty-target restore. Android has assembly coverage but no committed
behavioral test suite.

## Important constraints

- Do not rename legacy `tracker` identifiers without a dedicated migration.
- Do not infer production state from Compose or CI.
- Do not downgrade the legacy baseline on real data; restore a verified export.
- Preserve billing invariants summarized in `.agent/DECISIONS.md`.
- Demand-load only the router/page/client involved in the current task.
