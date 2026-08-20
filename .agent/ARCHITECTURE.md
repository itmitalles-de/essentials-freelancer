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
  the SMTP route remains unreachable behind the first-pilot lock.
- **Web (`frontend/`)**: React/Vite/TypeScript SPA for all main product areas.
  Its Nginx runtime serves static assets and proxies `/api/` to `backend:8000`.
- **Android (`android/`)**: Compose client using Retrofit. It stores the server
  URL/theme in DataStore and the JWT in encrypted preferences. Its scope is
  smaller than the web UI: login, time, client viewing, and invoice/PDF/status.
- **Dashboard (`dashboard/`)**: optional Homer container configured from
  read-only, browser-visible assets. It is navigation, not application state.
- **Operations (`scripts/`, `deploy/`)**: smoke testing, secret scanning,
  read-only deployment evidence, consistent export/restore, encrypted offsite
  upload, CycloneDX pilot SBOM generation, and optional systemd scheduling.
- **Acceptance (`tests/full-check/`, `frontend/e2e/`)**: generated-data
  API/PDF/billing and zero-message SMTP-lock fixtures plus Playwright/axe,
  populated prior-schema-copy migration, and deployment-evidence checks
  orchestrated by `make full-check`; `tests/android-smoke/` seeds the dedicated
  API-35 workflow.

## Data flow and responsibilities

The web browser reaches Nginx, which serves the SPA and forwards API requests to
FastAPI. The Android client reaches the same externally published API path.
FastAPI authenticates bearer tokens, applies business rules, writes PostgreSQL,
and writes generated/uploaded files below `/data/invoices`.

Core business relationships are implemented in `backend/app/models.py`:

- each project belongs to one client;
- time entries belong to a client and optionally a project;
- invoices link billed time entries and immutable line-item billing-policy,
  project/date/duration/rate/tax/amount snapshots;
- quotes belong to a client/project and can create one linked draft invoice;
- expenses may reference uploaded receipts;
- singleton company settings own prefixes, counters, defaults, and logo path.
- module installations and audit events own the server-enforced Essentials+
  feature state; manifests themselves remain version-controlled code;
- quote-assistant catalogs, versions, packages, templates, drafts, and line/tax
  snapshots retain deterministic inputs independently of later catalog edits;
- legacy invoice-send attempts remain retained evidence, but no new attempt can
  be created while the first-pilot SMTP module is locked.

The billing-policy service resolves configurable client/project rates and
service modes when time is recorded. It stores actual/billable work and travel
minutes, minima, increments, reasons and a policy ID. Invoicing from time first
returns an exact preview and confirmation token. Creation locks selected
entries, rejects running/already-billed/cross-client/stale-preview requests,
calculates money directly from billable minutes with Decimal cent rounding,
snapshots every decision, links entries, and generates its PDF in one
transaction boundary. PDF failure rolls database state back and removes the
expected file. Deleting an unsent draft unbills its time; sent/paid/cancelled
documents cannot follow that path. Quote conversion uses row locks and unique
links to prevent duplicate conversion and never creates time for quote work.

SMTP is forced to `disabled` by migration, registry reconciliation, module
enable guard and route guard. Even configured runtime SMTP values cannot emit a
message. The web client opens/downloads the PDF and records `sent` only after
the operator explicitly attests PDF review and completed manual external
delivery. This never sets `paid`. Future SMTP activation requires the complete
`send_unknown` crash-safety contract in `docs/operations/SMTP_ACCEPTANCE.md`.

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
current production runtime. Build arguments and OCI labels carry product
version, Git revision, and build time. `/api/meta` exposes only the public
allowlist of product/version/revision/schema/build/readiness fields.
`scripts/collect-deployment-state.sh` reads Compose/runtime state without
mutation and emits secret-redacted mode-0600 JSON plus Markdown; optional
proxy/TLS probing must be explicitly authorized.

## Persistence and recovery

- `tracker_db_data`: all relational users, settings, customers, projects, time,
  quotes, quote-assistant versions/snapshots, invoices, line items, expenses,
  module state/audit, invoice-send attempts, and idempotency records.
- `tracker_invoices`: invoice/quote PDFs, company logos, and expense receipts.

Both volumes are required for recovery. `scripts/export-business-data.sh`
creates and verifies a database dump, document archive, checksums, and revision
manifest. `scripts/restore-business-data.sh` accepts only an explicitly
confirmed empty target. Offsite encryption credentials remain in protected host
configuration, never in Git. Offsite inventory is read-only and retention
remains dry-run unless explicitly enabled; real acceptance restores into new
database and document volumes, never the source.

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

- `backend/tests/`: auth/business/module/assistant/reporting/security/schema
  tests, including billing-rule matrices, migration/history preservation,
  invoice rounding/numbering/snapshots, PDF/footer and SMTP-lock behavior.
- `frontend/tests/`: 9 component/API test files with 11 tests plus
  TypeScript/Vite build validation; `frontend/e2e/` covers authenticated module
  navigation, restored data, and axe accessibility checks.
- `android/app/src/test/`: 3 JVM tests including authenticated-client cache
  behavior; CI assembles both app and instrumentation APKs.
- `android/app/src/androidTest/`: API-35 Compose smoke for the authenticated
  synthetic pilot flow and Activity recreation.
- `tests/full-check/`: complete generated API/PDF/billing/SMTP-lock flow,
  PostgreSQL concurrency, a populated `0006` database-copy upgrade,
  deployment-evidence redaction and a programmable local SMTP fixture that
  must remain empty.
- `scripts/full-check.sh`: random disposable source/restore stacks, export,
  encrypted local restic snapshot/restore, count/checksum/revision comparison,
  and reliable cleanup.
- `.github/workflows/ci.yml`: focused backend/frontend/Compose/Android jobs, the
  same full acceptance target, SBOM artifact, and API-35 emulator smoke. All
  external Actions are pinned to full commit SHAs.

No automated repository test proves manual mail delivery, remote offsite
storage, public proxy/DNS/TLS, production data, deployed revision, or Android
release signing.

## Important constraints

- Do not rename legacy `tracker` identifiers without a dedicated migration.
- Do not infer production state from Compose or CI.
- Do not downgrade the legacy baseline on real data; restore a verified export.
- Preserve billing invariants summarized in `.agent/DECISIONS.md`.
- Do not infer tax status or enable SMTP without the complete crash-safe contract.
- Do not describe CI/local fixtures as deployed, manually delivered, or real-offsite
  evidence.
- Demand-load only the router/page/client involved in the current task.
