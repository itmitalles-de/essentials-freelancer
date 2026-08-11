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
  const [busy, setBusy] = useState(false);

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

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.post<Invoice>(`/invoices/${invoice.id}/send`);
      setInvoice(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("invoiceDetail.errSend"));
    } finally {
      setBusy(false);
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
        <div><strong>{t("invoiceDetail.total")}</strong> {invoice.total} €</div>
      </div>

      <table className="card">
        <thead>
          <tr>
            <th>{t("invoiceDetail.colDescription")}</th>
            <th>{t("invoiceDetail.colHours")}</th>
            <th>{t("invoiceDetail.colPricePerHour")}</th>
            <th>{t("invoiceDetail.colAmount")}</th>
          </tr>
        </thead>
        <tbody>
          {invoice.line_items.map((li) => (
            <tr key={li.id}>
              <td>{li.description}</td>
              <td>{li.quantity}</td>
              <td>{li.unit_price} €</td>
              <td>{li.amount} €</td>
            </tr>
          ))}
        </tbody>
      </table>

      {error && <div style={{ color: "var(--danger)" }}>{error}</div>}

      <div style={{ display: "flex", gap: "0.6rem" }}>
        <button className="secondary" onClick={() => openInvoicePdf(invoice.id, invoice.invoice_number)}>{t("invoiceDetail.openPdf")}</button>
        {invoice.status === "draft" && (
          <button onClick={send} disabled={busy}>{t("invoiceDetail.sendEmail")}</button>
        )}
        {invoice.status === "sent" && (
          <button onClick={markPaid}>{t("invoiceDetail.markPaid")}</button>
        )}
        {invoice.status === "draft" && (
          <button className="danger" onClick={remove}>{t("invoiceDetail.delete")}</button>
        )}
      </div>
    </div>
  );
}
