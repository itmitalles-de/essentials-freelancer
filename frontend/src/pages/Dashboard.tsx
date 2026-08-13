import { FormEvent, useEffect, useMemo, useState } from "react";

import { api, downloadAuthenticated } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client, Project, ReportSummary } from "../types";

function localDate(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function initialDates() {
  const now = new Date();
  return {
    dateFrom: localDate(new Date(now.getFullYear(), 0, 1)),
    dateTo: localDate(now),
  };
}

export function Dashboard() {
  const { t, lang } = useLanguage();
  const initial = useMemo(initialDates, []);
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [dateFrom, setDateFrom] = useState(initial.dateFrom);
  const [dateTo, setDateTo] = useState(initial.dateTo);
  const [clientId, setClientId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [expenseCategory, setExpenseCategory] = useState("");
  const [query, setQuery] = useState(
    `?date_from=${initial.dateFrom}&date_to=${initial.dateTo}`
  );
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.get<Client[]>("/clients?limit=500"), api.get<Project[]>("/projects?limit=500")])
      .then(([nextClients, nextProjects]) => {
        setClients(nextClients);
        setProjects(nextProjects);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    setError("");
    api.get<ReportSummary>(`/reports/summary${query}`)
      .then(setReport)
      .catch((reason: Error) => setError(reason.message));
  }, [query]);

  const reportParams = () => {
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (clientId) params.set("client_id", clientId);
    if (projectId) params.set("project_id", projectId);
    if (expenseCategory) params.set("expense_category", expenseCategory);
    const value = params.toString();
    return value ? `?${value}` : "";
  };

  const applyFilters = (event: FormEvent) => {
    event.preventDefault();
    setQuery(reportParams());
  };

  const clientName = (id: number) => clients.find((item) => item.id === id)?.name ?? `#${id}`;
  const projectName = (id: number | null) =>
    id === null ? "—" : projects.find((item) => item.id === id)?.name ?? `#${id}`;
  const visibleProjects = projects.filter(
    (project) => !clientId || project.client_id === Number(clientId)
  );
  const number = (value: string) => Number(value).toLocaleString(lang === "de" ? "de-DE" : "en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const currency = (value: string) =>
    new Intl.NumberFormat(lang === "de" ? "de-DE" : "en-US", {
      style: "currency",
      currency: "EUR",
    }).format(Number(value));
  const exportCsv = (kind: "time" | "quotes" | "invoices" | "expenses") => {
    const params = new URLSearchParams(reportParams().slice(1));
    if (kind !== "expenses") params.delete("expense_category");
    if (kind === "expenses") {
      params.delete("client_id");
      params.delete("project_id");
    }
    const suffix = params.toString() ? `?${params}` : "";
    return downloadAuthenticated(`/reports/${kind}.csv${suffix}`, `${kind}.csv`).catch(
      (reason: Error) => setError(reason.message)
    );
  };

  return (
    <div className="stack reporting-dashboard">
      <h2>{t("dashboard.title")}</h2>
      <form className="card report-filters" onSubmit={applyFilters} aria-label={t("dashboard.filters")}>
        <label>{t("dashboard.from")}<input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></label>
        <label>{t("dashboard.to")}<input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></label>
        <label>{t("dashboard.client")}<select value={clientId} onChange={(e) => { setClientId(e.target.value); setProjectId(""); }}><option value="">{t("dashboard.all")}</option>{clients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>{t("dashboard.project")}<select value={projectId} onChange={(e) => setProjectId(e.target.value)}><option value="">{t("dashboard.all")}</option>{visibleProjects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>{t("dashboard.expenseCategory")}<input value={expenseCategory} onChange={(e) => setExpenseCategory(e.target.value)} /></label>
        <button type="submit">{t("dashboard.apply")}</button>
      </form>

      {error && <div className="alert error" role="alert">{error}</div>}
      {!report && !error && <div role="status">{t("dashboard.loading")}</div>}
      {report && (
        <>
          <section className="report-card-grid" aria-label={t("dashboard.overview")}>
            <Metric label={t("dashboard.capturedHours")} value={`${number(report.time.captured_hours)} h`} />
            <Metric label={t("dashboard.billableHours")} value={`${number(report.time.unbilled_hours)} h`} />
            <Metric label={t("dashboard.openAmount")} value={currency(report.invoices.open_amount)} />
            <Metric label={t("dashboard.paidAmount")} value={currency(report.invoices.paid_amount)} />
            <Metric label={t("dashboard.expenseAmount")} value={currency(report.expenses.total)} />
            <Metric label={t("dashboard.conversionRate")} value={`${number(report.quotes.conversion_rate_percent)} %`} />
          </section>

          <ReportSection title={t("dashboard.timeTitle")} exportLabel={t("dashboard.exportCsv")} onExport={() => exportCsv("time")}>
            <table><thead><tr><th>{t("dashboard.client")}</th><th>{t("dashboard.project")}</th><th>{t("dashboard.capturedHours")}</th><th>{t("dashboard.billableHours")}</th></tr></thead><tbody>{report.time.groups.map((group) => <tr key={`${group.client_id}-${group.project_id ?? "none"}`}><td>{clientName(group.client_id)}</td><td>{projectName(group.project_id)}</td><td>{number(group.captured_hours)} h</td><td>{number(group.unbilled_hours)} h</td></tr>)}</tbody></table>
          </ReportSection>

          <div className="report-two-columns">
            <ReportSection title={t("dashboard.quotesTitle")} exportLabel={t("dashboard.exportCsv")} onExport={() => exportCsv("quotes")}>
              <StatusList statuses={report.quotes.statuses} translate={(key) => t(`dashboard.quote.${key}` as Parameters<typeof t>[0])} />
            </ReportSection>
            <ReportSection title={t("dashboard.invoicesTitle")} exportLabel={t("dashboard.exportCsv")} onExport={() => exportCsv("invoices")}>
              <StatusList statuses={report.invoices.statuses} translate={(key) => t(`dashboard.invoice.${key}` as Parameters<typeof t>[0])} />
            </ReportSection>
          </div>

          <ReportSection title={t("dashboard.expensesTitle")} exportLabel={t("dashboard.exportCsv")} onExport={() => exportCsv("expenses")}>
            <table><thead><tr><th>{t("dashboard.expenseCategory")}</th><th>{t("dashboard.amount")}</th></tr></thead><tbody>{report.expenses.categories.map((item) => <tr key={item.category}><td>{item.category}</td><td>{currency(item.amount)}</td></tr>)}</tbody></table>
          </ReportSection>
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="card report-metric"><span>{label}</span><strong>{value}</strong></div>;
}

function ReportSection({ title, exportLabel, onExport, children }: { title: string; exportLabel: string; onExport: () => void; children: React.ReactNode }) {
  return <section className="card report-section"><div className="report-heading"><h3>{title}</h3><button type="button" className="secondary" onClick={onExport}>{exportLabel}</button></div>{children}</section>;
}

function StatusList({ statuses, translate }: { statuses: Record<string, number>; translate: (key: string) => string }) {
  return <dl className="report-statuses">{Object.entries(statuses).map(([key, value]) => <div key={key}><dt>{translate(key)}</dt><dd>{value}</dd></div>)}</dl>;
}
