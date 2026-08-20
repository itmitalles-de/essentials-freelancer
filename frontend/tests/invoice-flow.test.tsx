import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../src/api";
import { LanguageProvider } from "../src/contexts/LanguageContext";
import { Invoices } from "../src/pages/Invoices";

vi.mock("../src/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    postIdempotent: vi.fn(),
  },
  openInvoicePdf: vi.fn(),
}));

let settingsRequest: Promise<{ default_tax_rate: string }>;

describe("invoice creation flow", () => {
  afterEach(cleanup);

  beforeEach(() => {
    settingsRequest = Promise.resolve({ default_tax_rate: "0.00" });
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path === "/invoices") return [];
      if (path === "/settings") return settingsRequest;
      if (path === "/clients") {
        return [
          {
            id: 4,
            name: "Example Consulting",
            contact_person: "",
            address_line1: "",
            address_line2: "",
            zip_city: "",
            email: "billing@example.invalid",
            hourly_rate: "80.00",
            notes: "",
            active: true,
            created_at: "2026-08-13T00:00:00",
          },
        ];
      }
      if (path === "/time-entries?client_id=4&billed=false") {
        return [
          {
            id: 9,
            client_id: 4,
            date: "2026-08-13",
            description: "Synthetic implementation work",
            duration_minutes: 90,
            hourly_rate: "80.00",
            running_started_at: null,
            billed: false,
            invoice_id: null,
          },
        ];
      }
      throw new Error(`Unexpected GET ${path}`);
    });
    vi.mocked(api.post).mockImplementation(async (path: string) => {
      if (path === "/invoices/preview") {
        return {
          lines: [{
            time_entry_id: 9,
            line_kind: "work",
            description: "Synthetic implementation work",
            actual_minutes: 90,
            billable_minutes: 90,
            hourly_rate: "80.00",
            rate_type: "custom",
            minimum_minutes: 0,
            increment_minutes: null,
            service_mode: "remote",
            is_first_order: false,
            billing_reason: "actual",
            billing_policy_id: null,
            date: "2026-08-13",
            project_id: null,
            net_amount: "120.00",
            tax_amount: "0.00",
            total_amount: "120.00",
          }],
          work_total: "120.00",
          travel_total: "0.00",
          subtotal: "120.00",
          tax_total: "0.00",
          total: "120.00",
          tax_rate: "0",
          tax_status: "standard",
          tax_notice: null,
          confirmation_token: "preview-token",
        };
      }
      return {};
    });
    vi.mocked(api.postIdempotent).mockResolvedValue({});
  });

  it("selects open time and creates an invoice for the matching client", async () => {
    const user = userEvent.setup();
    render(
      <LanguageProvider>
        <MemoryRouter>
          <Invoices />
        </MemoryRouter>
      </LanguageProvider>
    );

    const newInvoiceButton = screen.getByRole("button", { name: "Neue Rechnung" });
    await waitFor(() => expect(newInvoiceButton).toBeEnabled());
    await user.click(newInvoiceButton);
    await user.selectOptions(
      screen.getByRole("combobox"),
      screen.getByRole("option", { name: "Example Consulting" })
    );
    await user.click(await screen.findByRole("checkbox"));
    expect(screen.getByRole("spinbutton", { name: "Steuersatz (%)" })).toHaveValue(0);
    await user.click(screen.getByRole("button", { name: "Abrechnungsvorschau anzeigen" }));
    await screen.findByRole("heading", { name: "Abrechnungsvorschau vor Rechnung" });
    await user.click(screen.getAllByRole("checkbox")[1]);
    await user.click(screen.getByRole("button", { name: "Rechnung erstellen (1 Einträge)" }));

    await waitFor(() =>
      expect(api.postIdempotent).toHaveBeenCalledWith(
        "/invoices",
        expect.any(String),
        {
          client_id: 4,
          time_entry_ids: [9],
          tax_rate: "0.00",
          billing_confirmation_token: "preview-token",
          billing_confirmed: true,
        }
      )
    );
  });

  it("waits for the configured non-zero tax profile before opening invoice creation", async () => {
    let resolveSettings!: (value: { default_tax_rate: string }) => void;
    settingsRequest = new Promise((resolve) => {
      resolveSettings = resolve;
    });

    const user = userEvent.setup();
    render(
      <LanguageProvider>
        <MemoryRouter>
          <Invoices />
        </MemoryRouter>
      </LanguageProvider>
    );

    const newInvoiceButton = screen.getByRole("button", { name: "Neue Rechnung" });
    expect(newInvoiceButton).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Steuerprofil");

    await act(async () => {
      resolveSettings({ default_tax_rate: "19.00" });
      await settingsRequest;
    });

    await waitFor(() => expect(newInvoiceButton).toBeEnabled());
    await user.click(newInvoiceButton);
    expect(screen.getByRole("spinbutton", { name: "Steuersatz (%)" })).toHaveValue(19);
  });
});
