# Verification matrix

Status as of 2026-08-19. `Synthetic` means generated data and disposable local
infrastructure. It is never evidence for a production account, host, provider,
proxy, DNS record, or deployed revision. GitHub CI and API-35 results are
recorded separately after the pilot branch is pushed.

| Function | Implemented | Local synthetic evidence | CI | API 35 | Real external / deployed | Remaining gate or risk |
|---|---|---|---|---|---|---|
| Single-admin login and protected routes | Yes | Backend/frontend auth, unauthorized-route, rate-limit and Compose login checks | Pending pilot PR | Android test assembled | No | Runtime secrets and proxy behavior are deployment-specific. |
| Clients, projects and scoped rates | Yes | Unit/API/browser/restore checks on synthetic PostgreSQL | Pending pilot PR | Instrumentation scenario assembled | No | Authorized pilot data has not been entered. |
| Timer, manual time, concurrency and idempotency | Yes | JVM/backend/API/restore checks, including competing commands | Pending pilot PR | Start/stop/recreate scenario assembled | No | Real workload and latency remain unknown. |
| Quotes, deterministic assistant and one-time conversion | Yes | Versioned Decimal snapshots, human approval, PDF text and concurrent one-time conversion | Pending pilot PR | Not in mobile scope | No | Catalog content, prices and every PDF require human approval. |
| Invoice creation, numbering and Decimal rounding | Yes | Explicit tax input; PostgreSQL-parallel numbering; one-time allocation; 1/5/59-minute rounding; footer snapshot; PDF fields; cancellation | Pending pilot PR | List/status scenario assembled | No | Operator remains responsible for concrete tax and invoice correctness. |
| PDF review and invoice delivery gate | Yes | Browser confirmation shows recipient/number/amount/external warning; PDF-open prerequisite; mocked and fixture sends | Pending pilot PR | PDF-open/download scenario assembled | Real SMTP: **not tested** | Authorized SMTP account and controlled mailbox are absent. |
| SMTP idempotency, resend and failures | Yes | Successful replay does not resend; explicit resend is auditable; auth/reject/timeout/disconnect and failed-resend state covered | Pending pilot PR | Not applicable | Real SMTP: **not tested** | Provider acceptance, routing and delivery are external. |
| Deliberate paid state | Yes | Send never marks paid; transition and terminal-state tests | Pending pilot PR | Explicit paid action scenario assembled | No | Real payment observation is an operator responsibility. |
| Receipts and MIME protection | Yes | Generated PNG/JPEG/PDF uploads, limits/signatures, export/restore and browser rows | Pending pilot PR | Not in mobile scope | No | No real document was read. |
| Reports and CSV | Yes | Backend/filter/API/browser checks for time, quotes, invoices and expenses | Pending pilot PR | Not in mobile scope | No | Reports are operational facts, not accounting/tax advice. |
| Schema and migrations through `0006_pilot_safety` | Yes | SQLite migration regressions plus two fresh PostgreSQL stacks and readiness revision | Pending pilot PR | Indirect | No | A copy of any real database was intentionally not used. |
| Complete export and isolated restore | Yes | Database dump plus entire document volume, checksums, revision, empty-target refusal, counts/hashes/API/browser comparison and cleanup | Pending pilot PR | Not applicable | Real deployment: **not tested** | Host capacity, permissions and real data remain unknown. |
| Encrypted offsite backup | Yes | Temporary encrypted local Restic snapshot, check, retention evaluation and isolated restore | Pending pilot PR | Not applicable | Real offsite: **not tested** | Approved target and protected credentials are absent. |
| Deployment revision/drift evidence | Yes | Secret-safe JSON/Markdown inspector structure and redaction checked against disposable Compose | Pending pilot PR | Not applicable | Deployed revision: **unknown** | Authorized target access, proxy and TLS evidence are absent. |
| Liveness/readiness/build provenance | Yes | `/health`, database-backed `/ready`, public allowlisted `/meta`, OCI revision/build labels and restored revision checks | Pending pilot PR | Synthetic stack uses readiness | No | Public ingress/TLS and actual image identity are deployment-specific. |
| Android compatibility | Yes | 3 JVM tests; app and instrumentation APK assembly; authenticated-client cache regression | Pending pilot PR | Scenario prepared, not yet executed | No | API-35 execution awaits pilot PR CI; release signing remains external. |
| Supply chain and governance | Yes | Action SHA/image digest static checks, npm/pip audits, Gradle wrapper checksum and verification metadata, secret history scan, CycloneDX SBOM (710 components) | Pending pilot PR | Indirect | Branch enforcement unavailable | Private-repository plan returned HTTP 403 for branch protection/rulesets; manual Draft-PR gate is required. |

The reproducible entry point is `make full-check`. It uses random names, ports,
volumes, networks and generated secrets, emits diagnostics on failure, and
removes its disposable resources. The dedicated `android-api35-smoke` workflow
adds a real emulator layer against an unmistakably synthetic Compose stack.
Neither layer authorizes customer email or establishes production readiness.
