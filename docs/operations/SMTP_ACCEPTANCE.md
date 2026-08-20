# SMTP pilot lock and future hardening gate

Status on 2026-08-20: **SMTP is disabled and cannot be enabled in the first
internal pilot.** Runtime SMTP variables do not bypass the server-side module
lock. The send endpoint returns `pilot_module_locked`, records no send attempt,
and performs no SMTP call.

## Pilot delivery procedure

1. Create the invoice only after reviewing and confirming the billing preview.
2. Open and inspect every PDF page.
3. Download the unchanged PDF.
4. Send it manually through Tim's normal, independently operated mail account.
5. Only after that manual action, confirm `PDF reviewed` and `manually delivered`
   in the application.
6. Record payment separately after independently observing payment.

The application records a manual delivery state. It does not claim that its
own SMTP subsystem sent an email. Automatic resend is unavailable.

## Required contract before any future activation

SMTP must remain locked until one implementation and review proves all of the
following together:

- a send attempt is durably committed before the SMTP call;
- attempt states are `pending`, `sent`, `failed`, and `send_unknown`;
- `send_unknown` is used whenever external acceptance may have happened but
  local state is uncertain;
- `send_unknown` never retries automatically;
- the same idempotency key returns only the existing state;
- a new send requires a conscious operator action and a new key;
- stored Message-ID evidence is redacted;
- crash injection after SMTP acceptance is tested;
- process termination immediately before and after SMTP acceptance is tested;
- database commit failures after acceptance are tested;
- first-send/resend intent and original `sent_at` remain unambiguous;
- a controlled provider/mailbox acceptance test is separately authorized.

The former `pending/sent/failed` path does not satisfy this contract because a
process can terminate after provider acceptance and before the local commit.
Leaving that code unreachable behind the pilot lock is intentional. Partial
hardening is not an activation path.
