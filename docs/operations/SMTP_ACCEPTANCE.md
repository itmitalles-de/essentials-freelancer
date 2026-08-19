# Real SMTP acceptance

Status on 2026-08-19: **external gate open**. No explicitly approved SMTP test account and controlled real recipient were made available to this repository task. No random provider configuration was created and no customer message was sent.

Local automated coverage uses an in-repository SMTP fixture only. It proves success, idempotent replay, explicit resend, recipient rejection, authentication failure, timeout, disconnect, attachment integrity, attempt history, and invoice-state preservation. It does not prove provider acceptance or mailbox delivery.

## Authorization contract

Before a real test, the designated pilot operator must approve all of the following:

- a dedicated non-customer SMTP test account;
- one controlled recipient mailbox owned by the operator;
- the provider hostname, port, TLS mode, and allowed sender;
- a maintenance window and permission to perform one success plus controlled negative cases;
- an evidence location outside Git.

Read `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, and the recipient only from the authorized secret manager/runtime environment. Never print, paste into chat, commit, or include them in deployment evidence. A username without a password, or vice versa, is an invalid configuration and must not fall back to unauthenticated sending.

## Acceptance sequence

1. Collect pre-test deployment state and prove the intended revision/schema/readiness.
2. Create only `TESTKUNDE`, `TESTPROJEKT`, and `TESTRECHNUNG — NICHT BUCHEN`; use an invoice number prefix or description that cannot be mistaken for bookkeeping.
3. Open and manually inspect the PDF. Confirm recipient, invoice number, amount, and operator-owned invoice fields in the accessible send confirmation.
4. Send exactly once with a unique idempotency key. Confirm the provider accepted the message, then independently observe actual delivery in the controlled mailbox. Provider acceptance alone is not delivery proof.
5. Store only a redacted evidence form such as `sha256:<first 12 hex>` of the Message-ID, timestamps UTC, provider outcome category, delivery observation, invoice ID/number, and deployment SHA. Never store the full Message-ID or headers in Git.
6. Replay the same key and verify that no second provider message exists.
7. Perform one expressly confirmed resend with a new key. Verify two successful history entries, a stable original `sent_at`, and exactly one additional provider message.
8. Test invalid authentication using a temporary deliberately wrong secret if the provider/account policy permits it. Verify HTTP failure, a `failed` attempt category, and that a draft remains `draft`; a failed resend must leave an already sent invoice `sent` with its original `sent_at`.
9. Test recipient rejection only with a provider-supported safe rejected address or controlled policy rule. Do not probe arbitrary addresses. Verify the same state guarantees.
10. Retain the synthetic fixture tests for timeout and connection abort; do not disrupt a real provider to manufacture these faults.
11. Disable/remove test credentials from the runtime, collect post-test deployment state, and document deviations outside Git.

## Required state matrix

| Case | Expected HTTP/result | Invoice state | Send history |
|---|---|---|---|
| First accepted delivery | success | `sent`, first `sent_at` set | one `sent` attempt |
| Same idempotency key replay | same logical success, no SMTP call | unchanged | unchanged |
| Explicit resend accepted | success | `sent`, original `sent_at` unchanged | additional `sent`, `is_resend=true` |
| Draft authentication/rejection/timeout/disconnect failure | failure | `draft`, `sent_at=null` | `failed` with safe error class |
| Sent-invoice resend failure | failure | `sent`, original `sent_at` unchanged | additional failed resend |
| SMTP absent | module/configuration gate | PDF and draft creation still work | no unintended message |

## Exit evidence

The gate closes only after both provider acceptance and observed controlled-mailbox delivery are documented, all state cases pass, no customer address was used, and no secret or raw message metadata entered Git. Otherwise the truthful status remains `real SMTP: not tested`.
