import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, openInvoicePdf, ApiError } from "../api";
import { Client, Invoice } from "../types";

export function InvoiceDetail() {
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

  if (!invoice) return <div>Lädt…</div>;

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.post<Invoice>(`/invoices/${invoice.id}/send`);
      setInvoice(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Versand fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  };

  const markPaid = async () => {
    const updated = await api.put<Invoice>(`/invoices/${invoice.id}/status`, { status: "paid" });
    setInvoice(updated);
  };

  const remove = async () => {
    if (!confirm("Entwurf wirklich löschen?")) return;
    await api.delete(`/invoices/${invoice.id}`);
    navigate("/invoices");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxWidth: 700 }}>
      <h2 style={{ margin: 0 }}>Rechnung {invoice.invoice_number}</h2>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <div><strong>Kunde:</strong> {client?.name}</div>
        <div><strong>Datum:</strong> {invoice.issue_date} — <strong>Fällig:</strong> {invoice.due_date}</div>
        <div><strong>Status:</strong> <span className={`badge ${invoice.status}`}>{invoice.status}</span></div>
        <div><strong>Gesamt:</strong> {invoice.total} €</div>
      </div>

      <table className="card">
        <thead>
          <tr>
            <th>Beschreibung</th>
            <th>Stunden</th>
            <th>Preis/Std</th>
            <th>Betrag</th>
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
        <button className="secondary" onClick={() => openInvoicePdf(invoice.id, invoice.invoice_number)}>PDF öffnen</button>
        {invoice.status === "draft" && (
          <button onClick={send} disabled={busy}>Per E-Mail senden</button>
        )}
        {invoice.status === "sent" && (
          <button onClick={markPaid}>Als bezahlt markieren</button>
        )}
        {invoice.status === "draft" && (
          <button className="danger" onClick={remove}>Löschen</button>
        )}
      </div>
    </div>
  );
}
