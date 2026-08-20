# Billing policy for the first internal pilot

This document describes the configurable billing contract implemented by
`0007_billing_policy`. It is an operational specification, not tax or legal
advice. The operator must review every preview and generated PDF.

## Deployment profile

Tim's deployment uses these explicit settings:

| Setting | Value |
|---|---:|
| Private client work | 50.00 EUR/hour |
| Business and individual-project work | 75.00 EUR/hour |
| Travel | 30.00 EUR/hour |
| First-order work minimum | 60 minutes |
| Onsite or travel-associated work minimum | 60 minutes |
| Remote follow-up increment | 15 minutes |
| Travel minimum | 30 minutes |
| Travel increment | unset |

These values are stored in company settings and can be changed deliberately;
they are not constants in the calculation code. Client and project profiles
store the selected tariff and standard/override rate. A custom tariff requires
an explicit rate.

Rate precedence for a new time entry is: explicit time-entry override,
project-specific rate, project tariff override, individual-project business
tariff, client standard rate, then the configured deployment tariff. The
resolved rate and its source are stored on the time entry.

## Work-time rules

- A first order bills at least 60 work minutes.
- Onsite work, or any entry with travel, bills at least 60 work minutes.
- When both conditions apply, the larger configured minimum applies once; the
  minimums are not added.
- A remote follow-up without travel has no 60-minute minimum. Positive actual
  time is rounded up to the next configured 15-minute increment.
- Zero actual minutes remain zero unless a first-order/onsite minimum was
  explicitly selected.

Examples at the deployment rates:

| Case | Actual | Billable | Net work/travel amount |
|---|---:|---:|---:|
| Private remote follow-up | 1 min | 15 min | 12.50 EUR |
| Private remote follow-up | 16 min | 30 min | 25.00 EUR |
| Business remote follow-up | 31 min | 45 min | 56.25 EUR |
| Private first order | 10 min | 60 min | 50.00 EUR |
| Business onsite work | 20 min | 60 min | 75.00 EUR |
| Travel | 10 min | 30 min | 15.00 EUR |
| Travel | 31 min | 31 min | 15.50 EUR |

Travel is a separate invoice line. The 30-minute minimum is confirmed. No
increment above that minimum is assumed. If `travel_increment_minutes` remains
unset, 31 actual travel minutes bill as 31 minutes. A future increment affects
only newly calculated decisions and must be configured explicitly.

## Visible decision and immutable evidence

Each time entry stores actual and billable work minutes, rate/type/source,
minimum, increment, service mode, first-order flag, policy reason and versioned
policy ID. Travel has separate actual/billable minutes, rate, minimum,
optional increment, and reason.

Before creating a time invoice, the API and web UI show every work/travel line,
actual and billable minutes, rate/type, minimum, increment, reason, service
mode, date, project, net/tax/gross values, work total, travel total, tax status,
and total. Invoice creation requires the exact preview token plus a separate
operator confirmation. Any changed billing input invalidates the token.

Converting an accepted fixed-price quote has a separate preview and confirmation
gate. The operator must select the service date and review each immutable quote
line, project snapshot, unit price, tax status, due date, and totals. Work/travel
minutes, minima, increments, and service mode are displayed as not applicable
and stored as null rather than invented as zero. Quote conversion never creates
a time entry.

The invoice line then snapshots description, date, project name, actual and
billable duration, hourly rate, tariff type, minimum, increment, mode,
first-order flag, reason, policy ID, and money values. PDFs are generated once
from that snapshot and stored. Later rate, project-name, tax-profile, or footer
changes do not regenerate or alter an existing invoice/PDF.

## Quotes and tax profile

Creating a quote or estimate never creates a time entry. Quote preparation is
free. A separate technical consultation is billable only when the operator
records it as a normal service time entry.

The operator profile can explicitly select a default 0 percent rate and enable
an operator-confirmed § 19 UStG notice. Enabling that notice requires 0 percent
and non-empty text. The notice and custom footer are snapshotted on new
invoices; historical PDFs and custom footer text are never rewritten.

## Migration from `0006_pilot_safety`

Migration `0007_billing_policy` is additive. Existing client rates become
`custom`; existing client/project profiles remain unconfirmed. Billed and
unbilled time rows retain their original duration/rate and are marked with
neutral legacy policy IDs without applying a new calculation. Existing invoice
numbers, totals, lines, PDF paths, and document bytes remain unchanged; legacy
invoice snapshot fields are nullable because missing facts are not invented.
The invoice detail view likewise shows missing legacy facts as unknown and never
substitutes a current project name or labels a historical hours quantity as
minutes.

An existing unbilled entry can be invoiced only after the operator confirms the
client and project profiles and then confirms the complete new preview. The
migration also forces `communication.smtp` to `disabled`.
