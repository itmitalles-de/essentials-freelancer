# First internal pilot scope

## Purpose and feature freeze

The first internal pilot validates one real, operator-controlled business flow
on one private Essentials+ Freelancer installation. It is not a feature-growth
milestone. Until the exit criteria below are met, new product ideas are recorded
only in [`NICE_TO_HAVE.md`](NICE_TO_HAVE.md); they do not receive stubs, empty
APIs, database tables, hidden routes, feature flags, or disabled UI.

## Pilot scope

- exactly one administrator;
- the administrator's own clients and projects;
- the administrator's own manual time entries and timer use;
- the administrator's own quotes, including manually reviewed PDFs;
- the administrator's own draft invoices and manually reviewed PDFs;
- the administrator's own expenses;
- operational reports and CSV exports;
- complete database-and-document backup and restore.

The deterministic quote assistant remains versioned, reproducible, transparent,
and subject to explicit human approval. It does not approve, convert, send, or
make a business decision autonomously.

## Hard non-goals

The pilot does not add:

- multi-tenancy, teams, employee roles, or a public SaaS service;
- shop, inventory, orders, or additional Essentials+ modules;
- DATEV automation, tax advice, or accounting/tax-status inference;
- AI quote generation or expanded OCR;
- payment providers or a customer portal;
- Kubernetes or a platform redesign;
- cosmetic redesign without a concrete pilot-safety need.

## Exit criteria

The pilot is complete only when evidence exists for all of the following:

- one complete own-business workflow has been performed;
- a quote PDF has been manually checked before approval;
- a draft invoice and its PDF have been manually checked before any send;
- one controlled SMTP acceptance test reached only an approved test recipient;
- a complete export containing database and documents has been created;
- that export has been stored in an approved encrypted offsite target;
- the offsite snapshot has been restored into a new, empty installation;
- database counts, document hashes, and repository/schema revisions match;
- deviations and operator decisions have been documented;
- no document was lost;
- no invoice number was allocated twice;
- no unintended email was sent.

Synthetic local acceptance is necessary regression evidence but cannot satisfy
the real SMTP, real offsite, deployed-revision, or real-operator exit criteria.
