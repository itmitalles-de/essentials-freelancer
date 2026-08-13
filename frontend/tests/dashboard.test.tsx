import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, downloadAuthenticated } from "../src/api";
import { Dashboard } from "../src/pages/Dashboard";
import { ReportSummary } from "../src/types";

vi.mock("../src/api", () => ({
  api: { get: vi.fn() },
  downloadAuthenticated: vi.fn().mockResolvedValue(undefined),
}));

const labels: Record<string, string> = {
  "dashboard.title": "Dashboard",
  "dashboard.filters": "Berichtsfilter",
  "dashboard.from": "Von",
  "dashboard.to": "Bis",
  "dashboard.client": "Kunde",
  "dashboard.project": "Projekt",
  "dashboard.all": "Alle",
  "dashboard.expenseCategory": "Ausgabenkategorie",
  "dashboard.apply": "Filter anwenden",
  "dashboard.loading": "Bericht wird geladen…",
  "dashboard.overview": "Berichtsübersicht",
  "dashboard.capturedHours": "Erfasste Stunden",
  "dashboard.billableHours": "Nicht abgerechnete Stunden",
  "dashboard.openAmount": "Offener Rechnungsbetrag",
  "dashboard.paidAmount": "Bezahlter Rechnungsbetrag",
  "dashboard.expenseAmount": "Ausgaben",
  "dashboard.conversionRate": "Angebotskonversion",
  "dashboard.timeTitle": "Stunden nach Kunde und Projekt",
  "dashboard.quotesTitle": "Angebotsstatus",
  "dashboard.invoicesTitle": "Rechnungsstatus",
  "dashboard.expensesTitle": "Ausgaben nach Kategorie",
  "dashboard.exportCsv": "CSV exportieren",
  "dashboard.amount": "Betrag",
  "dashboard.quote.draft": "Entwurf",
  "dashboard.quote.sent": "Versendet",
  "dashboard.quote.accepted": "Angenommen",
  "dashboard.quote.rejected": "Abgelehnt",
  "dashboard.quote.converted": "Umgewandelt",
  "dashboard.invoice.draft": "Entwurf",
  "dashboard.invoice.sent": "Versendet",
  "dashboard.invoice.overdue": "Überfällig",
  "dashboard.invoice.paid": "Bezahlt",
  "dashboard.invoice.cancelled": "Storniert",
};

vi.mock("../src/contexts/LanguageContext", () => ({
  useLanguage: () => ({ t: (key: string) => labels[key] ?? key, lang: "de" }),
}));

const report: ReportSummary = {
  date_from: "2026-01-01",
  date_to: "2026-08-13",
  client_id: null,
  project_id: null,
  time: {
    captured_hours: "12.50",
    unbilled_hours: "4.00",
    groups: [
      {
        client_id: 1,
        project_id: 7,
        captured_hours: "12.50",
        unbilled_hours: "4.00",
      },
    ],
  },
  quotes: {
    statuses: { draft: 1, sent: 2, accepted: 0, rejected: 1, converted: 3 },
    conversion_rate_percent: "75.00",
  },
  invoices: {
    statuses: { draft: 1, sent: 2, overdue: 1, paid: 4, cancelled: 0 },
    open_amount: "300.00",
    paid_amount: "900.00",
  },
  expenses: { total: "55.50", categories: [{ category: "Software", amount: "55.50" }] },
};

describe("operational dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(downloadAuthenticated).mockResolvedValue(undefined);
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.startsWith("/clients")) {
        return [{ id: 1, name: "Alpha", active: true }] as never;
      }
      if (path.startsWith("/projects")) {
        return [{ id: 7, client_id: 1, name: "Launch", active: true }] as never;
      }
      return report as never;
    });
  });

  it("renders report dimensions, applies filters, and exports the filtered view", async () => {
    const user = userEvent.setup();
    render(<Dashboard />);

    expect((await screen.findAllByText("12,50 h")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Alpha").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Launch").length).toBeGreaterThan(0);
    expect(screen.getByText("Software")).toBeInTheDocument();
    expect(screen.getByText(/300,00\s*€/)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Kunde"), "1");
    await user.selectOptions(screen.getByLabelText("Projekt"), "7");
    await user.type(screen.getByLabelText("Ausgabenkategorie"), "Software");
    await user.click(screen.getByRole("button", { name: "Filter anwenden" }));

    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringMatching(/\/reports\/summary\?.*client_id=1.*project_id=7.*expense_category=Software/)
      )
    );

    await user.click(screen.getAllByRole("button", { name: "CSV exportieren" })[0]);
    expect(downloadAuthenticated).toHaveBeenCalledWith(
      expect.stringMatching(/\/reports\/time\.csv\?.*client_id=1.*project_id=7/),
      "time.csv"
    );
  });
});
