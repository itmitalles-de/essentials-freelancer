# Business-data backup and restore

The authoritative business state consists of two parts and is incomplete if
either part is missing:

- the PostgreSQL database in the existing `tracker_db_data` volume;
- invoice PDFs, quote PDFs, logos, and expense receipts in the existing
  `tracker_invoices` volume.

`scripts/export-business-data.sh` briefly stops only the backend writer, takes a
PostgreSQL custom-format dump, archives `/data/invoices`, validates both
archives, writes checksums and a revision manifest, then restores the previous
service state. It deliberately excludes `.env` and every credential. The
default destination is the ignored local `backups/` directory. That directory
contains business data and must never be committed.

## Export and offsite handling

Run the export from the deployment checkout with the production `.env`
present. Move the resulting timestamped directory to encrypted offsite storage
using the organization's approved backup tool. Encryption keys and the `.env`
belong in separate protected secret management, not inside this export or Git.

`scripts/offsite-backup.sh` combines the consistent export with an encrypted
restic snapshot, repository verification, retention, and pruning. It reads
paths and the repository URL from `/etc/freelancer-backup.env`; credentials
remain in the referenced mode-0600 restic password and rclone configuration
files. Provider selection, account provisioning, and real remote evidence stay
deployment-specific.

Once migration `0003_modules` is present, export and offsite scripts enforce
the persisted module states. `export.business_data` must be enabled; an offsite
run additionally requires `backup.offsite`. Deactivation therefore prevents
new host jobs without deleting previous exports, snapshots, or business data.
Databases predating the module table remain exportable so a safety export can
still precede migration.
The environment file itself must also be mode 0600 and owned by the service
user declared in `freelancer-backup.service`.

The deployment includes a daily systemd service/timer and an environment-file
example in `deploy/`. Before enabling the timer, initialize the restic
repository, run the service manually, verify the remote snapshot, and complete
an empty-target restore rehearsal. A successful timer status alone is not a
restore test.

## Restore rehearsal

Restore only on disposable infrastructure with a new Compose project name and
therefore new `tracker_*` volumes. Supply a fresh local `.env` with the same
database name/user and appropriate test-only credentials. Start only `db`, then
run `scripts/restore-business-data.sh <export-directory> --confirm-empty-target`.

The restore script refuses a running backend, a non-empty database, a non-empty
documents volume, or a checksum mismatch. Database readiness uses deadline
polling (180 seconds by default, configurable through
`DATABASE_READY_TIMEOUT_SECONDS`) rather than an assumed startup delay. The
script does not start application traffic afterward. Review the output, start
`backend` and `frontend`, verify `/api/ready`, log in, and execute the customer
→ project → time → invoice → PDF smoke flow. Confirm quote conversion and at
least one receipt download as well.

`make full-check` automates this rehearsal with generated data, a temporary
encrypted local restic repository, and a separately named empty Compose target.
It validates checksums, manifest revision, database counts, APIs, documents, and
browser views after restore. This proves the repository-local procedure only;
it is not evidence for a real remote provider or production host.

For a real disaster recovery, use the repository revision recorded in
`MANIFEST.txt` first. Upgrade only after that revision is healthy. A migration
rollback is not a substitute for restoring the pre-migration export.

## Migration rollback boundary

Migrations `0002` through `0005` are additive and preserve legacy tables, rows,
invoice numbers, database names, and volume names. Their downgrades can remove
newer module, assistant, project/quote, constraint, or idempotency state and are
therefore destructive by definition. Use them only on disposable rehearsal
infrastructure or after taking and verifying a full export. Production rollback
means restoring that export. Migration `0001_existing_mvp` deliberately refuses
downgrade because it may be a baseline over a pre-Alembic database and must
never drop legacy business data.
