import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { CompanySettings } from "../types";

export function Settings() {
  const [settings, setSettings] = useState<CompanySettings | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get<CompanySettings>("/settings").then(setSettings);
  }, []);

  if (!settings) return <div>Lädt…</div>;

  const set = (key: keyof CompanySettings) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => setSettings({ ...settings, [key]: e.target.value });

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const { next_invoice_number, ...payload } = settings;
    const updated = await api.put<CompanySettings>("/settings", payload);
    setSettings(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={{ maxWidth: 560 }}>
      <h2>Einstellungen — Firmendaten</h2>
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
