# Codex-Ausführungsprompt: Freelancer stabilisieren und zum fokussierten MVP ausbauen

Du arbeitest im privaten Repository `itmitalles-de/freelancer` auf dem aktuellen Default-Branch. Lies zuerst `AGENTS.md`, `README.md`, `docker-compose.yml` und anschließend die tatsächlich betroffenen Backend-, Frontend- und Android-Dateien. Bestehendes Verhalten und vorhandene Daten müssen erhalten bleiben.

## Ziel

Mache Freelancer zu einem verlässlichen, fokussierten Produkt für Solo-Selbstständige und Dienstleister. Es bleibt eine Single-User-Installation. Es wird weder zu einem Multi-Tenant-SaaS noch technisch neu geschrieben.

## Vorgehen

Erstelle zuerst einen kurzen, evidenzbasierten Ist-Bericht direkt aus dem Repository. Prüfe insbesondere:

- welche Funktionen wirklich vollständig implementiert sind;
- ob Backend, Frontend, Docker und Android reproduzierbar bauen;
- welche kritischen Pfade keine Tests besitzen;
- Datenpersistenz, Rechnungserzeugung, SMTP-Fehlerverhalten und Beleg-Uploads;
- Altbezeichnungen `tracker`, aber ändere interne Datenbank-, Volume- oder Package-Namen nicht beiläufig.

Setze danach in kleinen, überprüfbaren Schritten um:

1. Eine minimale CI-Pipeline für Backend, Frontend und Compose.
2. Backend-Tests für Login, Kunden, Zeitbuchungen, Rechnungserstellung/-status, PDF und Ausgaben.
3. Frontend-Buildprüfung und gezielte Tests für die wichtigsten Nutzerflüsse.
4. Backup-/Restore-Dokumentation und einen sicheren Export der Geschäftsdaten.
5. Erst anschließend fehlende MVP-Funktionen: Projekte, Angebote mit Übernahme in Rechnungen und nachvollziehbare Verknüpfung von Zeit, Kunde, Projekt und Rechnung.
6. Android nur anpassen, wenn eine Backend-Änderung die App betrifft oder ein klarer Kernfluss fehlt.

## Abgrenzung

Nicht implementieren:

- Shop, Produktkatalog, Lager, Versand oder Marktplatzanbindungen — das gehört in Shop Suite.
- Nextcloud, Mail, Office oder Teamchat — das gehört in Workspace Suite.
- Multi-Tenancy, Kubernetes oder eine Rust-Neuentwicklung.
- Steuer- oder Rechtsbehauptungen ohne belastbare Grundlage.

## Qualitätskriterien

- Keine Secrets oder realen Kundendaten.
- Keine destruktiven Datenbankänderungen ohne Migration und Rückweg.
- Neue Kernlogik erhält Tests.
- `docker compose config`, Images, Frontend-Build und relevante Tests müssen grün sein.
- Führe einen Smoke-Test des vollständigen Kernflusses Kunde → Zeit → Rechnung → PDF durch.
- Aktualisiere README nur mit Funktionen, die nachweislich funktionieren.

Arbeite bis zu einem kohärenten, grünen Zwischenstand. Berichte abschließend: umgesetzte Änderungen, ausgeführte Prüfungen, verbleibende Risiken und die drei sinnvollsten nächsten Schritte.
