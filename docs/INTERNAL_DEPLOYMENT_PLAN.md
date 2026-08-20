# Internal Docker Compose deployment plan

Status on 2026-08-20: **planned, not executed**. Repository documentation names
no exact authorized Docker host or access method. `dashboard/README.md` contains
only the placeholder `<NUC-IP>` and a public dashboard routing example; neither
is authorization or a deployable target. No address is inferred from them.

Deployment stops until the operator records the exact host, access method,
approved Compose directory, proxy/TLS boundary, and encrypted backup target
outside Git.

## Preconditions

- PR #3 is squash-merged and all required CI jobs pass again on `master`.
- The exact merge commit is selected; the checkout/build context is clean.
- The authorized host has adequate disk, Docker Engine, Docker Compose, and an
  approved external `proxy_net` or an explicitly reviewed local-only exposure.
- Production secrets are supplied through protected host configuration and are
  never copied into Git/evidence.
- A complete pre-deployment database/document export exists if upgrading an
  installation; its checksums and restore path are verified.
- Tim has explicitly approved operator identity, address, bank data, payment
  term, invoice prefix, 0-percent rate, and § 19 UStG notice text.

## Immutable build and Compose identity

1. Use one clean Compose project name dedicated to this installation; do not
   reuse source/restore rehearsal project names or volumes.
2. Build backend and frontend from the exact merge commit.
3. Tag every deployable image with the full Git SHA (or an unambiguous SHA-based
   tag) and record the resulting immutable image ID/digest. Do not use `latest`
   as the only reference.
4. Set OCI revision/build-time labels and verify `/api/meta` reports the same
   repository commit.
5. Keep `communication.smtp` disabled. SMTP runtime values should be absent;
   the application lock remains the final control.
6. Start PostgreSQL first, allow the additive migration to reach
   `0007_billing_policy`, then start backend/frontend only after readiness.

## Configuration and shadow flow

Configure the operator profile and verify it in the UI:

- private 50.00 EUR/hour;
- business/individual project 75.00 EUR/hour;
- travel 30.00 EUR/hour;
- first-order and onsite work minimum 60 minutes;
- remote follow-up increment 15 minutes;
- travel minimum 30 minutes and travel increment unset;
- tax rate 0 percent and the explicitly approved § 19 UStG notice;
- operator name/address/bank data/payment term/invoice prefix.

Create only unmistakable synthetic `TESTKUNDE`, `TESTPROJEKT`,
`TESTANGEBOT — NICHT BUCHEN`, and `TESTRECHNUNG — NICHT BUCHEN` objects. Run the
complete flow in `PILOT_RUNBOOK.md`: private remote rounding, business onsite
minimum, separate travel minimum, free quote, billing preview confirmation,
unique invoice number, PDF text/page review and download, SMTP-lock proof,
manual-delivery state only after an approved synthetic external delivery, paid
state, reports and CSV.

Stop on any mismatch in actual/billable minutes, rate, minimum, increment,
travel, tax notice, totals, PDF, number sequence, revision, or image identity.

## Backup and empty-target restore

1. Export PostgreSQL and the complete document volume as one revision-stamped
   unit and verify `MANIFEST.txt` plus checksums.
2. Store the export in the approved encrypted Restic/rclone target; record only
   redacted snapshot evidence.
3. Create a separately named empty Compose installation with new database and
   document volumes.
4. Prove both targets are empty, restore with the explicit empty-target guard,
   and start the restored application at the same commit/schema.
5. Compare all business-table counts, billing snapshots, invoice numbers,
   database revision, repository revision, and sorted document SHA-256
   inventories. Confirm the source was not modified and SMTP emitted nothing.

## Required deployment record

Record outside Git, without secrets or customer data:

- authorized target identity and approval reference;
- Compose project/directory and deployment time UTC;
- merge commit and deployed repository commit;
- exact backend/frontend image tags and immutable image IDs/digests;
- schema revision and readiness result;
- proxy/TLS observation if explicitly authorized;
- synthetic shadow-flow result and deviations;
- export manifest/checksum location;
- encrypted snapshot's redacted ID;
- isolated restore evidence, duration, data-count and document-hash comparison;
- SMTP state (`disabled`) and observed external message count (`0`).

Only after this record passes may real customer/project/time data enter the
installation. A missing target authorization remains an external gate, not a
reason to create or guess infrastructure.
