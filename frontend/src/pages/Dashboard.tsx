import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Client, Invoice, TimeEntry } from "../types";

export function Dashboard() {
  const [clients, setClients] = useState<Client[]>([]);
  const [unbilled, setUnbilled] = useState<TimeEntry[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  useEffect(() => {
    api.get<Client[]>("/clients").then(setClients);
    api.get<TimeEntry[]>("/time-entries?billed=false").then(setUnbilled);
    api.get<Invoice[]>("/invoices").then(setInvoices);
  }, []);

  const clientName = (id: number) => clients.find((c) => c.id === id)?.name ?? "?";

  const byClient = new Map<number, number>();
  for (const e of unbilled) {
    if (e.running_started_at) continue;
    byClient.set(e.client_id, (byClient.get(e.client_id) ?? 0) + e.duration_minutes);
  }

  const openInvoices = invoices.filter((i) => i.status === "sent");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <h2 style={{ margin: 0 }}>Dashboard</h2>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Offene Stunden je Kunde</h3>
          {byClient.size === 0 ? (
            <div style={{ color: "var(--fg-muted)" }}>Keine offenen Zeiteinträge.</div>
          ) : (
            <table>
              <tbody>
                {Array.from(byClient.entries()).map(([clientId, minutes]) => (
                  <tr key={clientId}>
                    <td>{clientName(clientId)}</td>
                    <td>{(minutes / 60).toFixed(2)} h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Link to="/time">Zur Zeiterfassung →</Link>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Offene Rechnungen (versendet, unbezahlt)</h3>
          {openInvoices.length === 0 ? (
            <div style={{ color: "var(--fg-muted)" }}>Keine offenen Rechnungen.</div>
          ) : (
            <table>
              <tbody>
                {openInvoices.map((inv) => (
                  <tr key={inv.id}>
                    <td><Link to={`/invoices/${inv.id}`}>{inv.invoice_number}</Link></td>
                    <td>{clientName(inv.client_id)}</td>
                    <td>{inv.total} €</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Link to="/invoices">Zu den Rechnungen →</Link>
        </div>
      </div>
    </div>
  );
}
