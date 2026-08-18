# Compatibility identifiers

## Public identity

- Visible product name: **Essentials+ Freelancer**
- Canonical private repository: `itmitalles-de/essentials-freelancer`

Product copy, repository links, badges, and clone instructions use the public
identity above. The following identifiers are internal compatibility
boundaries and intentionally do not follow the repository rename:

| Area | Retained identifier |
|---|---|
| PostgreSQL database | `tracker` |
| PostgreSQL user | `tracker` |
| Docker database volume | `tracker_db_data` |
| Docker document volume | `tracker_invoices` |
| Android application/package ID | `de.itmitalles.tracker` |
| Browser storage | Existing `tracker`-derived keys |
| Database history | Existing Alembic migration names and revision IDs |

## Why these names stay stable

Database names, users, volumes, package IDs, browser keys, and migration IDs
bind deployed data, installed clients, automation, and upgrade history. A
cosmetic rename could make an installation start with an empty database or
document volume, split an Android upgrade into a second application, invalidate
stored browser state, or break migration lineage. None of those risks produces
pilot value.

No database, user, volume, Android package, browser-storage, or migration rename
is part of the first internal pilot. Backup and restore procedures must continue
to treat `tracker_db_data` and `tracker_invoices` as one recovery unit.

## Possible later major migration

A separately approved major migration could rename the database/user, Compose
volumes, Android application ID, and browser keys. It would require an explicit
data-copy and rollback plan, old-to-new document verification, Android upgrade
strategy, migration-lineage compatibility, isolated restore rehearsal, and
operator sign-off. Existing migration revision IDs should normally remain
immutable even then; replacement lineage would need a deliberate bridge rather
than history rewriting.
