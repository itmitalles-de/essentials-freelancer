import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

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

describe("invoice creation flow", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path === "/invoices") return [];
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
    vi.mocked(api.post).mockResolvedValue({});
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

    await user.click(screen.getByRole("button", { name: "Neue Rechnung" }));
    await user.selectOptions(
      screen.getByRole("combobox"),
      screen.getByRole("option", { name: "Example Consulting" })
    );
    await user.click(await screen.findByRole("checkbox"));
    await user.type(screen.getByRole("spinbutton", { name: "Steuersatz (%)" }), "0");
    await user.click(
      screen.getByRole("button", { name: "Rechnung erstellen (1 Einträge)" })
    );

    await waitFor(() =>
      expect(api.postIdempotent).toHaveBeenCalledWith(
        "/invoices",
        expect.any(String),
        {
          client_id: 4,
          time_entry_ids: [9],
          tax_rate: "0",
        }
      )
    );
  });
});
