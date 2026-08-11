import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client, Expense, Invoice, TimeEntry } from "../types";

export function Dashboard() {
  const { t } = useLanguage();
  const [clients, setClients] = useState<Client[]>([]);
  const [unbilled, setUnbilled] = useState<TimeEntry[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);

  useEffect(() => {
    api.get<Client[]>("/clients").then(setClients);
    api.get<TimeEntry[]>("/time-entries?billed=false").then(setUnbilled);
    api.get<Invoice[]>("/invoices").then(setInvoices);
    api.get<Expense[]>("/expenses").then(setExpenses);
  }, []);

  const clientName = (id: number) => clients.find((c) => c.id === id)?.name ?? "?";

  const byClient = new Map<number, number>();
  for (const e of unbilled) {
    if (e.running_started_at) continue;
    byClient.set(e.client_id, (byClient.get(e.client_id) ?? 0) + e.duration_minutes);
  }

  const openInvoices = invoices.filter((i) => i.status === "sent");

  const currentYear = new Date().getFullYear();
  const revenue = invoices
    .filter((i) => i.status === "paid" && new Date(i.paid_at ?? i.issue_date).getFullYear() === currentYear)
    .reduce((sum, i) => sum + Number(i.total), 0);
  const expensesTotal = expenses
    .filter((e) => new Date(e.date).getFullYear() === currentYear)
    .reduce((sum, e) => sum + Number(e.amount), 0);
  const profit = revenue - expensesTotal;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <h2 style={{ margin: 0 }}>{t("dashboard.title")}</h2>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>{t("dashboard.yearTitle")} ({currentYear})</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
          <div>
            <div style={{ color: "var(--fg-muted)", fontSize: "0.85rem" }}>{t("dashboard.revenue")}</div>
            <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>{revenue.toFixed(2)} €</div>
          </div>
          <div>
            <div style={{ color: "var(--fg-muted)", fontSize: "0.85rem" }}>{t("dashboard.expenses")}</div>
            <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>{expensesTotal.toFixed(2)} €</div>
          </div>
          <div>
            <div style={{ color: "var(--fg-muted)", fontSize: "0.85rem" }}>{t("dashboard.profit")}</div>
            <div style={{ fontSize: "1.4rem", fontWeight: 700, color: profit >= 0 ? "var(--success)" : "var(--danger)" }}>
              {profit.toFixed(2)} €
            </div>
          </div>
        </div>
        <Link to="/expenses" className="btn" style={{ marginTop: "0.75rem" }}>{t("dashboard.toExpenses")}</Link>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>{t("dashboard.openHoursTitle")}</h3>
          {byClient.size === 0 ? (
            <div style={{ color: "var(--fg-muted)" }}>{t("dashboard.noOpenEntries")}</div>
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
          <Link to="/time" className="btn">{t("dashboard.toTimeTracking")}</Link>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>{t("dashboard.openInvoicesTitle")}</h3>
          {openInvoices.length === 0 ? (
            <div style={{ color: "var(--fg-muted)" }}>{t("dashboard.noOpenInvoices")}</div>
          ) : (
            <table>
              <tbody>
                {openInvoices.map((inv) => (
                  <tr key={inv.id}>
                    <td><Link to={`/invoices/${inv.id}`} className="btn btn-sm">{inv.invoice_number}</Link></td>
                    <td>{clientName(inv.client_id)}</td>
                    <td>{inv.total} €</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Link to="/invoices" className="btn">{t("dashboard.toInvoices")}</Link>
        </div>
      </div>
    </div>
  );
}
