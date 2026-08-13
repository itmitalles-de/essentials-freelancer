# TODO

This is the repository's authoritative task and continuation source. GitHub
issues were empty at the 2026-08-13 handoff; add links here if an external task
source becomes authoritative.

## Now

- [ ] On disposable Compose infrastructure with test-only credentials, run the
  complete `scripts/smoke-test.sh` flow and a fresh business-data export followed
  by the empty-target restore rehearsal in `docs/BACKUP_RESTORE.md`. Record the
  date, revision, and outcome in `.agent/STATE.md`.

## Next

- [ ] Once an approved offsite target and deployment access exist, initialize
  and verify the restic repository, run `freelancer-backup.service` manually,
  confirm the remote snapshot, rehearse a restore, and only then enable or trust
  `freelancer-backup.timer`.
- [ ] Exercise invoice SMTP delivery and failure handling against a safe test
  server before recording that path as production-proven.

## Later

- [ ] Add focused Android unit or instrumentation coverage when a mobile core
  flow is next changed; current automation assembles the debug APK only.

## Blocked

- [ ] Confirm the deployed production revision, service health, volume state,
  proxy/DNS path, and latest recoverable offsite snapshot. Blocked on authorized
  production access and deployment-specific evidence.

## Recently completed

- [x] Add CI, backend/frontend tests, migrations, projects, quotes, invoice
  traceability, and guarded core workflows (`afc2e45`, 2026-08-13).
- [x] Add consistent PostgreSQL/document export and empty-target restore tooling
  (`afc2e45`, 2026-08-13).
- [x] Add encrypted offsite backup automation and systemd scheduling assets
  (`42b030b`, `52ab610`, 2026-08-13).
- [x] Replace the generic root handoff with this single persistent task source.
