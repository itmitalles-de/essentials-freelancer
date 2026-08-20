import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, openInvoicePdf, ApiError } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client, Invoice } from "../types";

export function InvoiceDetail() {
  const { t } = useLanguage();
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pdfOpened, setPdfOpened] = useState(false);
  const [showDeliveryConfirm, setShowDeliveryConfirm] = useState(false);
  const [manualDeliveryConfirmed, setManualDeliveryConfirmed] = useState(false);

  const load = () => {
    api.get<Invoice>(`/invoices/${id}`).then((inv) => {
      setInvoice(inv);
      api.get<Client>(`/clients/${inv.client_id}`).then(setClient);
    });
  };

  useEffect(() => {
    load();
  }, [id]);

  if (!invoice) return <div>{t("invoiceDetail.loading")}</div>;

  const openForReview = async () => {
    setError(null);
    try {
      await openInvoicePdf(invoice.id, invoice.invoice_number);
      setPdfOpened(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("invoiceDetail.errPdf"));
    }
  };

  const confirmManualDelivery = async () => {
    if (!pdfOpened || !manualDeliveryConfirmed) return;
    setError(null);
    try {
      const updated = await api.put<Invoice>(`/invoices/${invoice.id}/status`, { status: "sent", pdf_reviewed: true, manual_delivery_confirmed: true });
      setInvoice(updated);
      setShowDeliveryConfirm(false);
      setManualDeliveryConfirmed(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("invoiceDetail.errDelivery"));
    }
  };

  const markPaid = async () => {
    const updated = await api.put<Invoice>(`/invoices/${invoice.id}/status`, { status: "paid" });
    setInvoice(updated);
  };

  const remove = async () => {
    if (!confirm(t("invoiceDetail.confirmDelete"))) return;
    await api.delete(`/invoices/${invoice.id}`);
    navigate("/invoices");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxWidth: 700 }}>
      <h2 style={{ margin: 0 }}>{t("invoiceDetail.title")} {invoice.invoice_number}</h2>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <div><strong>{t("invoiceDetail.client")}</strong> {client?.name}</div>
        <div><strong>{t("invoiceDetail.date")}</strong> {invoice.issue_date} — <strong>{t("invoiceDetail.due")}</strong> {invoice.due_date}</div>
        <div><strong>{t("invoiceDetail.status")}</strong> <span className={`badge ${invoice.status}`}>{invoice.status}</span></div>
        <div><strong>{t("invoiceDetail.subtotal")}</strong> {invoice.subtotal} €</div>
        <div><strong>{t("invoiceDetail.tax")}</strong> {invoice.tax_total} €</div>
        <div><strong>{t("invoices.taxStatus")}</strong> {invoice.tax_status_snapshot ?? "—"}{invoice.tax_notice_snapshot ? ` — ${invoice.tax_notice_snapshot}` : ""}</div>
        <div><strong>{t("invoiceDetail.total")}</strong> {invoice.total} €</div>
      </div>

      <table className="card">
        <thead>
          <tr>
            <th>{t("invoiceDetail.colDescription")}</th>
            <th>{t("invoiceDetail.colServiceDate")}</th>
            <th>{t("invoiceDetail.colActual")}</th>
            <th>{t("invoiceDetail.colBillable")}</th>
            <th>{t("invoiceDetail.colRate")}</th>
            <th>{t("invoiceDetail.colPolicy")}</th>
            <th>{t("invoiceDetail.colMode")}</th>
            <th>{t("invoiceDetail.colTax")}</th>
            <th>{t("invoiceDetail.colNet")}</th>
            <th>{t("invoiceDetail.colTaxAmount")}</th>
            <th>{t("invoiceDetail.colProject")}</th>
            <th>{t("invoiceDetail.colAmount")}</th>
          </tr>
        </thead>
        <tbody>
          {invoice.line_items.map((li) => (
            <tr key={li.id}>
              <td>{li.description}</td>
              <td>{li.snapshot_service_date ?? "—"}</td>
              <td>{li.snapshot_actual_minutes == null ? "—" : `${li.snapshot_actual_minutes} min`}</td>
              <td>{li.snapshot_billable_minutes == null ? "—" : `${li.snapshot_billable_minutes} min`}</td>
              <td>{li.snapshot_hourly_rate == null ? `${li.unit_price} €/${li.unit}` : `${li.snapshot_hourly_rate} €/h`} ({li.snapshot_rate_type ?? "legacy"})</td>
              <td>{li.snapshot_minimum_minutes == null ? "—" : `${li.snapshot_minimum_minutes} min`} / {li.snapshot_increment_minutes == null ? "—" : `${li.snapshot_increment_minutes} min`}<br />{li.snapshot_billing_reason ?? "—"}<br />{li.snapshot_billing_policy_id ?? "—"}</td>
              <td>{li.snapshot_service_mode ?? "—"}{li.snapshot_line_kind === "travel" ? ` · ${t("invoices.travel")}` : ""}</td>
              <td>{li.tax_rate} %</td>
              <td>{li.net_amount} €</td>
              <td>{li.tax_amount} €</td>
              <td>{li.snapshot_project_name ?? "—"}</td>
              <td>{li.amount} €</td>
            </tr>
          ))}
        </tbody>
      </table>

      {error && <div style={{ color: "var(--danger)" }}>{error}</div>}

      <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="secondary" onClick={openForReview}>{t("invoiceDetail.openPdf")}</button>
        {invoice.status === "draft" && <button onClick={() => setShowDeliveryConfirm(true)} disabled={!pdfOpened}>{t("invoiceDetail.confirmManualDelivery")}</button>}
        {invoice.status === "sent" && (
          <button onClick={markPaid}>{t("invoiceDetail.markPaid")}</button>
        )}
        {invoice.status === "draft" && (
          <button className="danger" onClick={remove}>{t("invoiceDetail.delete")}</button>
        )}
      </div>

      {(invoice.status === "draft" || invoice.status === "sent") && !pdfOpened && (
        <div style={{ color: "var(--fg-muted)" }}>{t("invoiceDetail.reviewPdfFirst")}</div>
      )}

      {showDeliveryConfirm && (
        <div
          role="dialog"
          aria-labelledby="invoice-delivery-confirm-title"
          className="card"
          style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
        >
          <h3 id="invoice-delivery-confirm-title" style={{ margin: 0 }}>{t("invoiceDetail.confirmManualDeliveryTitle")}</h3>
          <div>{t("invoiceDetail.manualDeliveryWarning")}</div>
          <label style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
            <input
              type="checkbox"
              autoFocus
              checked={manualDeliveryConfirmed}
              onChange={(event) => setManualDeliveryConfirmed(event.target.checked)}
            />
            {t("invoiceDetail.manualDeliveryCheckbox")}
          </label>
          <div style={{ display: "flex", gap: "0.6rem" }}>
            <button onClick={confirmManualDelivery} disabled={!manualDeliveryConfirmed}>{t("invoiceDetail.confirmManualDelivery")}</button>
            <button className="secondary" onClick={() => setShowDeliveryConfirm(false)}>{t("invoiceDetail.cancelSend")}</button>
          </div>
        </div>
      )}
      {invoice.status === "draft" && pdfOpened && <div style={{ color: "var(--fg-muted)" }}>{t("invoiceDetail.manualDeliveryHint")}</div>}
    </div>
  );
}
