import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, openInvoicePdf, ApiError } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client, CompanySettings, Invoice, InvoicePreview, TimeEntry } from "../types";

export function Invoices() {
  const { t } = useLanguage();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState<number | "">("");
  const [unbilled, setUnbilled] = useState<TimeEntry[]>([]);
  const [selectedEntries, setSelectedEntries] = useState<Set<number>>(new Set());
  const [taxRate, setTaxRate] = useState("");
  const [defaultTaxRate, setDefaultTaxRate] = useState<string | null>(null);
  const [settingsLoadFailed, setSettingsLoadFailed] = useState(false);
  const [creating, setCreating] = useState(false);
  const [preview, setPreview] = useState<InvoicePreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [billingConfirmed, setBillingConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadInvoices = () => api.get<Invoice[]>("/invoices").then(setInvoices);

  useEffect(() => {
    loadInvoices();
    api.get<Client[]>("/clients").then(setClients);
    api.get<CompanySettings>("/settings")
      .then((settings) => {
        setDefaultTaxRate(settings.default_tax_rate);
        setTaxRate(settings.default_tax_rate);
      })
      .catch(() => setSettingsLoadFailed(true));
  }, []);

  useEffect(() => {
    if (!selectedClientId) {
      setUnbilled([]);
      setPreview(null);
      setBillingConfirmed(false);
      return;
    }
    api
      .get<TimeEntry[]>(`/time-entries?client_id=${selectedClientId}&billed=false`)
      .then((entries) => {
        setUnbilled(entries.filter((e) => !e.running_started_at));
        setSelectedEntries(new Set());
        setPreview(null);
        setBillingConfirmed(false);
      });
  }, [selectedClientId]);

  const toggleEntry = (id: number) => {
    setSelectedEntries((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setPreview(null);
    setBillingConfirmed(false);
  };

  const calculatePreview = async () => {
    if (!selectedClientId || selectedEntries.size === 0 || taxRate === "") return;
    setPreviewLoading(true);
    setError(null);
    try {
      setPreview(await api.post<InvoicePreview>("/invoices/preview", {
        client_id: selectedClientId,
        time_entry_ids: Array.from(selectedEntries),
        tax_rate: taxRate,
      }));
      setBillingConfirmed(false);
    } catch (caught) {
      setPreview(null);
      setBillingConfirmed(false);
      setError(caught instanceof ApiError ? caught.message : t("invoices.previewError"));
    } finally {
      setPreviewLoading(false);
    }
  };

  const createInvoice = async () => {
    if (!selectedClientId || selectedEntries.size === 0 || !preview || !billingConfirmed || creating) return;
    setCreating(true);
    setError(null);
    try {
      const key = globalThis.crypto?.randomUUID?.() ?? `invoice-${Date.now()}`;
      await api.postIdempotent("/invoices", key, {
        client_id: selectedClientId,
        time_entry_ids: Array.from(selectedEntries),
        tax_rate: taxRate,
        billing_confirmation_token: preview.confirmation_token,
        billing_confirmed: true,
      });
      setShowCreate(false);
      setSelectedClientId("");
      setTaxRate(defaultTaxRate ?? "");
      setPreview(null);
      setBillingConfirmed(false);
      loadInvoices();
    } catch (caught) {
      setBillingConfirmed(false);
      setError(caught instanceof ApiError ? caught.message : t("invoices.createError"));
    } finally {
      setCreating(false);
    }
  };

  const clientName = (id: number) => clients.find((c) => c.id === id)?.name ?? "?";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{t("invoices.title")}</h2>
        <button disabled={defaultTaxRate === null} onClick={() => {
          if (!showCreate) {
            if (defaultTaxRate === null) return;
            setTaxRate(defaultTaxRate);
            setPreview(null);
            setBillingConfirmed(false);
          }
          setShowCreate((v) => !v);
        }}>{showCreate ? t("invoices.cancel") : t("invoices.new")}</button>
      </div>

      {defaultTaxRate === null && (
        <div role={settingsLoadFailed ? "alert" : "status"} style={{ color: settingsLoadFailed ? "var(--danger)" : "var(--fg-muted)" }}>
          {t(settingsLoadFailed ? "invoices.settingsError" : "invoices.settingsLoading")}
        </div>
      )}

      {showCreate && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {error && <div role="alert" style={{ color: "var(--danger)" }}>{error}</div>}
          <select value={selectedClientId} onChange={(e) => setSelectedClientId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">{t("invoices.chooseClient")}</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          <label>
            {t("invoices.taxRate")}
            <input
              aria-label={t("invoices.taxRate")}
              type="number"
              min="0"
              max="100"
              step="0.01"
              required
              value={taxRate}
              onChange={(event) => { setTaxRate(event.target.value); setPreview(null); setBillingConfirmed(false); }}
            />
          </label>
          <div style={{ color: "var(--fg-muted)" }}>{t("invoices.taxRateHint")}</div>

          {selectedClientId !== "" && (
            <>
              {unbilled.length === 0 ? (
                <div style={{ color: "var(--fg-muted)" }}>{t("invoices.noOpenEntries")}</div>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th></th>
                      <th>{t("invoices.colDate")}</th>
                      <th>{t("invoices.colDescription")}</th>
                      <th>{t("invoices.colActual")}</th>
                      <th>{t("invoices.colBillable")}</th>
                      <th>{t("invoices.colRate")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {unbilled.map((e) => (
                      <tr key={e.id}>
                        <td>
                          <input type="checkbox" checked={selectedEntries.has(e.id)} onChange={() => toggleEntry(e.id)} />
                        </td>
                        <td>{e.date}</td>
                        <td>{e.description}</td>
                        <td>{e.actual_minutes ?? e.duration_minutes} min</td>
                        <td>{e.billable_minutes ?? "—"} min</td>
                        <td>{e.hourly_rate} €/h ({e.billing_rate_type ?? "—"})</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <button onClick={calculatePreview} disabled={selectedEntries.size === 0 || taxRate === "" || previewLoading}>
                {previewLoading ? t("invoices.previewLoading") : t("invoices.preview")}
              </button>
              {preview && (
                <section className="card" aria-labelledby="invoice-preview-title">
                  <h3 id="invoice-preview-title">{t("invoices.previewTitle")}</h3>
                  <table>
                    <thead><tr><th>{t("invoices.previewKind")}</th><th>{t("invoices.previewDate")}</th><th>{t("invoices.previewProject")}</th><th>{t("invoices.previewActual")}</th><th>{t("invoices.previewBillable")}</th><th>{t("invoices.previewRate")}</th><th>{t("invoices.previewPolicy")}</th><th>{t("invoices.previewMode")}</th><th>{t("invoices.previewNet")}</th><th>{t("invoices.previewTax")}</th><th>{t("invoices.previewAmount")}</th></tr></thead>
                    <tbody>{preview.lines.map((line) => <tr key={`${line.time_entry_id}-${line.line_kind}`}>
                      <td>{line.line_kind === "travel" ? t("invoices.travel") : t("invoices.work")}<br />{line.description}</td>
                      <td>{line.service_date}</td><td>{line.project_name ?? "—"}</td>
                      <td>{line.actual_minutes} min</td><td>{line.billable_minutes} min</td>
                      <td>{line.hourly_rate} €/h ({line.rate_type})</td>
                      <td>{line.minimum_minutes} min / {line.increment_minutes ?? "—"} min<br />{line.billing_reason}<br />{line.billing_policy_id}</td>
                      <td>{t(`billing.${line.service_mode}`)}{line.is_first_order ? ` · ${t("time.firstOrder")}` : ""}</td>
                      <td>{line.net_amount} €</td><td>{line.tax_amount} €</td><td>{line.total_amount} €</td>
                    </tr>)}</tbody>
                  </table>
                  <div>{t("invoices.workTotal")}: {preview.work_total} € · {t("invoices.travelTotal")}: {preview.travel_total} €</div>
                  <div>{t("invoiceDetail.subtotal")} {preview.subtotal} € · {t("invoiceDetail.tax")} {preview.tax_total} € · <strong>{t("invoiceDetail.total")} {preview.total} €</strong></div>
                  <div>{t("invoices.taxStatus")}: {preview.tax_status}{preview.tax_notice ? ` — ${preview.tax_notice}` : ""}</div>
                  <label style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
                    <input type="checkbox" checked={billingConfirmed} onChange={(event) => setBillingConfirmed(event.target.checked)} />
                    {t("invoices.confirmBilling")}
                  </label>
                  <button onClick={createInvoice} disabled={!billingConfirmed || creating}>{t("invoices.create")} ({selectedEntries.size} {t("invoices.entries")})</button>
                </section>
              )}
            </>
          )}
        </div>
      )}

      <table className="card">
        <thead>
          <tr>
            <th>{t("invoices.colNumber")}</th>
            <th>{t("invoices.colClient")}</th>
            <th>{t("invoices.colIssueDate")}</th>
            <th>{t("invoices.colDueDate")}</th>
            <th>{t("invoices.colAmount")}</th>
            <th>{t("invoices.colStatus")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((inv) => (
            <tr key={inv.id}>
              <td><Link to={`/invoices/${inv.id}`} className="btn btn-sm">{inv.invoice_number}</Link></td>
              <td>{clientName(inv.client_id)}</td>
              <td>{inv.issue_date}</td>
              <td>{inv.due_date}</td>
              <td>{inv.total} €</td>
              <td><span className={`badge ${inv.status}`}>{inv.status}</span></td>
              <td>
                <button className="secondary" onClick={() => openInvoicePdf(inv.id, inv.invoice_number)}>{t("invoices.pdf")}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
