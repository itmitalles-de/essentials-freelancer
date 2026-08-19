# TODO

This is the authoritative continuation source. `docs/NICE_TO_HAVE.md` is only an
idea record; the pilot feature freeze forbids implementation from that file.

## Now

- [ ] Review the Draft PR without merging it. Treat every failed or absent
  required check as a stop condition; record API-35 emulator evidence separately
  from JVM/APK assembly.

## Single next real action after review

- [ ] Authorize one intended internal pilot deployment target and run the
  read-only deployment inspector before entering real data. Stop on revision,
  dirty-state, readiness, volume, schema, backup-age, proxy, or TLS drift.

## External gates

- [ ] **Deployment:** target/credentials and permission to inspect the running
  Compose installation, image identity, volumes, backup age, proxy and TLS were
  not supplied.
- [ ] **SMTP:** provide a dedicated approved test account and an
  operator-controlled non-customer recipient; follow
  `docs/operations/SMTP_ACCEPTANCE.md`. No random configuration is permitted.
- [ ] **Offsite:** provide an approved encrypted Restic/rclone target and
  protected credentials; inventory it read-only, upload a complete export, run
  the repository check, and restore into new isolated volumes per
  `docs/BACKUP_RESTORE.md`. Do not create a cloud resource automatically.
- [ ] **Governance:** the current private-repository plan does not expose branch
  protection/rulesets (GitHub API HTTP 403). Apply the documented manual
  Draft-PR/CODEOWNER/check gate or enable a supporting plan later.
- [ ] **Android release:** production signing and distribution remain outside
  this pilot-preparation task.

## Completed in this workstream

- [x] Align public repository references and document deliberately retained
  compatibility identifiers.
- [x] Freeze the single-admin pilot scope and route all new ideas to
  `docs/NICE_TO_HAVE.md` without code/schema/UI stubs.
- [x] Record the unchanged green technical baseline at starting commit
  `10ce63ca50c9fdd83e06f570dcc2acd41394afb5`.
- [x] Add explicit invoice review/send/idempotency evidence, explicit tax input,
  canonical Decimal rounding, numbering/footer/PDF/cancel/resend/failure tests,
  and safe SMTP-absent behavior.
- [x] Add read-only deployment JSON/Markdown evidence and a public allowlisted
  version/revision/schema/build/readiness surface.
- [x] Complete the synthetic export/local-Restic/isolated-restore path and the
  real SMTP/offsite operator contracts without claiming external proof.
- [x] Add Action/image pinning, dependency verification/audits, secret history
  scan, SBOM generation, CODEOWNERS and settings documentation.
- [x] Add the authenticated Android cache regression and API-35 pilot smoke
  scenario using unmistakably synthetic data.
