# Invoice operator checklist

This is an operational review aid, not legal, tax, or accounting advice. The operator remains responsible for determining the applicable rules with qualified professional help where needed. Application defaults and examples are never a binding statement.

The application does **not** infer tax status. A tax rate must be selected explicitly for time invoices and every quote line. A fresh installation has no tax footer. The known formerly generated § 19 sentence is removed by the pilot migration; custom operator text is preserved.

## Before creating pilot documents

- [ ] Full legal/operator name is present and correct.
- [ ] Complete operator address is present and correct.
- [ ] Customer legal name and address are present and correct.
- [ ] Invoice date is correct.
- [ ] Service date or service period is visible and correct.
- [ ] The invoice number is unique, sequential within the chosen series, and assigned once.
- [ ] Every service description is concrete and understandable.
- [ ] Quantity and unit are correct; visible quantity × unit price reconciles to the line amount using Decimal/cent rounding.
- [ ] Unit price, net subtotal, tax amount, and total are correct.
- [ ] Tax status/rate is an explicit operator decision; the application has not guessed it.
- [ ] A small-business/Kleinunternehmer note is present only if the concrete operator has determined that it applies.
- [ ] Payment due date/terms are correct.
- [ ] IBAN/BIC/bank information is correct for the operator.
- [ ] Footer text is intentionally approved and contains no stale example statement.
- [ ] Any additional operator-required identifier is correct.
- [ ] PDF content matches the stored invoice and the intended recipient.

## Before external email

- [ ] Open the immutable generated PDF in a viewer and inspect every page.
- [ ] Confirm the dialog recipient, invoice number, and amount against the PDF.
- [ ] Confirm that the dialog warns about an external email.
- [ ] Confirm this is the intended first send or an expressly planned resend.
- [ ] Use a new idempotency key for a new attempt; replaying a successful key must not send again.
- [ ] Do not send if SMTP, recipient, document, revision, or tax status is ambiguous.
- [ ] Do not send pilot/test material to a real customer.

## Payment, correction, and cancellation

- [ ] Delivery must never mark an invoice paid.
- [ ] Record payment only after independently observing payment and using the deliberate paid action.
- [ ] Define the operator's correction process before first real use; do not silently edit an already sent PDF.
- [ ] Verify whether the required business process calls for a corrected document, cancellation, or another controlled document outside this application's current capabilities.
- [ ] Use the `cancelled` state deliberately. Both draft and sent invoices may be cancelled; cancelled and paid invoices are terminal in the current state machine.
- [ ] Preserve original PDFs and send-attempt evidence; never reuse an assigned number for a different invoice.

## Pilot deviation record

Record the invoice ID/number, deployed SHA, review time UTC, operator role, checklist exceptions, correction/cancel decision, and document SHA-256 outside Git. Never record customer data, payment data, SMTP headers, or secrets in repository evidence.
