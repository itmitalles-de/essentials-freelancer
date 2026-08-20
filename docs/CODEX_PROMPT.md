# Codex-Folgeauftrag: Essentials+ Freelancer extern verifizieren und releasefähig halten

Arbeite im Repository `itmitalles-de/essentials-freelancer` auf Basis des gemergten
Essentials+-Stands. Lies zuerst `AGENTS.md`, `.agent/STATE.md`,
`.agent/TODO.md`, `README.md`, `docs/VERIFICATION_MATRIX.md` und
`docs/BACKUP_RESTORE.md`. Verwende Code, Migrationen und Tests als Source of
Truth. Lies keine reale `.env`, Backups, Belege, PDFs oder Kundendaten.

## Ziel

Halte den automatisiert verifizierten Kern grün und sammle – nur mit
ausdrücklicher Berechtigung und sicheren Testkonten – die noch fehlende externe
Evidenz für einen konkreten Release. Lokale Simulatoren dürfen niemals als
Produktionsnachweis bezeichnet werden.

## Vorgehen

1. Prüfe Branch/Default-Branch, offene PRs/Issues und aktuelle CI-Ergebnisse.
2. Führe `make full-check` unverändert mit synthetischen Daten aus. Repariere
   reproduzierbare Fehler ursächlich; überspringe keine Stufe und schwäche keine
   Assertion.
3. Vergleiche Ergebnis und Revision mit `docs/VERIFICATION_MATRIX.md`. Ergänze
   Tests für jede geänderte Funktion.
4. Wenn autorisierter Staging-/Produktionszugriff ausdrücklich vorliegt, prüfe
   getrennt und mit dokumentierter Revision:
   - Readiness, Legacy-Volumes sowie Proxy/DNS/TLS;
   - SMTP-Authentifizierung, Annahme und Zustellung an einen kontrollierten
     Testempfänger einschließlich sicherem Fehlerfall;
   - verschlüsselten Remote-Restic/Rclone-Snapshot, Retention und Restore in eine
     isolierte leere Installation.
5. Fehlt dieser Zugriff, verändere keine Produktionskonfiguration. Halte die
   Punkte unter `Blocked` in `.agent/TODO.md` und berichte die exakt benötigte
   Evidenz.
6. Aktualisiere State, Matrix und Betriebsdokumentation nur mit tatsächlich
   ausgeführten Ergebnissen. Öffne Änderungen als Draft PR; merge nicht
   automatisch.

## Unveränderliche Grenzen

- Eine Installation, genau ein Administrator; keine Multi-Tenancy oder
  Teamverwaltung.
- Kein Framework-Rewrite und keine breitflächigen Dependency-Upgrades.
- `tracker`-Datenbank/-Volumes und `de.itmitalles.tracker` bleiben kompatibel.
- Keine Lizenz- oder administrative Repository-/Branch-Umbenennung.
- Keine Steuer-, Buchhaltungs- oder Rechtsbehauptungen.
- `docs/NICE_TO_HAVE.md` ist kein Backlog. Implementiere daraus nur einen Punkt,
  wenn ein neuer Auftrag ihn ausdrücklich priorisiert und Voraussetzungen sowie
  automatisierte Abnahme festlegt.

## Abschlussbericht

Nenne geprüfte Revision, Tests/Ergebnisse, reale externe Belege, weiterhin nur
simulierte Integrationen, Blocker, Commits und Draft-PR. Trenne Fakten klar von
Annahmen und verbleibenden Risiken.
