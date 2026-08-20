# TODO

This is the authoritative continuation source. The pilot feature freeze in
`docs/PILOT_SCOPE.md` forbids additional product modules.

## Next authorized operational action

- [ ] Record one exact authorized internal Docker host, access method, Compose
  directory, proxy boundary, and approved encrypted backup target. Then follow
  `docs/INTERNAL_DEPLOYMENT_PLAN.md` from the squash-merged `master` commit.
- [ ] Before real data, configure and consciously confirm Tim's operator,
  billing and § 19 profile; create only marked test objects; run the complete
  shadow flow; store image IDs/digests and deployed commit outside Git.
- [ ] Create an encrypted complete backup and prove restore into a separately
  named empty installation. Stop on any revision, schema, count, document hash,
  invoice number, billing preview, PDF, SMTP-lock, proxy, or TLS mismatch.

No deployment may start from a placeholder or guessed address. SMTP stays
disabled and is not an external gate for the first pilot.

## External gates

- [ ] **Deployment:** exact target authorization and access are absent.
- [ ] **Persistent encrypted backup:** approved target and protected credentials
  are absent; the local Restic rehearsal is not offsite evidence.
- [ ] **Operator profile:** real name/address/bank/payment-term/prefix and the
  exact § 19 notice must be approved at deployment time and kept out of Git.
- [ ] **Android release:** production signing/distribution remains outside the
  debug internal-pilot smoke.
- [ ] **Governance:** the private-repository plan previously returned HTTP 403
  for branch protection/rulesets; PR #3 checks/manual review remain the
  compensating release record.

## Completed in the billing-policy workstream

- [x] Implement configurable private/business/custom and travel rates without
  retaining the incorrect prior rate assumption.
- [x] Persist explicit time decisions and immutable invoice/tax/footer/PDF
  snapshots; require visible exact-token operator confirmation.
- [x] Keep quote preparation free and require a separate confirmed fixed-price
  conversion preview without invented time facts.
- [x] Add additive `0007` migration values and prove a populated PostgreSQL
  `0006` copy upgrades without historical invoice/document drift.
- [x] Lock SMTP disabled with zero fixture messages and manual PDF delivery.
- [x] Cover billing examples, Decimal limits, parallel numbering, tax profile,
  PDF evidence, migration, browser accessibility, Android, backup and isolated
  restore in `make full-check`.
- [x] Complete an independent review of prices, minima, rounding, tax, old data,
  totals, SMTP crash risk, backup and restore with no open P0/P1.
