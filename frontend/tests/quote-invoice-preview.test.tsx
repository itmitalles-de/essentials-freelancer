import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../src/api";
import { LanguageProvider } from "../src/contexts/LanguageContext";
import { Quotes } from "../src/pages/Quotes";

vi.mock("../src/api", () => ({
  ApiError: class ApiError extends Error {},
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  openQuotePdf: vi.fn(),
}));

describe("fixed-quote invoice conversion", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path === "/quotes") return [{
        id: 3,
        client_id: 4,
        project_id: 5,
        quote_number: "AN-2026-0003",
        issue_date: "2026-08-20",
        valid_until: "2026-09-03",
        status: "accepted",
        subtotal: "100.00",
        tax_total: "0.00",
        total: "100.00",
        notes: "",
        converted_invoice_id: null,
        created_at: "2026-08-20T00:00:00",
        line_items: [],
      }];
      if (path === "/clients") return [{ id: 4, name: "TESTKUNDE" }];
      if (path === "/projects") return [{ id: 5, client_id: 4, name: "TESTPROJEKT", active: true }];
      throw new Error(`Unexpected GET ${path}`);
    });
    vi.mocked(api.post).mockImplementation(async (path: string) => {
      if (path === "/quotes/3/invoice-preview") return {
        quote_id: 3,
        lines: [{
          quote_line_item_id: 9,
          description: "Festpreisleistung",
          quantity: "1.00",
          unit: "flat",
          unit_price: "100.00",
          actual_minutes: null,
          billable_minutes: null,
          rate_type: "fixed_quote",
          minimum_minutes: null,
          increment_minutes: null,
          service_mode: null,
          billing_reason: "accepted_quote_fixed_price",
          service_date: "2026-08-20",
          project_id: 5,
          project_name: "TESTPROJEKT",
          net_amount: "100.00",
          tax_rate: "0.00",
          tax_amount: "0.00",
          total_amount: "100.00",
        }],
        work_total: "0.00",
        travel_total: "0.00",
        fixed_total: "100.00",
        subtotal: "100.00",
        tax_total: "0.00",
        total: "100.00",
        tax_status: "small_business_section_19",
        tax_notice: "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.",
        service_date: "2026-08-20",
        due_date: "2026-09-03",
        confirmation_token: "quote-confirm:synthetic-preview-token",
      };
      if (path === "/quotes/3/convert") return {};
      throw new Error(`Unexpected POST ${path}`);
    });
  });

  it("requires a visible preview and explicit confirmation", async () => {
    const user = userEvent.setup();
    render(
      <LanguageProvider>
        <MemoryRouter>
          <Quotes />
        </MemoryRouter>
      </LanguageProvider>
    );

    await user.click(await screen.findByRole("button", { name: "Rechnung erstellen" }));
    await user.click(screen.getByRole("button", { name: "Rechnungsvorschau anzeigen" }));
    await screen.findByRole("heading", { name: "Festpreis-Rechnung vor Erstellung prüfen" });
    expect(screen.getAllByText("Nicht anwendbar (Festpreis)")).toHaveLength(2);
    expect(screen.getByText(/accepted_quote_fixed_price/)).toHaveTextContent("Nicht anwendbar (Festpreis)");
    expect(screen.getByText(/small_business_section_19/)).toHaveTextContent("§ 19 UStG");

    const confirm = screen.getByRole("checkbox", { name: /Leistungsdatum, Festpreispositionen, Steuerstatus und Summen/ });
    const create = screen.getByRole("button", { name: "Bestätigen und Rechnung erstellen" });
    expect(create).toBeDisabled();
    await user.click(confirm);
    await user.click(create);

    await waitFor(() => expect(api.post).toHaveBeenCalledWith(
      "/quotes/3/convert",
      {
        service_date: expect.any(String),
        billing_confirmation_token: "quote-confirm:synthetic-preview-token",
        billing_confirmed: true,
      }
    ));
  });
});
