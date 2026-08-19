import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, openInvoicePdf, ApiError } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client, Invoice, InvoiceSendAttempt, Project } from "../types";

export function InvoiceDetail() {
  const { t } = useLanguage();
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [attempts, setAttempts] = useState<InvoiceSendAttempt[]>([]);
  const [pdfOpened, setPdfOpened] = useState(false);
  const [showSendConfirm, setShowSendConfirm] = useState(false);
  const [pdfReviewed, setPdfReviewed] = useState(false);
  const [sendKey, setSendKey] = useState("");

  const load = () => {
    api.get<Invoice>(`/invoices/${id}`).then((inv) => {
      setInvoice(inv);
      api.get<Client>(`/clients/${inv.client_id}`).then(setClient);
      api.get<InvoiceSendAttempt[]>(`/invoices/${inv.id}/send-attempts`).then(setAttempts);
    });
  };

  useEffect(() => {
    load();
    api.get<Project[]>("/projects").then(setProjects);
  }, [id]);

  if (!invoice) return <div>{t("invoiceDetail.loading")}</div>;
  const projectName = (projectId: number | null) => projects.find((project) => project.id === projectId)?.name ?? "—";

  const openForReview = async () => {
    setError(null);
    try {
      await openInvoicePdf(invoice.id, invoice.invoice_number);
      setPdfOpened(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("invoiceDetail.errPdf"));
    }
  };

  const beginSend = () => {
    if (!client || !pdfOpened) return;
    setPdfReviewed(false);
    setSendKey(globalThis.crypto?.randomUUID?.() ?? `send-${Date.now()}`);
    setShowSendConfirm(true);
  };

  const send = async () => {
    if (!client || !sendKey || !pdfReviewed) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.postIdempotent<Invoice>(
        `/invoices/${invoice.id}/send`,
        sendKey,
        {
          recipient: client.email,
          invoice_number: invoice.invoice_number,
          total: invoice.total,
          pdf_reviewed: true,
          resend: invoice.status === "sent",
        },
      );
      setInvoice(updated);
      setShowSendConfirm(false);
      setPdfOpened(false);
      setAttempts(await api.get<InvoiceSendAttempt[]>(`/invoices/${invoice.id}/send-attempts`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("invoiceDetail.errSend"));
      setShowSendConfirm(false);
      setPdfOpened(false);
      setSendKey("");
      setAttempts(await api.get<InvoiceSendAttempt[]>(`/invoices/${invoice.id}/send-attempts`));
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
        <div><strong>{t("invoiceDetail.subtotal")}</strong> {invoice.subtotal} €</div>
        <div><strong>{t("invoiceDetail.tax")}</strong> {invoice.tax_total} €</div>
        <div><strong>{t("invoiceDetail.total")}</strong> {invoice.total} €</div>
      </div>

      <table className="card">
        <thead>
          <tr>
            <th>{t("invoiceDetail.colDescription")}</th>
            <th>{t("invoiceDetail.colHours")}</th>
            <th>{t("invoiceDetail.colUnit")}</th>
            <th>{t("invoiceDetail.colPricePerHour")}</th>
            <th>{t("invoiceDetail.colTax")}</th>
            <th>{t("invoiceDetail.colProject")}</th>
            <th>{t("invoiceDetail.colAmount")}</th>
          </tr>
        </thead>
        <tbody>
          {invoice.line_items.map((li) => (
            <tr key={li.id}>
              <td>{li.description}</td>
              <td>{li.quantity}</td>
              <td>{li.unit}</td>
              <td>{li.unit_price} €</td>
              <td>{li.tax_rate} %</td>
              <td>{projectName(li.project_id)}</td>
              <td>{li.amount} €</td>
            </tr>
          ))}
        </tbody>
      </table>

      {error && <div style={{ color: "var(--danger)" }}>{error}</div>}

      <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="secondary" onClick={openForReview}>{t("invoiceDetail.openPdf")}</button>
        {(invoice.status === "draft" || invoice.status === "sent") && (
          <button onClick={beginSend} disabled={busy || !client?.email || !pdfOpened}>
            {invoice.status === "sent" ? t("invoiceDetail.resendEmail") : t("invoiceDetail.sendEmail")}
          </button>
        )}
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

      {showSendConfirm && client && (
        <div
          role="dialog"
          aria-labelledby="invoice-send-confirm-title"
          aria-describedby="invoice-send-confirm-warning"
          className="card"
          style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
        >
          <h3 id="invoice-send-confirm-title" style={{ margin: 0 }}>
            {invoice.status === "sent" ? t("invoiceDetail.confirmResendTitle") : t("invoiceDetail.confirmSendTitle")}
          </h3>
          <div><strong>{t("invoiceDetail.recipient")}</strong> {client.email}</div>
          <div><strong>{t("invoiceDetail.invoiceNumber")}</strong> {invoice.invoice_number}</div>
          <div><strong>{t("invoiceDetail.amount")}</strong> {invoice.total} €</div>
          <div id="invoice-send-confirm-warning">{t("invoiceDetail.externalEmailWarning")}</div>
          <label style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
            <input
              type="checkbox"
              autoFocus
              checked={pdfReviewed}
              onChange={(event) => setPdfReviewed(event.target.checked)}
            />
            {t("invoiceDetail.pdfReviewed")}
          </label>
          <div style={{ display: "flex", gap: "0.6rem" }}>
            <button onClick={send} disabled={busy || !pdfReviewed}>
              {invoice.status === "sent" ? t("invoiceDetail.confirmResend") : t("invoiceDetail.confirmSend")}
            </button>
            <button className="secondary" onClick={() => setShowSendConfirm(false)} disabled={busy}>
              {t("invoiceDetail.cancelSend")}
            </button>
          </div>
        </div>
      )}

      {attempts.length > 0 && (
        <section aria-labelledby="invoice-send-history-title">
          <h3 id="invoice-send-history-title">{t("invoiceDetail.sendHistory")}</h3>
          <ul>
            {attempts.map((attempt) => (
              <li key={attempt.id}>
                {attempt.is_resend ? t("invoiceDetail.resend") : t("invoiceDetail.firstSend")}
                {" — "}{attempt.outcome}{" — "}{attempt.recipient}{" — "}{attempt.created_at}
                {attempt.failure_code ? ` (${attempt.failure_code})` : ""}
                {attempt.message_id_redacted ? ` — ${attempt.message_id_redacted}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
