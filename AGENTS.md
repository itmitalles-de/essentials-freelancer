# AGENTS.md

## Produktgrenze

Dieses Repository ist **Freelancer**, Hauptprojekt 1 von 3. Es richtet sich an Solo-Selbstständige und Dienstleister.

- Hierher gehören Kunden, Projekte, Zeiterfassung, Angebote, Rechnungen, Ausgaben und einfache Exporte.
- Produktkatalog, Lager, Auftragsabwicklung und E-Commerce gehören in **Shop Suite**.
- Dateien, Mail, Office, Talk und Groupware gehören in **Workspace Suite**.
- Kein Multi-Tenant-SaaS und kein Framework-Rewrite ohne ausdrücklichen Auftrag.

## Bestehende Architektur

- Backend: FastAPI, PostgreSQL, ReportLab, SMTP
- Frontend: React, Vite, TypeScript
- Android: Kotlin, Jetpack Compose
- Betrieb: Docker Compose; bestehende Volumes und `proxy_net` erhalten
- Aktuell: eine Installation, ein Admin, Kleinunternehmer-Rechnungsmodus

Interne Altbezeichnungen wie `tracker` dürfen nur in einem eigenen, getesteten Migrationsschritt geändert werden. Keine Volumes, Datenbanknamen oder Android-Package-IDs nebenbei umbenennen.

## Arbeitsweise

1. Vor Änderungen `README.md`, Compose-Datei und die betroffenen Module vollständig lesen.
2. Aktuellen Ist-Zustand und vorhandene uncommitted Änderungen prüfen; fremde Änderungen erhalten.
3. Erst eine kleine vertikale Änderung umsetzen, dann testen und Diff prüfen.
4. Fehler reproduzieren und Ursachen belegen. Keine kosmetischen Workarounds für Daten- oder Zustandsfehler.
5. Keine Secrets, realen Kundendaten oder Zugangsdaten committen.
6. Vor Datenmodelländerungen Migration und Rückwärtsverträglichkeit planen.

## Verifikation

Mindestens passend zur Änderung:

- `docker compose config`
- `docker compose build`
- Frontend: `npm ci && npm run build`
- Backend: vorhandene bzw. neu ergänzte Tests
- Android bei Android-Änderungen: `cd android && ./gradlew assembleDebug`
- Ein echter Smoke-Test des geänderten Nutzerflusses

Fertig bedeutet: Verhalten umgesetzt, relevante Tests grün, Dokumentation aktuell, keine Secrets und keine unbeabsichtigten Änderungen außerhalb des Scopes.
