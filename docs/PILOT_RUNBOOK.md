# First internal pilot runbook

This runbook is the controlled path for one administrator using one installation. It supports a fully synthetic rehearsal and a later manual run with the operator's own authorized data. It does not authorize customer email, production deployment, or creation of cloud resources.

## Stop conditions and evidence language

Stop immediately on a revision mismatch, dirty deployment checkout, failed readiness, unexpected recipient, reused invoice number, missing document, failed export checksum, non-empty restore target, or ambiguous tax/operator data.

Keep evidence explicitly separated as `implemented`, `synthetically tested`, `tested in CI`, `tested on API-35 emulator`, `manually delivered`, `tested with real offsite target`, `productively deployed`, or `unknown`. Synthetic success never advances a real-service category.

The synthetic objects are always unmistakable:

- customer: `TESTKUNDE`
- project: `TESTPROJEKT`
- quote: `TESTANGEBOT`
- invoice number/description: `TESTRECHNUNG`
- every free-text business field and fixture: `NICHT BUCHEN`
- every email address: an authorized controlled address; automated fixtures use only `.invalid`

Never send a real invoice to a real customer during this runbook.

## Automated synthetic rehearsal

`make full-check` creates disposable source and restore stacks, exercises the
billing preview/snapshot rules, API/browser/PDF/SMTP-lock/export/restic/restore/
cleanup behavior, upgrades a populated copy of the prior PostgreSQL schema, and
removes its resources. Its configured SMTP fixture must receive zero messages.
The API-35 CI job creates a separate disposable stack seeded by
`tests/android-smoke/seed.py`. Neither run proves manual mail delivery, real
offsite storage, a production proxy, or a production deployment.

## Controlled 22-step operator flow

