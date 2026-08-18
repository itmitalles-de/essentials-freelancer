# Pilot acceptance baseline

## Evidence boundary

This baseline records an unchanged run of `make full-check` before pilot
implementation work. It proves repository-local behavior with generated data
and disposable local infrastructure only. It does **not** prove a deployed
revision, production data compatibility, real SMTP delivery, a real offsite
provider, public proxy/DNS/TLS, or Android device behavior.

## Revision and environment

- Baseline commit: `10ce63ca50c9fdd83e06f570dcc2acd41394afb5`
- Branch starting point: `master` / `origin/master`
- Run completed: `2026-08-18T23:08:21Z`
- Host kernel: Linux `7.0.0-29-generic` (`x86_64`)
- Docker: `29.1.3`
- Docker Compose: `2.40.3`
- Bash: `5.3.9`
- Host Python: `3.14.4`; backend test image Python: `3.12`
- Node.js: `24.10.0`; npm: `11.6.1`
- Android build JDK: Temurin `17.0.20+8`
- Gradle: `8.9`; Android platform installed/used: API 35
- Restic: `0.19.0`
- pdftotext: `26.01.0`
- Browser: Google Chrome `151.0.7922.169`

The repository was clean before the run. No assertion, test layer, or command
in `scripts/full-check.sh` was changed or skipped.

## Results

| Layer | Result | Recorded evidence |
|---|---|---|
| Backend | Pass | 36 pytest tests, including migration/schema regression; one upstream ReportLab deprecation warning. |
| Frontend | Pass | 7 Vitest files / 8 tests; TypeScript and Vite production build succeeded. |
| Frontend dependencies | Pass | `npm ci`; `npm audit --audit-level=moderate` reported 0 vulnerabilities. |
| Android | Pass | 1 JVM suite / 2 tests and `assembleDebug`; this is not emulator evidence. |
| Compose/static/security | Pass | Compose render validation, shell syntax, Python fixture compilation, ShellCheck, and tracked-tree secret scan. |
| API/PDF | Pass | Generated client/project/time/quote/invoice/expense flow; quote and invoice PDF text assertions passed. |
| SMTP fixture | Pass | Exactly two explicit successful sends were captured; PDF attachment, recipient, and subject matched. Reject, timeout, and disconnect each returned failure while preserving draft status and empty `sent_at`. |
| Playwright | Pass | 2 scenarios on the source stack and the same 2 after restore (4 executions total). |
| axe | Pass | 16 light/dark analyses across source and restored views; no serious or critical violation. |
| Direct export | Pass | PostgreSQL dump, document archive, checksums, secret-exclusion declaration, and repository revision validated. |
| Restic fixture | Pass | One encrypted local snapshot created; `restic check`, retention evaluation, targeted restore, checksums, and revision validation passed. |
| Empty-target restore | Pass | Separate Compose project and new volumes; readiness, database counts, APIs, document hashes, repository/schema revisions, and browser views matched. |
| Cleanup | Pass | No run-specific `freelancer-fc-*` container, volume, network, or image remained after the exit trap. Pre-existing unrelated test images were intentionally not removed. |

## Interpretation

The technical baseline is green and strong enough to begin controlled pilot
hardening. The local SMTP server and local Restic repository are fixtures. Real
SMTP acceptance, a real encrypted offsite restore, the actual deployed commit,
public TLS/proxy behavior, and API-35 emulator behavior remain separate evidence
categories and must never be inferred from this run.
