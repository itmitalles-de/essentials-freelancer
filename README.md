# Freelancer

Zeiterfassung, Rechnungsstellung und Rechnungsversand für itmitalles — als Docker-App (Backend + Web-Frontend), Android-Client und separates Homer-Dashboard.

> **Hauptprojekt 1 von 3:** Freelancer ist das fokussierte Arbeits- und Abrechnungssystem für Solo-Selbstständige und Dienstleister. Produkt- und Shop-Prozesse gehören in die Shop Suite; Datei-, Mail- und Kollaborationsfunktionen in die Workspace Suite.

**Aktueller Stand (2026-08-12):** Funktionsfähiger Single-User-MVP mit Kunden, Zeiterfassung, Rechnungen/PDF/SMTP, Ausgaben samt Beleg-Upload, Android-Client und Homer-Dashboard. Es fehlt noch eine belastbare automatische Test- und CI-Basis; vor größeren neuen Features hat Stabilisierung Vorrang.

## Funktionen

- Kunden verwalten (mit individuellem Stundensatz)
- Zeit erfassen: Timer (Start/Stopp) oder manueller Eintrag
- Aus offenen Zeiteinträgen eine Rechnung erstellen (PDF, Kleinunternehmerregelung §19 UStG)
- Rechnungen per SMTP versenden, Status verfolgen (Entwurf/versendet/bezahlt)
- Alle Rechnungen jederzeit abrufbar (Web + Android)
- Android-App zum Zeiterfassen und Rechnungen einsehen unterwegs
- Homer-Dashboard als zentrale Startseite für Freelancer-Werkzeuge und Infrastruktur

## Web-Stack

- **Backend**: FastAPI (Python), PostgreSQL, PDF-Erzeugung mit reportlab, SMTP-Versand
- **Frontend**: React + Vite + TypeScript, Dark Mode (System/Hell/Dunkel, persistiert)
- **Dashboard**: Homer, konfiguriert unter `dashboard/assets/config.yml`
- **Deployment**: Docker Compose (`db`, `backend`, `frontend`, `freelancer-dashboard`)

## Setup

```bash
cp .env.example .env
# .env anpassen: JWT_SECRET, ADMIN_PASSWORD, ggf. SMTP-Zugangsdaten
docker network inspect proxy_net >/dev/null 2>&1 || docker network create proxy_net
docker compose up -d --build
```

Danach ist die App unter `http://localhost:8080` erreichbar (Port über `FRONTEND_PORT` in `.env` konfigurierbar). Login mit `ADMIN_USERNAME`/`ADMIN_PASSWORD` aus der `.env`.

Das Homer-Dashboard läuft standardmäßig unter `http://localhost:8081`. Details zu Domain, Caddy und Konfiguration stehen in [`dashboard/README.md`](dashboard/README.md).

Firmendaten (Adresse, IBAN, Steuernummer, Rechnungstext) werden nach dem ersten Login unter **Einstellungen** gepflegt.

### SMTP

Ohne gesetzte `SMTP_HOST`/`SMTP_FROM` funktioniert alles außer dem E-Mail-Versand (PDF-Download geht immer). Rechnungen können jederzeit nachträglich versendet werden, sobald SMTP konfiguriert ist.

## Android-App

Liegt in `android/`, Kotlin + Jetpack Compose (Material 3), MVVM.

- Beim ersten Start: Server-URL (z.B. `https://tracker.itmitalles.de`), Benutzername, Passwort eingeben
- Zeiterfassung mit Timer und manuellen Einträgen
- Kundenliste (nur lesend)
- Rechnungsliste inkl. PDF öffnen und „als bezahlt markieren“
- Farbschema unter Einstellungen (System/Hell/Dunkel)

Build lokal:

```bash
cd android
./gradlew assembleDebug
```

Debug-APK liegt danach unter `android/app/build/outputs/apk/debug/app-debug.apk`.

## Architekturentscheidungen

- Single-User: nur ein Admin-Zugang (aus `.env` geseedet), kein Multi-Tenant
- Kleinunternehmerregelung (§19 UStG): keine Umsatzsteuer, entsprechender Hinweis auf jeder Rechnung
- Rechnungsnummern sind fortlaufend (`<Präfix>-<Jahr>-<laufende Nummer>`), Zähler liegt in den Firmeneinstellungen
- Homer enthält ausschließlich Links und öffentlich auslieferbare Darstellung; keine Zugangsdaten oder Tokens
