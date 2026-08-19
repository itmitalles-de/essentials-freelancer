# Current state

## Pilot boundary

Essentials+ Freelancer remains one installation for exactly one administrator.
Its pilot scope is clients, projects, time, quotes, invoice drafts, expenses,
CSV reports, and complete backup/restore. The feature freeze and hard non-goals
are authoritative in `docs/PILOT_SCOPE.md`; new ideas go only to
`docs/NICE_TO_HAVE.md` and receive no stubs or dormant schema/UI.

Visible product/repository naming is `Essentials+ Freelancer` and
`itmitalles-de/essentials-freelancer`. PostgreSQL database/user `tracker`,
volumes `tracker_db_data`/`tracker_invoices`, browser storage keys, Android
package `de.itmitalles.tracker`, and migration names remain deliberate
compatibility identifiers. See `docs/COMPATIBILITY_IDENTIFIERS.md`.

## Workstream

- Starting/default revision: `master` / `origin/master` at
  `10ce63ca50c9fdd83e06f570dcc2acd41394afb5`.
- Active branch: `pilot/freelancer-first-internal-use`.
- No matching active branch or Draft PR existed at start. Draft PR #3 is now
  open for review and remains unmerged.
- Initial unchanged `make full-check` passed; exact tools/results are recorded
  in `docs/PILOT_BASELINE.md`.
- No production data, receipt, PDF, credential, SMTP account, offsite target,
  deployment host, or signing key was supplied or read.

## Implemented pilot controls

- Pilot scope/freeze, compatibility-name boundary, 22-step runbook, invoice
  operator checklist, SMTP acceptance gate, backup/restore contract, GitHub
  settings evidence, and verification matrix.
- Explicit invoice/quote tax input; blank fresh-install tax footer; migration
  `0006_pilot_safety` removes only the exact legacy generated footer while
  preserving custom text.
- Time-invoice visible quantities are rounded first with Decimal/ROUND_HALF_UP;
  line totals derive from that same printed quantity. Invoice number allocation
  is tested concurrently on PostgreSQL.
- Invoice delivery requires a previously opened PDF plus an accessible
  confirmation containing recipient, invoice number, amount, and external-mail
  warning. SMTP remains optional; first send and resend are deliberate and use
  required idempotency keys. Redacted send-attempt evidence records success or
  safe failure without changing a draft/sent invoice incorrectly.
- `/api/meta` exposes only product version, repository revision, schema version,
  build time, and readiness. `/api/ready` is the Compose health gate.
- `scripts/collect-deployment-state.sh` performs a read-only, secret-redacted
  runtime inspection and emits mode-0600 JSON plus Markdown.
- Complete export still treats PostgreSQL and the document volume as one unit.
  Offsite retention is dry-run by default; inventory, encrypted upload, check,
  redacted snapshot evidence, and isolated restore are documented.
- Android login no longer poisons the authenticated Retrofit cache. A debug-only
  API-35 instrumentation flow covers login, timer/list actions, client/invoice
  views, PDF open/download, deliberate paid status, and Activity recreation
  against exact synthetic seed objects.
- External GitHub Actions use reviewed commit SHAs; container bases use image
  digests; Gradle verifies dependencies and wrapper distribution; Python/npm
  audits, a history-aware secret scan, CODEOWNERS, and a CycloneDX pilot SBOM
  are part of repository/CI checks.

## Evidence status

- **Implemented:** all controls above.
- **Synthetically tested locally:** focused backend (48), frontend (9), Android
  JVM (3) and APK assembly checks; complete Compose API/PDF/SMTP-fixture/export/
  local-Restic/isolated-restore/browser/axe/deployment-evidence/cleanup flow
  passed from clean commit
  `9da1efaa7889ff53ef37dcf8a512921335ffc4c9`. The final unchanged
  `make full-check` repeat left no disposable containers, volumes, or networks.
  Exact results are in
  `docs/PILOT_BASELINE.md`.
- **Tested in CI:** yes; Draft PR #3 run `32207844740` passed all six jobs at
  the final code-bearing commit, including the unchanged full check.
- **Tested on API-35 emulator:** yes; the dedicated CI job booted an API-35
  emulator and passed login, protected lists, timer start/stop, PDF
  open/download, deliberate paid transition, Activity recreation, and cleanup
  against the synthetic stack.
- **Tested with real SMTP:** no; external gate.
- **Tested with a real offsite target:** no; external gate.
- **Productively deployed:** no evidence; external gate.
- **Unknown:** actual target revision/images/volumes/backup age/proxy/TLS and
  authorized real-data behavior.

Python runtime requirements are directly pinned and the resolved environment is
audited during each build, but transitive packages are not hash-locked. The
pilot therefore treats a reviewed image ID/digest as the deployable artifact and
does not infer that a later rebuild is byte-identical. Gradle verification is an
integrity control, not a vulnerability-feed result.

## Schema and recovery

Migrations `0001` through `0005` retain the established product/module schema.
`0006_pilot_safety` adds `invoice_send_attempts` and performs the narrow footer
cleanup above. All compatibility IDs and existing business documents remain.
Production rollback is a verified full database/document restore, never a
destructive legacy-baseline downgrade.

## External gates

- authorized deployment target access for inspector, revision, volume, proxy
  and TLS evidence;
- approved SMTP test account and operator-controlled recipient;
- approved encrypted Restic/rclone target and protected credentials, followed
  by an isolated real restore;
- Android release-signing authority (not needed for the debug pilot smoke);
- GitHub branch-protection/ruleset capability: current private-repository plan
  returned HTTP 403, so the Draft PR/manual review gate is compensating control.

## Primary references

- `docs/PILOT_SCOPE.md` and `docs/PILOT_RUNBOOK.md`
- `docs/PILOT_BASELINE.md` and `docs/VERIFICATION_MATRIX.md`
- `docs/operations/INVOICE_OPERATOR_CHECKLIST.md`
- `docs/operations/SMTP_ACCEPTANCE.md`
- `docs/BACKUP_RESTORE.md`
- `docs/GITHUB_REPOSITORY_SETTINGS.md`
- `.agent/TODO.md`
