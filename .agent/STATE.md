# Current State

## Project goal

Provide a focused, reliable single-user application for solo professionals to
manage clients, projects, time, quotes, invoices, expenses, and recoverable
business data. Freelancer is not a multi-tenant service, shop system, or
groupware suite.

## Current status

- Default branch: `master`.
- Inspected baseline: `ed28b555cd6e521fd96eb19ab6e2100f90d1e63f`
  (`Merge pull request #1 from .../agent/freelancer-mvp-stabilization`,
  2026-08-13).
- The GitHub `CI` run for that revision completed successfully on 2026-08-13.
- No open GitHub issues or pull requests were present at this handoff.
- The repository contains no recorded active implementation workstream.
- Deployed production revision and runtime health were not inspected; repository
  and CI state must not be treated as proof of production state.

## Working

- FastAPI/SQLAlchemy backend provides authenticated client, project, time,
  quote, invoice, expense, settings, PDF, and optional SMTP flows.
- React/Vite web UI covers the main desktop flows; Nginx serves the SPA and
  proxies `/api/` to the backend service.
- Android Compose client covers login, time tracking, read-only clients,
  invoice listing/PDF download, and marking eligible invoices paid.
- Alembic baselines complete legacy databases and adds projects, quotes, and
  traceability without renaming legacy data objects.
- Docker Compose defines PostgreSQL 16, backend, frontend, and optional Homer
  dashboard services.
- Export/restore scripts handle PostgreSQL plus the full document volume;
  restic/rclone and systemd assets support optional encrypted offsite backups.

## Active work

No active repository-specific implementation work is recorded. Continue the
highest-priority verified operational task in `.agent/TODO.md` unless the user
specifies another task.

## Recently completed

- Stabilized the MVP with CI, backend and frontend tests, migrations, projects,
  quotes, invoice traceability, guarded status transitions, safer uploads, and
  verified export/restore tooling (`afc2e45`, 2026-08-13).
- Added encrypted restic/rclone offsite automation and systemd units, then fixed
  export discovery (`42b030b`, `52ab610`, 2026-08-13).
- Merged the stabilization branch through PR #1 (`ed28b55`, 2026-08-13).
- Replaced the generic root handoff with the `.agent/` continuation workflow.

## Known issues

- A disposable end-to-end Compose smoke run and an empty-target restore
  rehearsal are required operational checks but have no result recorded here.
- CI deliberately does not prove host-volume persistence, SMTP delivery,
  production proxy/DNS behavior, offsite snapshot recovery, or the full API
  smoke flow.
- Offsite provider initialization, production timer enablement, and remote
  restore status are unknown and require deployment-specific evidence.
- Android currently has build coverage in CI but no committed unit or
  instrumentation tests.
- The default small-business invoice footer is configurable and is not tax or
  legal advice; operators must validate their own requirements.

## Next recommended tasks

1. Run the disposable smoke and empty-target export/restore rehearsal described
   in `.agent/TODO.md` and `docs/BACKUP_RESTORE.md`.
2. With approved deployment access, verify the encrypted offsite repository,
   manual service execution, retained snapshot, and restore before enabling or
   trusting the timer.
3. Exercise SMTP against a safe test server before describing invoice delivery
   as production-proven.

## Relevant files

- `README.md`: authoritative product scope, setup, persistence, and validation.
- `docs/BACKUP_RESTORE.md`: authoritative recovery and offsite procedure.
- `docker-compose.yml`: service, volume, port, and network topology.
- `backend/app/models.py`: persisted entities and core relationships.
- `backend/app/routers/invoices.py`: billed-time and invoice state behavior.
- `backend/app/routers/quotes.py`: quote lifecycle and one-time conversion.
- `backend/migrations/versions/`: compatibility-preserving schema history.
- `frontend/src/App.tsx`: web routes; `frontend/src/pages/`: user workflows.
- `android/app/src/main/java/de/itmitalles/tracker/`: mobile client.
- `.github/workflows/ci.yml`: current automated checks.
- `scripts/` and `deploy/`: smoke, backup, restore, and scheduling assets.

## Validation

Verified during the 2026-08-13 stabilization and merge:

- GitHub CI: backend tests, frontend tests/build/audit, Compose validation/build,
  shell syntax, secret scan, and Android debug assembly all passed at `ed28b55`.

For this documentation migration, run lightweight path, formatting, link,
secret-pattern, and repository-diff checks. Runtime claims above remain limited
to the evidence explicitly stated.

## Last handoff

2026-08-13: migrated the generic root `TODO.md` into the compact persistent
agent-state system. No prior concrete task was lost; the old handoff stated only
that no repository-specific goal was active.
