# Claude Code Guide

Read `AGENTS.md` first and follow it as the repository-local operating guide.

For continuation work:

1. Inspect `git status`.
2. Read `.agent/STATE.md`.
3. Read `.agent/TODO.md`.
4. Inspect recent relevant commits.
5. Continue the highest-priority unfinished item unless the user specified a
   different task.

Demand-load only when relevant:

- `.agent/DECISIONS.md` for durable product, data, billing, and deployment
  constraints.
- `.agent/ARCHITECTURE.md` for component boundaries and source navigation.
- `README.md` for product scope, setup, and the full validation matrix.
- `docs/BACKUP_RESTORE.md` for business-data recovery and offsite operations.

## Repository-specific caveats

- Do not rename the legacy `tracker` database/user, Docker volumes, or Android
  package as incidental cleanup.
- PostgreSQL data and the document volume form one backup unit.
- Do not claim production, SMTP, backup, or restore health from manifests or CI
  alone; record the evidence and environment actually checked.
- Never expose `.env`, production credentials, customer records, PDFs,
  receipts, backups, restic passwords, or rclone configuration.
- Keep application code and comments in English unless the existing user-facing
  German/English localization requires otherwise.

## Common checks

Use scoped checks first. The canonical commands are in `AGENTS.md` and
`README.md`; CI covers backend tests, frontend tests/build/audit, Compose build
and config, shell syntax, secret scanning, and Android debug assembly.

Before substantial work ends, validate, update `.agent/STATE.md` and
`.agent/TODO.md`, and update decisions or architecture only if they truly
changed. Assume the next session cannot see this conversation.
