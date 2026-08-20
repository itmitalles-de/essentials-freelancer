# Invoice operator checklist

This is an operational review aid, not legal, tax, or accounting advice. The operator remains responsible for determining the applicable rules with qualified professional help where needed. Application defaults and examples are never a binding statement.

The application does **not** infer tax status. A tax rate must be selected explicitly for time invoices and every quote line. The operator may explicitly enable a confirmed § 19 notice only with 0 percent and approved text. Migration `0007_billing_policy` preserves old PDFs/custom footer text and applies the profile only to new documents.

## Before creating pilot documents

- [ ] Full legal/operator name is present and correct.
- [ ] Complete operator address is present and correct.
- [ ] Customer legal name and address are present and correct.
- [ ] Invoice date is correct.
- [ ] Service date or service period is visible and correct.
- [ ] The invoice number is unique, sequential within the chosen series, and assigned once.
- [ ] Every service description is concrete and understandable.
- [ ] Client tariff, standard rate, service mode, project override/rate and profile-confirmation state are correct.
- [ ] Actual and billable work minutes are both visible and correct.
- [ ] First-order/onsite 60-minute minimum and remote 15-minute increment are applied only in the documented cases.
- [ ] Actual and billable travel minutes are separate; the 30-minute minimum is correct and no increment was invented while the setting is empty.
- [ ] Applied rate type, rate, minimum, increment, reason and policy ID are visible before confirmation.
- [ ] For an accepted fixed-price quote, choose the real service date and confirm the dedicated conversion preview; time/minimum/rounding fields must say not applicable, not invent zero-duration work.
- [ ] Quantity and unit are correct; billable minutes × hourly rate reconciles to the line amount using Decimal/cent rounding.
- [ ] Unit price, net subtotal, tax amount, and total are correct.
- [ ] Tax status/rate is an explicit operator decision; the application has not guessed it.
- [ ] A small-business/Kleinunternehmer note is present only if the concrete operator has determined that it applies.
- [ ] Payment due date/terms are correct.
- [ ] IBAN/BIC/bank information is correct for the operator.
- [ ] Footer text is intentionally approved and contains no stale example statement.
- [ ] Any additional operator-required identifier is correct.
- [ ] PDF content matches the stored invoice and the intended recipient.

## Before and after manual external delivery

- [ ] Open the immutable generated PDF in a viewer and inspect every page.
- [ ] Download the same reviewed PDF and verify invoice number/amount against the intended manual mail.
- [ ] Send through Tim's normal external mail account; the application SMTP module remains disabled.
- [ ] Confirm manual delivery in the application only after the external action completed.
- [ ] Do not confirm if recipient, document, revision, delivery, or tax status is ambiguous.
- [ ] Do not send pilot/test material to a real customer.

## Payment, correction, and cancellation

- [ ] Delivery must never mark an invoice paid.
- [ ] Record payment only after independently observing payment and using the deliberate paid action.
- [ ] Define the operator's correction process before first real use; do not silently edit an already sent PDF.
- [ ] Verify whether the required business process calls for a corrected document, cancellation, or another controlled document outside this application's current capabilities.
- [ ] Use the `cancelled` state deliberately. Both draft and sent invoices may be cancelled; cancelled and paid invoices are terminal in the current state machine.
- [ ] Preserve original PDFs and the manual delivery record; never reuse an assigned number for a different invoice.

## Pilot deviation record

Record the invoice ID/number, deployed SHA, review time UTC, operator role, checklist exceptions, correction/cancel decision, manual-delivery observation, and document SHA-256 outside Git. Never record customer data, payment data, mail headers, or secrets in repository evidence.
