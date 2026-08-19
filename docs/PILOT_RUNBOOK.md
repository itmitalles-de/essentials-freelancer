# First internal pilot runbook

This runbook is the controlled path for one administrator using one installation. It supports a fully synthetic rehearsal and a later manual run with the operator's own authorized data. It does not authorize customer email, production deployment, or creation of cloud resources.

## Stop conditions and evidence language

Stop immediately on a revision mismatch, dirty deployment checkout, failed readiness, unexpected recipient, reused invoice number, missing document, failed export checksum, non-empty restore target, or ambiguous tax/operator data.

Keep evidence explicitly separated as `implemented`, `synthetically tested`, `tested in CI`, `tested on API-35 emulator`, `tested with real SMTP`, `tested with real offsite target`, `productively deployed`, or `unknown`. Synthetic success never advances a real-service category.

The synthetic objects are always unmistakable:

- customer: `TESTKUNDE`
- project: `TESTPROJEKT`
- quote: `TESTANGEBOT`
- invoice number/description: `TESTRECHNUNG`
- every free-text business field and fixture: `NICHT BUCHEN`
- every email address: an authorized controlled address; automated fixtures use only `.invalid`

Never send a real invoice to a real customer during this runbook.

## Automated synthetic rehearsal

`make full-check` creates disposable source and restore stacks, exercises API/browser/PDF/SMTP-fixture/export/restic/restore/cleanup behavior, and removes its resources. The API-35 CI job creates a separate disposable stack seeded by `tests/android-smoke/seed.py`. Neither run proves a real SMTP provider, real offsite storage, a production proxy, or a production deployment.

## Controlled 22-step operator flow

1. **Check installation.** Record the intended Git SHA. Run readiness, then `scripts/collect-deployment-state.sh` with the authorized env file and output directory. Stop unless app revision, image revision, database schema, readiness, volumes, and intended SHA agree. Record proxy/TLS only through an explicitly authorized public URL.
2. **Sign in as the administrator.** Confirm this is the sole administrator and that no customer is watching the session. Do not create another account or role.
3. **Review company data.** Use `docs/operations/INVOICE_OPERATOR_CHECKLIST.md`. Confirm operator identity, address, payment details, number prefixes, footer, payment term, and the concrete tax decision. The application does not infer tax status. For rehearsal, use `TESTBETRIEB — NICHT BUCHEN`.
4. **Create the test customer.** Name it exactly `TESTKUNDE`; use only invented address data and an approved controlled `.invalid`/test recipient. Include `NICHT BUCHEN` in notes/contact fields.
5. **Create the project.** Name it exactly `TESTPROJEKT`, link it to `TESTKUNDE`, explicitly verify its hourly rate, and mark its description `NICHT BUCHEN`.
6. **Book time.** Add a manual synthetic entry for `TESTPROJEKT`, including `NICHT BUCHEN`. Verify date, duration, rate, and unbilled status.
7. **Start and stop the timer.** Select `TESTKUNDE`/`TESTPROJEKT`, start with a synthetic description, observe the running state, stop deliberately, and verify that only one running timer existed.
8. **Create the quote.** Create `TESTANGEBOT — NICHT BUCHEN`. Enter every quantity, price, and tax rate explicitly. If using the deterministic assistant, retain its catalog version and calculation trace.
9. **Review the quote PDF.** Open the generated PDF and manually verify operator/customer identity, service, dates, quantities, rates, tax decision, totals, footer, and unmistakable synthetic marking. Record deviations; do not merely check that a PDF file exists.
10. **Approve the quote.** Perform the explicit human approval/status action. The deterministic assistant may not transfer an unapproved draft. Approval is not an email action.
11. **Convert once to an invoice draft.** Invoke conversion once, retain the returned invoice ID, repeat only as an idempotency check, and confirm both responses identify the same single draft and single invoice number.
12. **Review the invoice.** Use the operator checklist. Confirm visible line quantity × unit price, rounding, tax, total, dates, unique number, payment term, payment data, and footer. The number/description must clearly identify `TESTRECHNUNG` and `NICHT BUCHEN` during rehearsal.
13. **Open and download the PDF.** Open it in a viewer before delivery, save the authorized evidence copy, and calculate its SHA-256. A missing or changed file is a stop condition.
14. **Perform the controlled email test.** Only when `docs/operations/SMTP_ACCEPTANCE.md` is authorized, inspect the confirmation dialog's recipient, invoice number, amount, and external-email warning; attest PDF review; then send once. Replay the same idempotency key and prove no duplicate; use a new key and explicit resend confirmation only for the planned resend case. Without authorized SMTP, leave this step at the external gate and continue with PDF/export rehearsal.
15. **Do not auto-mark paid.** Confirm successful delivery changes only `draft` to `sent`; it must not populate `paid_at` or mark the invoice paid.
16. **Record payment deliberately.** For synthetic/emulator data only, invoke the visible `Als bezahlt markieren` action after the send state is visible. For the real pilot, do this only after independently observing payment.
17. **Record a synthetic expense.** Create an expense marked `NICHT BUCHEN` and attach a generated synthetic PNG/JPEG/PDF receipt. Never copy a production receipt into a disposable test stack or Git.
18. **Review reports and CSV.** Open summary reports and all CSV exports. Verify expected customer/project/status/amount rows and that no unexpected production row entered the synthetic run.
19. **Create the complete export.** Run `scripts/export-business-data.sh` to a protected local directory. Confirm `business.pg.dump`, `documents.tar.gz`, `MANIFEST.txt`, and `SHA256SUMS`; verify `secrets_included=no` and the intended repository commit.
20. **Create the encrypted offsite snapshot.** Follow `docs/BACKUP_RESTORE.md`. Inventory the target read-only first, change no existing retention, upload the complete export with restic/rclone using secret management, run repository integrity checks, and capture the redacted snapshot ID. If no approved target exists, record `external gate — offsite target` and create nothing.
21. **Restore into a new empty installation.** Use a different Compose project and newly created database/document volumes. Verify the target is empty, invoke `scripts/restore-business-data.sh ... --confirm-empty-target`, start it, and collect deployment state. Never restore onto the source volumes.
22. **Compare data and document hashes.** Compare source/target counts for every business and evidence table, including `invoice_send_attempts`. Verify export checksums and compare a sorted SHA-256 inventory of every restored document against the source inventory. Confirm matching repository/schema revisions, no missing/extra documents, no duplicate invoice number, no unintended email, and no changed source system. Record deviations, remove only the isolated test installation, and leave the source untouched.

## Completion record

Record date/time UTC, operator role, source/target deployment-state JSON paths, intended and observed SHAs, database-count comparison, document-hash comparison, export path, redacted offsite snapshot ID, redacted SMTP Message-ID hash, delivery observation, cleanup result, and every deviation. Do not record credentials, tokens, `.env` values, customer data, or full Message-IDs.
