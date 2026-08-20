# Agent Guide

## Purpose and product boundary

Freelancer is the primary single-user product for solo professionals. It owns
clients, projects, time tracking, quotes, invoices, expenses, and simple
business-data exports.

- Keep it a single installation with one administrator; do not introduce
  multi-tenancy or a framework rewrite without an explicit request.
- Product catalog, inventory, orders, and e-commerce belong in Shop Suite.
- Files, mail, office, Talk, and groupware belong in Workspace Suite.
- Internal `tracker` identifiers are compatibility boundaries. Do not casually
  rename the PostgreSQL database/user, volumes, or Android package.

## Startup

1. Inspect `git status` and preserve all existing worktree changes.
2. Read `.agent/STATE.md` for verified current reality.
3. Read `.agent/TODO.md` when continuing existing work.
4. Read `.agent/DECISIONS.md` and `.agent/ARCHITECTURE.md` only when relevant.
5. Inspect the specific implementation area required by the task.
6. Use `README.md` and `docs/BACKUP_RESTORE.md` as the authoritative product
   and recovery guides; do not reproduce them in agent state.

For a vague continuation request, inspect recent relevant commits and continue
the highest-priority unfinished item in `.agent/TODO.md` unless the user names a
different task. Do not redo completed work.

## Architecture map

- `backend/`: FastAPI, SQLAlchemy, Alembic, ReportLab, SMTP, and backend tests.
- `frontend/`: React/Vite/TypeScript web UI and Vitest tests.
- `android/`: Kotlin/Jetpack Compose client for established mobile flows.
- `dashboard/`: optional static Homer dashboard; its browser-visible config
  must never contain credentials.
- `docker-compose.yml`: PostgreSQL, backend, frontend, dashboard, volumes, and
  the external `proxy_net` boundary.
- `scripts/`: smoke, secret, export, restore, and encrypted-offsite tooling.
- `deploy/`: optional systemd offsite-backup service and timer.

Demand-load more detail from `.agent/ARCHITECTURE.md` and the linked source
files. Do not load every UI, router, test, or Android file by default.

## Data and billing safety

- The database and document volume together are the authoritative business
  state; a backup containing only one is incomplete.
- Preserve invoice and quote numbering, billed-time links, totals, one-time
  quote conversion, and controlled status transitions.
- Use migrations for data-model changes. Take and verify a complete export
  before deployment; never treat destructive migration downgrade as a
  production rollback.
- Never commit `.env`, tokens, credentials, real customer data, exports,
  receipts, generated PDFs, or backup encryption material.
- Do not make tax or legal claims. The configurable invoice footer remains the
  operator's responsibility.

## Context hygiene

- Prefer targeted `rg`, narrow file reads, scoped diffs, and focused tests.
- Avoid recursive repository ingestion, giant log dumps, lockfile output, and
  rereading already-understood large files.
- Run the smallest relevant test first, then broaden validation in proportion
  to risk.
- Use isolated or subagent investigations where supported only for large,
  independent explorations, and return concise findings.
- Record durable verified findings in `.agent/STATE.md`; record future work only
  in `.agent/TODO.md`, not solely in chat.
- Keep planned, implemented, and production-verified behavior distinct.

## Simple Business UI contract

For every product-owned web or Android UI change, first read the canonical,
version-pinned Simple Business contract named in
`.simple-business-design-system.json`. In the standard sibling checkout, the
authoritative files are under `../simple-business-design-system/docs/design-system/`.
Do not duplicate or reinterpret those rules in this repository.

The central contract governs the shared shell, color/tokens, flat construction,
sidebar/drawer behavior, settings anatomy, theme control, icon semantics, and
five-direction comparison. Existing UI is legacy until migrated; do not add new
violations. Package/lint activation remains gated by the central consumer
manifest and must use an exact released version, never a floating branch, CDN,
or runtime download.

## Validation

Choose the checks relevant to the change:

```bash
docker build --target test -t freelancer-backend-test ./backend
docker run --rm freelancer-backend-test
cd frontend && npm ci && npm test && npm run build && npm audit --audit-level=moderate
cd .. && POSTGRES_PASSWORD=local-check JWT_SECRET=local-check ADMIN_PASSWORD=local-check docker compose config -q
bash -n scripts/*.sh
./scripts/check-secrets.sh
cd android && ./gradlew assembleDebug
```

For runtime behavior, use disposable infrastructure and test-only credentials
with `scripts/smoke-test.sh`. Follow `docs/BACKUP_RESTORE.md` for export and
empty-target restore rehearsal. Do not run recovery tests against production.

## Handoff

Before ending substantial work:

1. Validate the changed behavior and inspect the final diff.
2. Update `.agent/STATE.md` with concise verified reality.
3. Update `.agent/TODO.md`, preserving exactly one authoritative task source.
4. Record a durable decision in `.agent/DECISIONS.md` only when one was made.
5. Update `.agent/ARCHITECTURE.md` only when implemented architecture changed.

Assume the next session has no useful memory of the current conversation.

When visible context use grows to roughly 50-70%, prefer reaching a coherent
stopping point, validating, updating the handoff, and continuing in a fresh
session. Do not interrupt an atomic change merely to meet a percentage.
