import { FormEvent, useEffect, useState } from "react";
import { api, fetchCompanyLogoUrl, uploadCompanyLogo } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { CompanySettings } from "../types";

export function Settings() {
  const { t } = useLanguage();
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

  if (!settings) return <div>{t("settings.loading")}</div>;

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
      setLogoError(err instanceof Error ? err.message : t("settings.errUpload"));
    }
  };

  const onLogoRemove = async () => {
    const updated = await api.delete<CompanySettings>("/settings/logo");
    setSettings(updated);
  };

  return (
    <div style={{ maxWidth: 560 }}>
      <h2>{t("settings.title")}</h2>
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.6rem", marginBottom: "1rem" }}>
        <strong>{t("settings.logo")}</strong>
        {logoUrl && (
          <img
            src={logoUrl}
            alt={t("settings.logoAlt")}
            style={{ maxWidth: 200, maxHeight: 120, objectFit: "contain", background: "var(--bg-elevated)", borderRadius: 4, padding: 8 }}
          />
        )}
        <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
          <input type="file" accept="image/png,image/jpeg" onChange={onLogoSelected} />
          {settings.has_logo && (
            <button type="button" onClick={onLogoRemove}>
              {t("settings.logoRemove")}
            </button>
          )}
        </div>
        {logoError && <div style={{ color: "var(--danger)" }}>{logoError}</div>}
        <div style={{ color: "var(--fg-muted)", fontSize: "0.85rem" }}>
          {t("settings.logoHint")}
        </div>
      </div>
      <form onSubmit={onSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        <input placeholder={t("settings.companyName")} value={settings.company_name} onChange={set("company_name")} />
        <input placeholder={t("settings.ownerName")} value={settings.owner_name} onChange={set("owner_name")} />
        <input placeholder={t("settings.address")} value={settings.address_line1} onChange={set("address_line1")} />
        <input placeholder={t("settings.addressLine2")} value={settings.address_line2} onChange={set("address_line2")} />
        <input placeholder={t("settings.zipCity")} value={settings.zip_city} onChange={set("zip_city")} />
        <input placeholder={t("settings.email")} value={settings.email} onChange={set("email")} />
        <input placeholder={t("settings.phone")} value={settings.phone} onChange={set("phone")} />
        <input placeholder={t("settings.taxId")} value={settings.tax_id} onChange={set("tax_id")} />
        <input placeholder={t("settings.iban")} value={settings.iban} onChange={set("iban")} />
        <input placeholder={t("settings.bic")} value={settings.bic} onChange={set("bic")} />
        <input placeholder={t("settings.bankName")} value={settings.bank_name} onChange={set("bank_name")} />
        <textarea placeholder={t("settings.footerNote")} value={settings.invoice_footer_note} onChange={set("invoice_footer_note")} />
        <input placeholder={t("settings.invoiceNumberPrefix")} value={settings.invoice_number_prefix} onChange={set("invoice_number_prefix")} />
        <input placeholder={t("settings.defaultHourlyRate")} value={settings.default_hourly_rate} onChange={set("default_hourly_rate")} />
        <input
          placeholder={t("settings.paymentTerms")}
          type="number"
          value={settings.default_payment_terms_days}
          onChange={(e) => setSettings({ ...settings, default_payment_terms_days: Number(e.target.value) })}
        />
        <div style={{ color: "var(--fg-muted)", fontSize: "0.85rem" }}>
          {t("settings.nextInvoiceNumber")} {settings.invoice_number_prefix}-{new Date().getFullYear()}-{String(settings.next_invoice_number).padStart(4, "0")}
        </div>
        <button type="submit">{t("settings.save")}</button>
        {saved && <div style={{ color: "var(--success)" }}>{t("settings.saved")}</div>}
      </form>
    </div>
  );
}
