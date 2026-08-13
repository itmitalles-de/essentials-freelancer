import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError } from "../api";
import {
  AssistantDraft,
  AssistantPreview,
  AssistantSelection,
  AssistantTemplate,
  CatalogItem,
  CatalogVersion,
  Client,
  Project,
  QuotePackage,
} from "../types";

const today = () => new Date().toISOString().slice(0, 10);

const emptyCatalog: {
  stable_key: string;
  kind: CatalogItem["kind"];
  name: string;
  description: string;
  unit: string;
  net_unit_price: string;
  tax_rate: string;
  valid_from: string;
  valid_until: string;
} = {
  stable_key: "",
  kind: "service",
  name: "",
  description: "",
  unit: "hours",
  net_unit_price: "",
  tax_rate: "19",
  valid_from: today(),
  valid_until: "",
};

function newest<T extends { version: number }>(versions: T[]): T {
  return [...versions].sort((a, b) => b.version - a.version)[0];
}

function versionValidOn(version: { valid_from: string; valid_until: string | null }, date: string) {
  return version.valid_from <= date && (!version.valid_until || date <= version.valid_until);
}

export function QuoteAssistant() {
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [packages, setPackages] = useState<QuotePackage[]>([]);
  const [templates, setTemplates] = useState<AssistantTemplate[]>([]);
  const [drafts, setDrafts] = useState<AssistantDraft[]>([]);
  const [catalogForm, setCatalogForm] = useState(emptyCatalog);
  const [versionItemId, setVersionItemId] = useState<number | null>(null);
  const [packageKey, setPackageKey] = useState("");
  const [packageName, setPackageName] = useState("");
  const [packageVersions, setPackageVersions] = useState<number[]>([]);
  const [templateKey, setTemplateKey] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [pricingDate, setPricingDate] = useState(today());
  const [clientId, setClientId] = useState<number | "">("");
  const [projectId, setProjectId] = useState<number | "">("");
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState("");
  const [timing, setTiming] = useState("");
  const [notes, setNotes] = useState("");
  const [surcharge, setSurcharge] = useState("0");
  const [discount, setDiscount] = useState("0");
  const [selections, setSelections] = useState<AssistantSelection[]>([]);
  const [preview, setPreview] = useState<AssistantPreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const [loadedClients, loadedProjects, loadedCatalog, loadedPackages, loadedTemplates, loadedDrafts] = await Promise.all([
      api.get<Client[]>("/clients"),
      api.get<Project[]>("/projects"),
      api.get<CatalogItem[]>("/quote-assistant/catalog/items"),
      api.get<QuotePackage[]>("/quote-assistant/packages"),
      api.get<AssistantTemplate[]>("/quote-assistant/templates"),
      api.get<AssistantDraft[]>("/quote-assistant/drafts"),
    ]);
    setClients(loadedClients);
    setProjects(loadedProjects);
    setCatalog(loadedCatalog);
    setPackages(loadedPackages);
    setTemplates(loadedTemplates);
    setDrafts(loadedDrafts);
  };

  useEffect(() => {
    load().catch((caught) => setError(caught instanceof ApiError ? caught.message : "Daten konnten nicht geladen werden."));
  }, []);

  const currentCatalog = useMemo(
    () => catalog
      .map((item) => ({ item, version: item.versions.find((version) => versionValidOn(version, pricingDate)) }))
      .filter((entry): entry is { item: CatalogItem; version: CatalogVersion } => Boolean(entry.version)),
    [catalog, pricingDate]
  );
  const currentPackages = useMemo(
    () => packages
      .map((item) => ({ item, version: item.versions.find((version) => versionValidOn(version, pricingDate)) }))
      .filter((entry): entry is { item: QuotePackage; version: QuotePackage["versions"][number] } => Boolean(entry.version)),
    [packages, pricingDate]
  );

  const fail = (caught: unknown, fallback: string) =>
    setError(caught instanceof ApiError ? caught.message : fallback);

  const submitCatalog = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const version = {
      description: catalogForm.description,
      unit: catalogForm.unit,
      net_unit_price: catalogForm.net_unit_price,
      tax_rate: catalogForm.tax_rate,
      valid_from: catalogForm.valid_from,
      valid_until: catalogForm.valid_until || null,
    };
    try {
      if (versionItemId) {
        await api.post(`/quote-assistant/catalog/items/${versionItemId}/versions`, version);
      } else {
        await api.post("/quote-assistant/catalog/items", {
          stable_key: catalogForm.stable_key,
          kind: catalogForm.kind,
          name: catalogForm.name,
          version,
        });
      }
      setVersionItemId(null);
      setCatalogForm({ ...emptyCatalog, valid_from: today() });
      await load();
    } catch (caught) {
      fail(caught, "Katalogposition konnte nicht gespeichert werden.");
    }
  };

  const beginNewVersion = (item: CatalogItem) => {
    const previous = newest(item.versions);
    setVersionItemId(item.id);
    setCatalogForm({
      stable_key: item.stable_key,
      kind: item.kind,
      name: item.name,
      description: previous.description,
      unit: previous.unit,
      net_unit_price: previous.net_unit_price,
      tax_rate: previous.tax_rate,
      valid_from: today(),
      valid_until: "",
    });
  };

  const createPackage = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await api.post("/quote-assistant/packages", {
        stable_key: packageKey,
        name: packageName,
        version: {
          description: packageName,
          valid_from: pricingDate,
          items: packageVersions.map((catalog_version_id) => ({ catalog_version_id, quantity: 1 })),
        },
      });
      setPackageKey("");
      setPackageName("");
      setPackageVersions([]);
      await load();
    } catch (caught) {
      fail(caught, "Leistungspaket konnte nicht gespeichert werden.");
    }
  };

  const selectionKey = (selection: AssistantSelection) =>
    selection.catalog_version_id ? `catalog-${selection.catalog_version_id}` : `package-${selection.package_version_id}`;
  const hasSelection = (candidate: AssistantSelection) =>
    selections.some((selection) => selectionKey(selection) === selectionKey(candidate));
  const toggleSelection = (candidate: AssistantSelection) => {
    setPreview(null);
    setSelections((current) =>
      current.some((selection) => selectionKey(selection) === selectionKey(candidate))
        ? current.filter((selection) => selectionKey(selection) !== selectionKey(candidate))
        : [...current, candidate]
    );
  };
  const quantityFor = (candidate: AssistantSelection) =>
    String(selections.find((selection) => selectionKey(selection) === selectionKey(candidate))?.quantity ?? "1");
  const setQuantity = (candidate: AssistantSelection, quantity: string) => {
    setPreview(null);
    setSelections((current) => current.map((selection) =>
      selectionKey(selection) === selectionKey(candidate) ? { ...selection, quantity } : selection
    ));
  };

  const previewRequest = () => ({
    pricing_date: pricingDate,
    selections,
    surcharge_percent: surcharge,
    discount_percent: discount,
  });

  const calculate = async () => {
    setError(null);
    try {
      setPreview(await api.post<AssistantPreview>("/quote-assistant/preview", previewRequest()));
    } catch (caught) {
      fail(caught, "Vorschau konnte nicht berechnet werden.");
    }
  };

  const createDraft = async () => {
    if (!clientId || !preview) return;
    setError(null);
    try {
      await api.post("/quote-assistant/drafts", {
        ...previewRequest(),
        client_id: clientId,
        project_id: projectId || null,
        title,
        notes,
        guided_answers: { location, timing },
      });
      setPreview(null);
      await load();
    } catch (caught) {
      fail(caught, "Entwurf konnte nicht gespeichert werden.");
    }
  };

  const applyTemplate = (value: string) => {
    if (!value) return;
    const versionId = Number(value);
    const version = templates.flatMap((template) => template.versions).find((item) => item.id === versionId);
    if (!version) return;
    setSelections(version.selections);
    setSurcharge(version.surcharge_percent);
    setDiscount(version.discount_percent);
    setPreview(null);
  };

  const saveTemplate = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await api.post("/quote-assistant/templates", {
        stable_key: templateKey,
        name: templateName,
        version: {
          description: templateName,
          questions: ["Wo findet die Leistung statt?", "Wann soll sie erfolgen?"],
          selections,
          surcharge_percent: surcharge,
          discount_percent: discount,
        },
      });
      setTemplateKey("");
      setTemplateName("");
      await load();
    } catch (caught) {
      fail(caught, "Vorlage konnte nicht gespeichert werden.");
    }
  };

  const transitionDraft = async (draft: AssistantDraft, action: "approve" | "transfer") => {
    setError(null);
    try {
      await api.post(`/quote-assistant/drafts/${draft.id}/${action}`);
      await load();
    } catch (caught) {
      fail(caught, "Entwurf konnte nicht weitergeführt werden.");
    }
  };

  const availableProjects = projects.filter((project) => project.active && project.client_id === clientId);

  return (
    <div className="stack quote-assistant">
      <div>
        <h2>Angebotsassistent</h2>
        <p className="muted">Deterministische Kalkulation ohne KI. Erst die ausdrückliche Freigabe erlaubt PDF und Übernahme.</p>
      </div>
      {error && <div className="alert error" role="alert">{error}</div>}

      <details className="card">
        <summary><strong>Katalog, Pakete und Vorlagen verwalten</strong></summary>
        <div className="assistant-admin-grid">
          <form className="stack" onSubmit={submitCatalog}>
            <h3>{versionItemId ? "Neue Preisversion" : "Katalogposition"}</h3>
            {!versionItemId && <>
              <label>Stabile ID<input required value={catalogForm.stable_key} onChange={(event) => setCatalogForm({ ...catalogForm, stable_key: event.target.value })} placeholder="service.installation" /></label>
              <label>Name<input required value={catalogForm.name} onChange={(event) => setCatalogForm({ ...catalogForm, name: event.target.value })} /></label>
              <label>Typ<select value={catalogForm.kind} onChange={(event) => setCatalogForm({ ...catalogForm, kind: event.target.value as typeof catalogForm.kind })}><option value="service">Leistung</option><option value="material">Material</option><option value="travel">Fahrt</option></select></label>
            </>}
            <label>Beschreibung<input required value={catalogForm.description} onChange={(event) => setCatalogForm({ ...catalogForm, description: event.target.value })} /></label>
            <label>Einheit<input required value={catalogForm.unit} onChange={(event) => setCatalogForm({ ...catalogForm, unit: event.target.value })} /></label>
            <label>Nettopreis<input required type="number" min="0" step="0.01" value={catalogForm.net_unit_price} onChange={(event) => setCatalogForm({ ...catalogForm, net_unit_price: event.target.value })} /></label>
            <label>Steuersatz<input required type="number" min="0" max="100" step="0.01" value={catalogForm.tax_rate} onChange={(event) => setCatalogForm({ ...catalogForm, tax_rate: event.target.value })} /></label>
            <label>Gültig ab<input required type="date" value={catalogForm.valid_from} onChange={(event) => setCatalogForm({ ...catalogForm, valid_from: event.target.value })} /></label>
            <label>Gültig bis<input type="date" value={catalogForm.valid_until} onChange={(event) => setCatalogForm({ ...catalogForm, valid_until: event.target.value })} /></label>
            <button type="submit">{versionItemId ? "Version anlegen" : "Position anlegen"}</button>
            {versionItemId && <button type="button" className="secondary" onClick={() => { setVersionItemId(null); setCatalogForm(emptyCatalog); }}>Abbrechen</button>}
          </form>

          <div className="stack">
            <h3>Versionierter Katalog</h3>
            {catalog.map((item) => <div className="catalog-row" key={item.id}><span><strong>{item.name}</strong><br /><code>{item.stable_key}</code> · v{newest(item.versions).version} · {newest(item.versions).net_unit_price} € netto · {newest(item.versions).tax_rate}%</span><button type="button" className="secondary" onClick={() => beginNewVersion(item)}>Neue Version</button></div>)}
          </div>

          <form className="stack" onSubmit={createPackage}>
            <h3>Leistungspaket</h3>
            <label>Stabile ID<input required value={packageKey} onChange={(event) => setPackageKey(event.target.value)} placeholder="package.standard" /></label>
            <label>Name<input required value={packageName} onChange={(event) => setPackageName(event.target.value)} /></label>
            {currentCatalog.map(({ item, version }) => <label key={version.id}><input aria-label={`Paketposition ${item.name}`} type="checkbox" checked={packageVersions.includes(version.id)} onChange={() => setPackageVersions((current) => current.includes(version.id) ? current.filter((id) => id !== version.id) : [...current, version.id])} /> {item.name}</label>)}
            <button disabled={!packageVersions.length}>Paket anlegen</button>
          </form>
        </div>
      </details>

      <section className="card stack" aria-labelledby="guided-flow-title">
        <h3 id="guided-flow-title">Geführte Kalkulation</h3>
        <div className="assistant-form-grid">
          <label>Vorlage<select aria-label="Vorlage" defaultValue="" onChange={(event) => applyTemplate(event.target.value)}><option value="">Ohne Vorlage</option>{templates.flatMap((template) => template.versions.map((version) => <option key={version.id} value={version.id}>{template.name} · v{version.version}</option>))}</select></label>
          <label>Kunde<select required aria-label="Kunde" value={clientId} onChange={(event) => { setClientId(event.target.value ? Number(event.target.value) : ""); setProjectId(""); }}><option value="">Bitte wählen</option>{clients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Projekt<select aria-label="Projekt" value={projectId} onChange={(event) => setProjectId(event.target.value ? Number(event.target.value) : "")}><option value="">Ohne Projekt</option>{availableProjects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Kalkulationsdatum<input type="date" value={pricingDate} onChange={(event) => { setPricingDate(event.target.value); setPreview(null); }} /></label>
          <label>Titel<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
          <label>Wo findet die Leistung statt?<input value={location} onChange={(event) => setLocation(event.target.value)} /></label>
          <label>Wann soll sie erfolgen?<input value={timing} onChange={(event) => setTiming(event.target.value)} /></label>
          <label>Aufschlag in %<input type="number" min="0" step="0.01" value={surcharge} onChange={(event) => { setSurcharge(event.target.value); setPreview(null); }} /></label>
          <label>Rabatt in %<input type="number" min="0" max="100" step="0.01" value={discount} onChange={(event) => { setDiscount(event.target.value); setPreview(null); }} /></label>
        </div>
        <label>Notizen<textarea value={notes} onChange={(event) => setNotes(event.target.value)} /></label>

        <div className="selection-grid">
          {currentCatalog.map(({ item, version }) => {
            const candidate = { catalog_version_id: version.id, quantity: "1" };
            return <label className="selection-card" key={`catalog-${version.id}`}><span><input aria-label={`Kalkulationsposition ${item.name}`} type="checkbox" checked={hasSelection(candidate)} onChange={() => toggleSelection(candidate)} /> <strong>{item.name}</strong> · {version.net_unit_price} € netto/{version.unit} · {version.tax_rate}%</span>{hasSelection(candidate) && <input aria-label={`Menge ${item.name}`} type="number" min="0.01" step="0.01" value={quantityFor(candidate)} onChange={(event) => setQuantity(candidate, event.target.value)} />}</label>;
          })}
          {currentPackages.map(({ item, version }) => {
            const candidate = { package_version_id: version.id, quantity: "1" };
            return <label className="selection-card" key={`package-${version.id}`}><span><input aria-label={`Kalkulationspaket ${item.name}`} type="checkbox" checked={hasSelection(candidate)} onChange={() => toggleSelection(candidate)} /> <strong>Paket: {item.name}</strong> · v{version.version}</span>{hasSelection(candidate) && <input aria-label={`Menge Paket ${item.name}`} type="number" min="0.01" step="0.01" value={quantityFor(candidate)} onChange={(event) => setQuantity(candidate, event.target.value)} />}</label>;
          })}
        </div>
        <div className="button-row"><button type="button" onClick={calculate} disabled={!selections.length}>Rechenweg anzeigen</button><form onSubmit={saveTemplate} className="inline-form"><input aria-label="Vorlagen-ID" placeholder="template.standard" required value={templateKey} onChange={(event) => setTemplateKey(event.target.value)} /><input aria-label="Vorlagenname" placeholder="Vorlagenname" required value={templateName} onChange={(event) => setTemplateName(event.target.value)} /><button className="secondary" disabled={!selections.length}>Auswahl als Vorlage speichern</button></form></div>

        {preview && <div className="calculation-preview" aria-live="polite"><h4>Vollständiger Rechenweg</h4><table><thead><tr><th>Schritt</th><th>Berechnung</th><th>Betrag</th></tr></thead><tbody>{preview.calculation_steps.map((step) => <tr key={step.key}><td>{step.label}</td><td>{step.expression}</td><td>{Number(step.amount).toFixed(2)} €</td></tr>)}</tbody></table><p className="assistant-total">Gesamt: {Number(preview.total).toFixed(2)} €</p><button type="button" onClick={createDraft} disabled={!clientId || !title}>Als ungeprüften Entwurf speichern</button></div>}
      </section>

      <section className="stack" aria-labelledby="assistant-drafts-title">
        <h3 id="assistant-drafts-title">Entwürfe und Freigaben</h3>
        {drafts.map((draft) => <article className="card draft-row" key={draft.id}><div><strong>{draft.title}</strong> · {Number(draft.total).toFixed(2)} € · <span className={`badge module-${draft.status === "draft" ? "needs_configuration" : "enabled"}`}>{draft.status}</span><br /><span className="muted">Katalog-Snapshot vom {draft.pricing_date}</span></div><div className="button-row">{draft.status === "draft" && <button onClick={() => transitionDraft(draft, "approve")}>Ausdrücklich freigeben</button>}{draft.status === "approved" && <button onClick={() => transitionDraft(draft, "transfer")}>In Angebot übernehmen und PDF erzeugen</button>}{draft.quote_id && <Link className="btn" to="/quotes">Angebot #{draft.quote_id}</Link>}</div></article>)}
      </section>
    </div>
  );
}
