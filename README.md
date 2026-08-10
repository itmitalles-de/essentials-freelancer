# tracker

Zeiterfassung, Rechnungsstellung und Rechnungsversand für itmitalles — als Docker-App (Backend + Web-Frontend) plus Android-Client.

## Funktionen

- Kunden verwalten (mit individuellem Stundensatz)
- Zeit erfassen: Timer (Start/Stopp) oder manueller Eintrag
- Aus offenen Zeiteinträgen eine Rechnung erstellen (PDF, Kleinunternehmerregelung §19 UStG)
- Rechnungen per SMTP versenden, Status verfolgen (Entwurf/versendet/bezahlt)
- Alle Rechnungen jederzeit abrufbar (Web + Android)
- Android-App zum Zeiterfassen und Rechnungen einsehen unterwegs

## Web-Stack

- **Backend**: FastAPI (Python), PostgreSQL, PDF-Erzeugung mit reportlab, SMTP-Versand
- **Frontend**: React + Vite + TypeScript, Dark Mode (System/Hell/Dunkel, persistiert)
- **Deployment**: Docker Compose (`db`, `backend`, `frontend`)

## Setup

```bash
cp .env.example .env
# .env anpassen: JWT_SECRET, ADMIN_PASSWORD, ggf. SMTP-Zugangsdaten
docker compose up -d --build
```

Danach ist die App unter `http://localhost:8080` erreichbar (Port über `FRONTEND_PORT` in `.env` konfigurierbar). Login mit `ADMIN_USERNAME`/`ADMIN_PASSWORD` aus der `.env`.

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
