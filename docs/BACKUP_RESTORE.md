# Business-data backup and restore

Status on 2026-08-19: the repository-local procedure is synthetically verified; an approved encrypted remote target, protected credentials, real snapshot, and isolated real-target restore were **not provided** and remain an external gate. No cloud resource was created.

## Complete recovery unit

A backup is incomplete unless it contains both:

- the PostgreSQL database in the compatibility volume `tracker_db_data`;
- every invoice PDF, quote PDF, logo, and expense receipt in `tracker_invoices` (`/data/invoices`).

`scripts/export-business-data.sh` stops only the backend writer, waits for database health, creates a PostgreSQL custom-format dump and complete document archive, validates both, writes SHA-256 checksums and a revision manifest, and restores the prior service state. It excludes `.env` and credentials. The ignored local `backups/` directory contains business data and must never enter Git.

## Pilot recovery policy

The following values are the first-pilot operating contract; the designated operator must confirm them before enabling the timer:

- **RPO:** at most 24 hours (one successful complete encrypted snapshot per day).
- **RTO:** four hours from declared restore start to verified application access, subject to remote bandwidth.
- **Retention:** 7 daily, 5 weekly, and 12 monthly snapshots after explicit approval.
- **Responsible role:** the designated single pilot operator; a named substitute must be recorded outside Git.
- **Restore rhythm:** one isolated restore every month and after any material migration/backup-tool change; an untested scheduled job does not satisfy this.

These are operational targets, not proof. Actual measured snapshot age and restore duration must be recorded outside Git.

## Safe offsite acceptance

Credentials and repository URLs live only in `/etc/freelancer-backup.env` and referenced mode-0600 restic/rclone files. Use `deploy/freelancer-backup.env.example` as the configuration contract; never fill it in inside the repository.

1. Confirm authorization for the exact remote target and operator.
2. Inventory the existing repository read-only with `scripts/offsite-backup.sh --inventory-only`. It emits only snapshot count, time, and a redacted snapshot-ID hash; it creates/deletes nothing and changes no retention.
3. Confirm no unrelated repository or retention policy is being targeted.
4. Enable the existing `backup.offsite` module only after configuration readiness is truthful.
5. Run `scripts/offsite-backup.sh`. It creates a consistent export, uploads the timestamped complete export encrypted, runs `restic check`, and reports a redacted snapshot-ID hash.
6. `RESTIC_APPLY_RETENTION=false` is the safe default. Do not change existing retention during first acceptance. Set it to `true` only after the documented policy is independently approved.
7. If `BACKUP_EVIDENCE_FILE` points outside Git, the script writes a mode-protected machine-readable record containing the snapshot ID, UTC completion, repository-check outcome, and whether retention ran. It contains no repository URL or credential.
8. Restore the exact snapshot into a new isolated Compose project and new `tracker_*` volumes. Never target the source volumes.
9. Compare every business/evidence-table count, sorted document SHA-256 inventory, schema revision, and application/repository revision.
10. Record measured RPO/RTO and deviations, then remove only the isolated test installation. Leave the source and remote snapshot untouched.

The daily systemd unit/timer in `deploy/` must remain disabled until the first real snapshot and isolated restore pass. A successful timer status alone is not recovery evidence.

## Restore rehearsal

Prepare a new Compose project with fresh credentials and volumes. Start only `db`, then invoke `scripts/restore-business-data.sh <export-directory> --confirm-empty-target`.

The restore script refuses a running backend, non-empty database, non-empty document volume, or checksum mismatch. It uses health/deadline checks rather than assumed startup sleeps and does not start application traffic after restoration. Then:

1. review restore output;
2. start backend/frontend;
3. verify `/api/ready` and `/api/meta` against the intended SHA/schema/build;
4. collect JSON/Markdown deployment evidence;
5. log in and exercise customer → project → time → quote → invoice → PDF plus one receipt;
6. compare all database counts, including `invoice_send_attempts`;
7. compare sorted document SHA-256 inventories and export `SHA256SUMS`;
8. write a protected restore-evidence JSON outside Git.

The optional restore-evidence file consumed by `collect-deployment-state.py` has only this allowlist:

```json
{
  "completed_at_utc": "UTC timestamp",
  "source_repository_commit": "40-character commit",
  "target_repository_commit": "40-character commit",
  "database_counts_match": true,
  "document_hashes_match": true,
  "isolated_target": true,
  "result": "passed"
}
```

`make full-check` automates the same shape using generated data, a temporary encrypted local restic repository, and a separate empty target. It verifies checksums, revision, tables/APIs/documents/browser views, and cleanup. A local restic repository is not a real offsite result.

## Rollback boundary

Migrations `0002` through `0006` preserve compatibility IDs and existing business documents on upgrade. `0006_pilot_safety` adds invoice-send evidence and clears only the exact known footer sentence formerly injected automatically; custom footer text is retained. Downgrades can discard newer state and are not production rollback. Restore the complete database/document export at the revision in `MANIFEST.txt`; upgrade only after that revision is healthy. The legacy baseline refuses destructive downgrade.