1. **Check installation.** Record the intended Git SHA. Run readiness, then `scripts/collect-deployment-state.sh` with the authorized env file and output directory. Stop unless app revision, image revision, database schema, readiness, volumes, and intended SHA agree. Record proxy/TLS only through an explicitly authorized public URL.
2. **Sign in as the administrator.** Confirm this is the sole administrator and that no customer is watching the session. Do not create another account or role.
3. **Review company data and policy.** Use `docs/BILLING_POLICY.md` and `docs/operations/INVOICE_OPERATOR_CHECKLIST.md`. Confirm operator identity, address, bank data, number prefixes, footer, payment term, 50/75/30 rates, 60-minute work minima, 15-minute remote increment, 30-minute travel minimum, unset travel increment, and the explicit 0-percent/§-19 decision. For rehearsal, use `TESTBETRIEB — NICHT BUCHEN`.
4. **Create the test customer.** Name it exactly `TESTKUNDE`; use only invented address data and an approved controlled `.invalid`/test recipient. Select private/business/custom tariff, verify the displayed standard rate and mode, then explicitly confirm the billing profile. Include `NICHT BUCHEN` in notes/contact fields.
5. **Create the project.** Name it exactly `TESTPROJEKT`, link it to `TESTKUNDE`, explicitly verify tariff override, own rate, remote/onsite mode and individual-project flag, then confirm the profile. Mark its description `NICHT BUCHEN`.
6. **Book time.** Add a remote follow-up and an onsite/travel synthetic entry, including `NICHT BUCHEN`. Verify actual minutes, billable minutes, work rate, work minimum/increment, separate travel minutes/rate/minimum, reason/policy ID, and unbilled status.
7. **Start and stop the timer.** Select `TESTKUNDE`/`TESTPROJEKT`, start with a synthetic description, observe the running state, stop deliberately, and verify that only one running timer existed.
8. **Create the free quote.** Create `TESTANGEBOT — NICHT BUCHEN`. Enter every quantity, price, and tax rate explicitly. Confirm that no time entry or billable service was created. If using the deterministic assistant, retain its catalog version and calculation trace. Record a technical consultation only as a separate deliberate service entry.
9. **Review the quote PDF.** Open the generated PDF and manually verify operator/customer identity, service, dates, quantities, rates, tax decision, totals, footer, and unmistakable synthetic marking. Record deviations; do not merely check that a PDF file exists.
10. **Approve the quote.** Perform the explicit human approval/status action. The deterministic assistant may not transfer an unapproved draft. Approval is not an email action.
11. **Preview, confirm, and convert once to a fixed-price invoice draft.** Select the real service date; review the fixed-price quantities/prices, project snapshot, explicit not-applicable time/minimum/rounding fields, tax status, due date, and totals. Confirm the exact preview, invoke conversion once, retain the returned invoice ID, repeat only as an idempotency check, and confirm both responses identify the same single draft and single invoice number.
12. **Create and review the time invoice.** Select only finished unbilled entries. Review the pre-invoice table line by line: actual/billable work and travel minutes, minimums, increments, rates/types, reasons, dates, project snapshots, work/travel totals, 0-percent tax status, §-19 notice, and grand total. Confirm the exact preview once, then create the invoice. Use the operator checklist for both invoices; confirm unique numbers, payment terms/data and footer. Recalculate after any stale-preview warning.
13. **Open and download the PDF.** Open it in a viewer before delivery, save the authorized evidence copy, and calculate its SHA-256. A missing or changed file is a stop condition.
14. **Deliver manually.** SMTP must remain disabled. Send the inspected PDF through Tim's normal external mail account. The application must not claim an SMTP send. Only after manual delivery, attest PDF review and manual delivery in the application. If delivery did not occur or is ambiguous, leave the invoice in `draft`.
15. **Do not auto-mark paid.** Confirm the deliberate manual-delivery action changes only `draft` to `sent`; it must not populate `paid_at` or mark the invoice paid.
16. **Record payment deliberately.** For synthetic/emulator data only, invoke the visible `Als bezahlt markieren` action after the send state is visible. For the real pilot, do this only after independently observing payment.
17. **Record a synthetic expense.** Create an expense marked `NICHT BUCHEN` and attach a generated synthetic PNG/JPEG/PDF receipt. Never copy a production receipt into a disposable test stack or Git.
18. **Review reports and CSV.** Open summary reports and all CSV exports. Verify expected customer/project/status/amount rows and that no unexpected production row entered the synthetic run.
19. **Create the complete export.** Run `scripts/export-business-data.sh` to a protected local directory. Confirm `business.pg.dump`, `documents.tar.gz`, `MANIFEST.txt`, and `SHA256SUMS`; verify `secrets_included=no` and the intended repository commit.
20. **Create the encrypted offsite snapshot.** Follow `docs/BACKUP_RESTORE.md`. Inventory the target read-only first, change no existing retention, upload the complete export with restic/rclone using secret management, run repository integrity checks, and capture the redacted snapshot ID. If no approved target exists, record `external gate — offsite target` and create nothing.
21. **Restore into a new empty installation.** Use a different Compose project and newly created database/document volumes. Verify the target is empty, invoke `scripts/restore-business-data.sh ... --confirm-empty-target`, start it, and collect deployment state. Never restore onto the source volumes.
22. **Compare data and document hashes.** Compare source/target counts for every business and evidence table, including the expected empty `invoice_send_attempts` table. Verify export checksums and compare a sorted SHA-256 inventory of every restored document against the source inventory. Confirm matching repository/schema revisions, preserved billing snapshots, no missing/extra documents, no duplicate invoice number, no SMTP message, and no changed source system. Record deviations, remove only the isolated test installation, and leave the source untouched.

## Completion record

Record date/time UTC, operator role, source/target deployment-state JSON paths,
intended and observed SHAs, billing-preview confirmation, database-count
comparison, document-hash comparison, export path, redacted offsite snapshot
ID, manual-delivery observation, cleanup result, and every deviation. Do not
record credentials, tokens, `.env` values, customer data, or mail headers.
