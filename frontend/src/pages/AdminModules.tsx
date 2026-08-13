import { useState } from "react";

import { api, ApiError } from "../api";
import { useModules } from "../contexts/ModulesContext";
import { ModuleStatus } from "../types";

const GROUPS = [
  "Arbeit",
  "Verkauf und Angebote",
  "Abrechnung",
  "Ausgaben",
  "Kommunikation",
  "Export und Integrationen",
  "Kundenspezifisch",
];

const STATE_LABELS: Record<ModuleStatus["state"], string> = {
  not_installed: "Nicht installiert",
  needs_configuration: "Konfiguration erforderlich",
  disabled: "Deaktiviert",
  enabled: "Aktiviert",
  degraded: "Beeinträchtigt",
};

export function AdminModules() {
  const { modules, loading, refresh } = useModules();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const changeState = async (module: ModuleStatus, action: "enable" | "disable") => {
    setBusy(module.manifest.id);
    setError(null);
    try {
      await api.post(`/admin/modules/${module.manifest.id}/${action}`);
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Modulzustand konnte nicht geändert werden.");
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <p>Modulkatalog wird geladen …</p>;

  return (
    <section className="stack" aria-labelledby="modules-title">
      <div>
        <h2 id="modules-title">Admin-Center</h2>
        <p className="muted">
          Module werden serverseitig durchgesetzt. Deaktivierung entfernt keine Geschäftsdaten.
        </p>
      </div>
      {error && <div className="alert error" role="alert">{error}</div>}
      {GROUPS.map((group) => {
        const groupModules = modules.filter((item) => item.manifest.group === group);
        return (
          <section key={group} className="stack" aria-labelledby={`module-group-${group}`}>
            <h3 id={`module-group-${group}`}>{group}</h3>
            {groupModules.length === 0 ? (
              <p className="muted">Keine Module in dieser Gruppe.</p>
            ) : (
              <div className="module-grid">
                {groupModules.map((module) => (
                  <article className="card module-card" key={module.manifest.id}>
                    <div className="module-card-heading">
                      <div>
                        <h4>{module.manifest.display_name}</h4>
                        <code>{module.manifest.id}</code>
                      </div>
                      <span className={`badge module-${module.state}`}>
                        {STATE_LABELS[module.state]}
                      </span>
                    </div>
                    <p>{module.manifest.description}</p>
                    <p className="muted">{module.health.message}</p>
                    {[...module.configuration, ...module.secrets]
                      .filter((item) => !item.configured)
                      .map((item) => (
                        <div className="configuration-gap" key={item.key}>
                          Fehlt: <code>{item.key}</code>
                        </div>
                      ))}
                    <details>
                      <summary>Modulvertrag</summary>
                      <dl className="module-contract">
                        <dt>Typ</dt><dd>{module.manifest.module_type}</dd>
                        <dt>Manifest</dt><dd>v{module.manifest.schema_version}</dd>
                        <dt>Abhängigkeiten</dt><dd>{module.manifest.dependencies.join(", ") || "Keine"}</dd>
                        <dt>API-Grenzen</dt><dd>{module.manifest.api_boundaries.join(", ") || "Keine"}</dd>
                        <dt>Navigation</dt><dd>{module.manifest.navigation_boundaries.join(", ") || "Keine"}</dd>
                        <dt>Jobs</dt><dd>{module.manifest.job_boundaries.join(", ") || "Keine"}</dd>
                        <dt>Datenbesitz</dt><dd>{module.manifest.data_ownership.join(", ") || "Kein eigener Datenbestand"}</dd>
                        <dt>Deaktivierung</dt><dd>{module.manifest.deactivation_behavior}</dd>
                        <dt>Restore</dt><dd>{module.manifest.restore_behavior}</dd>
                      </dl>
                    </details>
                    <div className="module-actions">
                      {module.state === "disabled" || module.state === "not_installed" ? (
                        <button
                          onClick={() => changeState(module, "enable")}
                          disabled={busy === module.manifest.id}
                        >
                          Aktivieren
                        </button>
                      ) : (
                        <button
                          className="secondary"
                          onClick={() => changeState(module, "disable")}
                          disabled={module.manifest.required || busy === module.manifest.id}
                          title={module.manifest.required ? "Erforderliche Kernmodule bleiben aktiv" : undefined}
                        >
                          {module.manifest.required ? "Erforderlich" : "Deaktivieren"}
                        </button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        );
      })}
    </section>
  );
}
