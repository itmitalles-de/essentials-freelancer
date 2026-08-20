import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError, openQuotePdf } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client, Project, Quote, QuoteInvoicePreview, QuoteStatus } from "../types";

const emptyLine = () => ({ description: "", quantity: "1", unit: "hours", unit_price: "", tax_rate: "" });

export function Quotes() {
  const { t } = useLanguage();
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [clientId, setClientId] = useState<number | "">("");
  const [projectId, setProjectId] = useState<number | "">("");
  const [validDays, setValidDays] = useState(14);
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState([emptyLine()]);
  const [error, setError] = useState<string | null>(null);
  const [conversionQuoteId, setConversionQuoteId] = useState<number | null>(null);
  const [conversionServiceDate, setConversionServiceDate] = useState(new Date().toISOString().slice(0, 10));
  const [conversionPreview, setConversionPreview] = useState<QuoteInvoicePreview | null>(null);
  const [conversionConfirmed, setConversionConfirmed] = useState(false);
  const [converting, setConverting] = useState(false);

  const load = () => api.get<Quote[]>("/quotes").then(setQuotes);
  useEffect(() => {
    load();
    api.get<Client[]>("/clients").then(setClients);
    api.get<Project[]>("/projects").then(setProjects);
  }, []);

  const resetForm = () => {
    setClientId("");
    setProjectId("");
    setValidDays(14);
    setNotes("");
    setLines([emptyLine()]);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!clientId) return;
    setError(null);
    try {
      await api.post("/quotes", {
        client_id: clientId,
        project_id: projectId || null,
        valid_in_days: validDays,
        notes,
        line_items: lines.map((line) => ({
          ...line,
          quantity: Number(line.quantity),
          unit_price: Number(line.unit_price),
          tax_rate: Number(line.tax_rate),
        })),
      });
      resetForm();
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Quote could not be saved");
    }
  };

  const setStatus = async (quote: Quote, status: QuoteStatus) => {
    setError(null);
    try {
      await api.put(`/quotes/${quote.id}/status`, { status });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Status could not be changed");
    }
  };

  const prepareConversion = (quote: Quote) => {
    setConversionQuoteId(quote.id);
    setConversionServiceDate(new Date().toISOString().slice(0, 10));
    setConversionPreview(null);
    setConversionConfirmed(false);
    setError(null);
  };

  const previewConversion = async () => {
    if (conversionQuoteId === null) return;
    setError(null);
    try {
      setConversionPreview(await api.post<QuoteInvoicePreview>(`/quotes/${conversionQuoteId}/invoice-preview`, { service_date: conversionServiceDate }));
      setConversionConfirmed(false);
    } catch (err) {
      setConversionPreview(null);
      setError(err instanceof ApiError ? err.message : t("quotes.previewError"));
    }
  };

  const convert = async () => {
    if (conversionQuoteId === null || conversionPreview === null || !conversionConfirmed || converting) return;
    setError(null);
    setConverting(true);
    try {
      await api.post(`/quotes/${conversionQuoteId}/convert`, {
        service_date: conversionServiceDate,
        billing_confirmation_token: conversionPreview.confirmation_token,
        billing_confirmed: true,
      });
      setConversionQuoteId(null);
      setConversionPreview(null);
      setConversionConfirmed(false);
      load();
    } catch (err) {
      setConversionConfirmed(false);
      setError(err instanceof ApiError ? err.message : t("quotes.convertError"));
    } finally {
      setConverting(false);
    }
  };

  const remove = async (quote: Quote) => {
    if (!confirm(t("quotes.confirmDelete"))) return;
    await api.delete(`/quotes/${quote.id}`);
    load();
  };

  const clientName = (id: number) => clients.find((item) => item.id === id)?.name ?? "?";
  const projectName = (id: number | null) => projects.find((item) => item.id === id)?.name ?? "—";
  const availableProjects = projects.filter((item) => item.active && item.client_id === clientId);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{t("quotes.title")}</h2>
        <button onClick={() => { setShowForm((value) => !value); resetForm(); }}>{showForm ? t("quotes.cancel") : t("quotes.new")}</button>
      </div>
      {error && <div style={{ color: "var(--danger)" }}>{error}</div>}
      <div className="card" role="note">{t("quotes.freeQuoteNotice")}</div>
      {showForm && (
        <form onSubmit={submit} className="card" style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.6rem" }}>
            <select required value={clientId} onChange={(event) => { setClientId(event.target.value ? Number(event.target.value) : ""); setProjectId(""); }}>
              <option value="">{t("quotes.client")}</option>{clients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <select value={projectId} onChange={(event) => setProjectId(event.target.value ? Number(event.target.value) : "")}>
              <option value="">{t("quotes.project")}</option>{availableProjects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <input type="number" min="0" required aria-label={t("quotes.validDays")} value={validDays} onChange={(event) => setValidDays(Number(event.target.value))} />
          </div>
          <textarea placeholder={t("quotes.notes")} value={notes} onChange={(event) => setNotes(event.target.value)} />
          {lines.map((line, index) => (
            <div key={index} style={{ display: "grid", gridTemplateColumns: "2fr 0.7fr 1fr 1fr 0.8fr auto", gap: "0.5rem" }}>
              <input required placeholder={t("quotes.description")} value={line.description} onChange={(event) => setLines(lines.map((item, itemIndex) => itemIndex === index ? { ...item, description: event.target.value } : item))} />
              <input required type="number" min="0.01" step="0.01" placeholder={t("quotes.quantity")} value={line.quantity} onChange={(event) => setLines(lines.map((item, itemIndex) => itemIndex === index ? { ...item, quantity: event.target.value } : item))} />
              <select value={line.unit} onChange={(event) => setLines(lines.map((item, itemIndex) => itemIndex === index ? { ...item, unit: event.target.value } : item))}>
                {(["hours", "days", "items", "flat"] as const).map((unit) => <option key={unit} value={unit}>{t(`quotes.unit.${unit}`)}</option>)}
              </select>
              <input required type="number" min="0" step="0.01" placeholder={t("quotes.unitPrice")} value={line.unit_price} onChange={(event) => setLines(lines.map((item, itemIndex) => itemIndex === index ? { ...item, unit_price: event.target.value } : item))} />
              <input required aria-label={t("quotes.taxRate")} type="number" min="0" max="100" step="0.01" placeholder={t("quotes.taxRate")} value={line.tax_rate} onChange={(event) => setLines(lines.map((item, itemIndex) => itemIndex === index ? { ...item, tax_rate: event.target.value } : item))} />
              <button type="button" className="secondary" disabled={lines.length === 1} onClick={() => setLines(lines.filter((_, itemIndex) => itemIndex !== index))}>{t("quotes.removeLine")}</button>
            </div>
          ))}
          <div style={{ display: "flex", gap: "0.6rem" }}><button type="button" className="secondary" onClick={() => setLines([...lines, emptyLine()])}>{t("quotes.addLine")}</button><button type="submit">{t("quotes.create")}</button></div>
        </form>
      )}
      <table className="card">
        <thead><tr><th>{t("quotes.colNumber")}</th><th>{t("quotes.colClient")}</th><th>{t("quotes.colProject")}</th><th>{t("quotes.colValid")}</th><th>{t("quotes.colAmount")}</th><th>{t("quotes.colStatus")}</th><th></th></tr></thead>
        <tbody>{quotes.map((quote) => (
          <tr key={quote.id}>
            <td>{quote.quote_number}</td><td>{clientName(quote.client_id)}</td><td>{projectName(quote.project_id)}</td><td>{quote.valid_until}</td><td>{quote.total} €</td><td><span className={`badge ${quote.status}`}>{quote.status}</span></td>
            <td style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
              <button className="secondary" onClick={() => openQuotePdf(quote.id, quote.quote_number)}>{t("quotes.pdf")}</button>
              {quote.status === "draft" && <><button onClick={() => setStatus(quote, "sent")}>{t("quotes.markSent")}</button><button className="danger" onClick={() => remove(quote)}>{t("quotes.delete")}</button></>}
              {quote.status === "sent" && <><button onClick={() => setStatus(quote, "accepted")}>{t("quotes.accept")}</button><button className="danger" onClick={() => setStatus(quote, "rejected")}>{t("quotes.reject")}</button></>}
              {quote.status === "accepted" && <button onClick={() => prepareConversion(quote)}>{t("quotes.convert")}</button>}
              {quote.converted_invoice_id && <Link className="btn btn-sm" to={`/invoices/${quote.converted_invoice_id}`}>{t("quotes.invoice")}</Link>}
            </td>
          </tr>
        ))}</tbody>
      </table>
      {conversionQuoteId !== null && (
        <section className="card" aria-labelledby="quote-invoice-preview-title" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <h3 id="quote-invoice-preview-title" style={{ margin: 0 }}>{t("quotes.invoicePreviewTitle")}</h3>
          <label>{t("quotes.serviceDate")} <input type="date" value={conversionServiceDate} onChange={(event) => { setConversionServiceDate(event.target.value); setConversionPreview(null); setConversionConfirmed(false); }} /></label>
          <button onClick={previewConversion}>{t("quotes.showInvoicePreview")}</button>
          {conversionPreview && (
            <>
              <table>
                <thead><tr><th>{t("quotes.description")}</th><th>{t("quotes.serviceDate")}</th><th>{t("invoices.previewProject")}</th><th>{t("invoices.previewActual")}</th><th>{t("invoices.previewBillable")}</th><th>{t("invoices.previewPolicy")}</th><th>{t("quotes.quantity")}</th><th>{t("quotes.unitPrice")}</th><th>{t("invoices.previewTax")}</th><th>{t("invoices.previewAmount")}</th></tr></thead>
                <tbody>{conversionPreview.lines.map((line) => <tr key={line.quote_line_item_id}>
                  <td>{line.description}</td><td>{line.service_date}</td><td>{line.project_name ?? "—"}</td>
                  <td>{t("quotes.notApplicableFixed")}</td><td>{t("quotes.notApplicableFixed")}</td><td>{t("quotes.notApplicableFixed")}<br />{line.billing_reason}</td>
                  <td>{line.quantity} {line.unit}</td><td>{line.unit_price} €</td><td>{line.tax_rate} % / {line.tax_amount} €</td><td>{line.total_amount} €</td>
                </tr>)}</tbody>
              </table>
              <div>{t("invoices.workTotal")}: {conversionPreview.work_total} € · {t("invoices.travelTotal")}: {conversionPreview.travel_total} € · {t("quotes.fixedTotal")}: {conversionPreview.fixed_total} €</div>
              <div>{t("invoiceDetail.subtotal")} {conversionPreview.subtotal} € · {t("invoiceDetail.tax")} {conversionPreview.tax_total} € · <strong>{t("invoiceDetail.total")} {conversionPreview.total} €</strong></div>
              <div>{t("invoices.taxStatus")}: {conversionPreview.tax_status}{conversionPreview.tax_notice ? ` — ${conversionPreview.tax_notice}` : ""} · {t("invoiceDetail.due")} {conversionPreview.due_date}</div>
              <label style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}><input type="checkbox" checked={conversionConfirmed} onChange={(event) => setConversionConfirmed(event.target.checked)} />{t("quotes.confirmInvoiceConversion")}</label>
              <button onClick={convert} disabled={!conversionConfirmed || converting}>{t("quotes.confirmCreateInvoice")}</button>
            </>
          )}
          <button className="secondary" onClick={() => { setConversionQuoteId(null); setConversionPreview(null); setConversionConfirmed(false); }}>{t("quotes.cancelConversion")}</button>
        </section>
      )}
    </div>
  );
}
