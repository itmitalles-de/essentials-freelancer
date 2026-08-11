import { FormEvent, useEffect, useState } from "react";
import { api, fetchCompanyLogoUrl, uploadCompanyLogo } from "../api";
import { CompanySettings } from "../types";

export function Settings() {
  const [settings, setSettings] = useState<CompanySettings | null>(null);
  const [saved, setSaved] = useState(false);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [logoError, setLogoError] = useState<string | null>(null);

  useEffect(() => {
    api.get<CompanySettings>("/settings").then(setSettings);
  }, []);

  useEffect(() => {
    if (!settings?.has_logo) {
      setLogoUrl(null);
      return;
    }
    let objectUrl: string | null = null;
    fetchCompanyLogoUrl().then((url) => {
      objectUrl = url;
      setLogoUrl(url);
    });
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [settings?.has_logo]);

  if (!settings) return <div>Lädt…</div>;

  const set = (key: keyof CompanySettings) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => setSettings({ ...settings, [key]: e.target.value });

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const { next_invoice_number, has_logo, ...payload } = settings;
    const updated = await api.put<CompanySettings>("/settings", payload);
    setSettings(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const onLogoSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setLogoError(null);
    try {
      const updated = await uploadCompanyLogo<CompanySettings>(file);
      setSettings(updated);
    } catch (err) {
      setLogoError(err instanceof Error ? err.message : "Upload fehlgeschlagen");
    }
  };

  const onLogoRemove = async () => {
    const updated = await api.delete<CompanySettings>("/settings/logo");
    setSettings(updated);
  };

  return (
    <div style={{ maxWidth: 560 }}>
      <h2>Einstellungen — Firmendaten</h2>
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.6rem", marginBottom: "1rem" }}>
        <strong>Logo</strong>
        {logoUrl && (
          <img
            src={logoUrl}
            alt="Firmenlogo"
            style={{ maxWidth: 200, maxHeight: 120, objectFit: "contain", background: "var(--bg-elevated)", borderRadius: 4, padding: 8 }}
          />
        )}
        <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
          <input type="file" accept="image/png,image/jpeg" onChange={onLogoSelected} />
          {settings.has_logo && (
            <button type="button" onClick={onLogoRemove}>
              Logo entfernen
            </button>
          )}
        </div>
        {logoError && <div style={{ color: "var(--danger)" }}>{logoError}</div>}
        <div style={{ color: "var(--fg-muted)", fontSize: "0.85rem" }}>
          PNG oder JPEG, max. 5 MB. Erscheint oben rechts auf jeder Rechnung.
        </div>
      </div>
      <form onSubmit={onSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        <input placeholder="Firmenname" value={settings.company_name} onChange={set("company_name")} />
        <input placeholder="Inhaber" value={settings.owner_name} onChange={set("owner_name")} />
        <input placeholder="Adresse" value={settings.address_line1} onChange={set("address_line1")} />
        <input placeholder="Adresszusatz" value={settings.address_line2} onChange={set("address_line2")} />
        <input placeholder="PLZ Ort" value={settings.zip_city} onChange={set("zip_city")} />
        <input placeholder="E-Mail" value={settings.email} onChange={set("email")} />
        <input placeholder="Telefon" value={settings.phone} onChange={set("phone")} />
        <input placeholder="Steuernummer" value={settings.tax_id} onChange={set("tax_id")} />
        <input placeholder="IBAN" value={settings.iban} onChange={set("iban")} />
        <input placeholder="BIC" value={settings.bic} onChange={set("bic")} />
        <input placeholder="Bank" value={settings.bank_name} onChange={set("bank_name")} />
        <textarea placeholder="Fußnote auf Rechnung (z.B. §19 UStG Hinweis)" value={settings.invoice_footer_note} onChange={set("invoice_footer_note")} />
        <input placeholder="Rechnungsnummern-Präfix" value={settings.invoice_number_prefix} onChange={set("invoice_number_prefix")} />
        <input placeholder="Standard-Stundensatz" value={settings.default_hourly_rate} onChange={set("default_hourly_rate")} />
        <input
          placeholder="Zahlungsziel (Tage)"
          type="number"
          value={settings.default_payment_terms_days}
          onChange={(e) => setSettings({ ...settings, default_payment_terms_days: Number(e.target.value) })}
        />
        <div style={{ color: "var(--fg-muted)", fontSize: "0.85rem" }}>
          Nächste Rechnungsnummer: {settings.invoice_number_prefix}-{new Date().getFullYear()}-{String(settings.next_invoice_number).padStart(4, "0")}
        </div>
        <button type="submit">Speichern</button>
        {saved && <div style={{ color: "var(--success)" }}>Gespeichert.</div>}
      </form>
    </div>
  );
}
