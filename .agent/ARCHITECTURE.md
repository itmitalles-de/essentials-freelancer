# Architecture

## Overview

Essentials+ Freelancer is a Docker Compose application with a FastAPI/PostgreSQL backend, a
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
- **Acceptance (`tests/full-check/`, `frontend/e2e/`)**: generated-data API/PDF
  and SMTP fixtures plus Playwright/axe checks orchestrated by `make full-check`.

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
- module installations and audit events own the server-enforced Essentials+
  feature state; manifests themselves remain version-controlled code;
- quote-assistant catalogs, versions, packages, templates, drafts, and line/tax
  snapshots retain deterministic inputs independently of later catalog edits.

Invoicing from time locks selected entries, rejects running/already-billed or
cross-client entries, computes Decimal amounts, links them to the invoice, and
generates its PDF in one transaction boundary. PDF failure rolls database state
back and removes the expected file. Deleting an unsent draft unbills its time;
sent/paid/cancelled documents cannot follow that path. Quote conversion uses
row locks and unique links to prevent duplicate conversion.

Protected routers call the module guard after authentication. Optional
navigation is derived from the same authenticated module catalog. Host-side
export/restic jobs query persisted module state after database readiness; the
Admin Center changes state but never runs shell commands. Module deactivation
blocks new owned operations and jobs while leaving rows and documents intact.

Operational reports are read models computed from existing time, quote,
invoice, project/client, and expense tables. Filtered CSV endpoints use the
same filters and do not create a parallel reporting store.

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
  quotes, quote-assistant versions/snapshots, invoices, line items, expenses,
  module state/audit, and idempotency records.
- `tracker_invoices`: invoice/quote PDFs, company logos, and expense receipts.

Both volumes are required for recovery. `scripts/export-business-data.sh`
creates and verifies a database dump, document archive, checksums, and revision
manifest. `scripts/restore-business-data.sh` accepts only an explicitly
confirmed empty target. Offsite encryption credentials remain in protected host
configuration, never in Git.

## Authentication and security boundaries

Startup seeds the configured administrator when absent. Login issues a JWT used
for protected routes. This is a single-admin system, not tenant isolation.
Secrets enter through `.env` or protected offsite host files. Module API
responses contain requirement keys and configured booleans, never values.
Uploaded receipts are bounded and checked against allowed extension, declared
MIME, and file signature. API responses add request IDs/security headers and
structured errors; rate limits cover login and SMTP send. Logs record route
templates rather than query strings or request bodies. All business exports are
sensitive. Homer assets are public to the browser and may contain no secrets.

## Testing

- `backend/tests/`: 36 auth/business/module/assistant/reporting/security/schema
  tests, including migration and concurrency/idempotency behavior.
- `frontend/tests/`: component/API/calculation tests plus TypeScript/Vite build
  validation; `frontend/e2e/` covers authenticated module navigation, restored
  data, and axe accessibility checks.
- `android/app/src/test/`: focused JVM compatibility tests; CI also assembles the
  debug APK.
- `tests/full-check/`: complete generated API/PDF/SMTP flow and a programmable
  local SMTP fixture.
- `scripts/full-check.sh`: random disposable source/restore stacks, export,
  encrypted local restic snapshot/restore, count/checksum/revision comparison,
  and reliable cleanup.
- `.github/workflows/ci.yml`: focused backend/frontend/Compose/Android jobs plus
  the same full acceptance target.

No automated repository test proves a real SMTP provider, remote offsite
storage, public proxy/DNS/TLS, production data, or the deployed revision.

## Important constraints

- Do not rename legacy `tracker` identifiers without a dedicated migration.
- Do not infer production state from Compose or CI.
- Do not downgrade the legacy baseline on real data; restore a verified export.
- Preserve billing invariants summarized in `.agent/DECISIONS.md`.
- Demand-load only the router/page/client involved in the current task.
