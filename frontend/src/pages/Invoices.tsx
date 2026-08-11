import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, openInvoicePdf } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client, Invoice, TimeEntry } from "../types";

export function Invoices() {
  const { t } = useLanguage();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState<number | "">("");
  const [unbilled, setUnbilled] = useState<TimeEntry[]>([]);
  const [selectedEntries, setSelectedEntries] = useState<Set<number>>(new Set());

  const loadInvoices = () => api.get<Invoice[]>("/invoices").then(setInvoices);

  useEffect(() => {
    loadInvoices();
    api.get<Client[]>("/clients").then(setClients);
  }, []);

  useEffect(() => {
    if (!selectedClientId) {
      setUnbilled([]);
      return;
    }
    api
      .get<TimeEntry[]>(`/time-entries?client_id=${selectedClientId}&billed=false`)
      .then((entries) => {
        setUnbilled(entries.filter((e) => !e.running_started_at));
        setSelectedEntries(new Set());
      });
  }, [selectedClientId]);

  const toggleEntry = (id: number) => {
    setSelectedEntries((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const createInvoice = async () => {
    if (!selectedClientId || selectedEntries.size === 0) return;
    await api.post("/invoices", {
      client_id: selectedClientId,
      time_entry_ids: Array.from(selectedEntries),
    });
    setShowCreate(false);
    setSelectedClientId("");
    loadInvoices();
  };

  const clientName = (id: number) => clients.find((c) => c.id === id)?.name ?? "?";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{t("invoices.title")}</h2>
        <button onClick={() => setShowCreate((v) => !v)}>{showCreate ? t("invoices.cancel") : t("invoices.new")}</button>
      </div>

      {showCreate && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <select value={selectedClientId} onChange={(e) => setSelectedClientId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">{t("invoices.chooseClient")}</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

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
                      <th>{t("invoices.colDuration")}</th>
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
                        <td>{(e.duration_minutes / 60).toFixed(2)} h</td>
                        <td>{e.hourly_rate} €/h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <button onClick={createInvoice} disabled={selectedEntries.size === 0}>
                {t("invoices.create")} ({selectedEntries.size} {t("invoices.entries")})
              </button>
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
              <td><Link to={`/invoices/${inv.id}`}>{inv.invoice_number}</Link></td>
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
