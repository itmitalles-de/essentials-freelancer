# TODO

This is the authoritative continuation source. `docs/NICE_TO_HAVE.md` is an idea
record, not an active backlog.

## Now

- [ ] Review the Draft PR checks for
  `agent/essentials-freelancer-autonomous`; address reproducible repository/CI
  failures without weakening or skipping the full acceptance target.

## Blocked

- [ ] Prove the revision actually deployed, service/readiness state, legacy
  volumes, and public proxy/DNS/TLS path. Blocked on authorized production or
  staging access and deployment-specific evidence.
- [ ] Prove real SMTP authentication, provider acceptance and delivery to a safe
  controlled recipient while retaining failed-send state guarantees. Blocked on
  an approved external SMTP test account and recipient.
- [ ] Initialize/inspect the approved remote restic/rclone target, run the real
  scheduled service, verify retention, and restore into isolated infrastructure.
  Blocked on provider selection, protected credentials, and deployment access.
- [ ] Verify Android behavior on supported devices/emulators and release signing
  if a distributable release is required. Blocked on the release environment and
  signing authority; debug/JVM automation is already present.

## Recently completed

- [x] Implement Essentials+ manifests, persisted states, server/navigation/job
  enforcement, grouped Admin Center, auditing, dependency rules and secret
  redaction (`a1464f8`, 2026-08-13).
- [x] Implement the deterministic versioned quote assistant with immutable
  Decimal snapshots, human approval and idempotent transfer (`d93d997`,
  2026-08-13).
- [x] Add reporting/CSV, constraints/indexes/idempotency, structured operational
  behavior, MIME/security/rate-limit hardening and tests (`59245b0`, 2026-08-13).
- [x] Add the disposable API/browser/SMTP/export/restic/empty-target restore
  acceptance target, CI integration, verification matrix, and explicit external
  evidence boundaries on the active branch.
