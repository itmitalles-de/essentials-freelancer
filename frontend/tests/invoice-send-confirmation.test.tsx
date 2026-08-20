import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, openInvoicePdf } from "../src/api";
import { LanguageProvider } from "../src/contexts/LanguageContext";
import { InvoiceDetail } from "../src/pages/InvoiceDetail";
import { Invoice } from "../src/types";

vi.mock("../src/api", () => ({
  ApiError: class ApiError extends Error {},
  api: {
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  openInvoicePdf: vi.fn(),
}));

const invoice: Invoice = {
  id: 7,
  client_id: 4,
  invoice_number: "RE-2026-0007",
  issue_date: "2026-08-19",
  due_date: "2026-09-02",
  status: "draft",
  subtotal: "100.00",
  tax_total: "19.00",
  total: "119.00",
  notes: "",
  sent_at: null,
  paid_at: null,
  created_at: "2026-08-19T10:00:00",
  quote_id: null,
  line_items: [
    {
      id: 1,
      description: "TESTRECHNUNG — NICHT BUCHEN",
      quantity: "1.00",
      unit: "hours",
      unit_price: "100.00",
      net_amount: "100.00",
      tax_rate: "19.00",
      tax_amount: "19.00",
      amount: "119.00",
      project_id: null,
    },
  ],
};

describe("safe invoice delivery", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path === "/invoices/7") return invoice;
      if (path === "/clients/4") {
        return {
          id: 4,
          name: "TESTKUNDE",
          email: "billing@example.invalid",
        };
      }
      if (path === "/projects") return [];
      if (path === "/invoices/7/send-attempts") return [];
      throw new Error(`Unexpected GET ${path}`);
    });
    vi.mocked(openInvoicePdf).mockResolvedValue(undefined);
    vi.mocked(api.put).mockResolvedValue({
      ...invoice,
      status: "sent",
      sent_at: "2026-08-19T10:01:00",
    });
  });

  it("requires a PDF review and explicit manual delivery confirmation", async () => {
    const user = userEvent.setup();
    render(
      <LanguageProvider>
        <MemoryRouter initialEntries={["/invoices/7"]}>
          <Routes>
            <Route path="/invoices/:id" element={<InvoiceDetail />} />
          </Routes>
        </MemoryRouter>
      </LanguageProvider>
    );

    const deliveryButton = await screen.findByRole("button", { name: "Manuelle externe Zustellung bestätigen" });
    expect(screen.getByText("19.00 %")).toBeInTheDocument();
    expect(screen.getAllByText("19.00 €")).toHaveLength(2);
    expect(deliveryButton).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "PDF öffnen" }));
    expect(openInvoicePdf).toHaveBeenCalledWith(7, "RE-2026-0007");
    await waitFor(() => expect(deliveryButton).toBeEnabled());
    await user.click(deliveryButton);

    const dialog = screen.getByRole("dialog", {
      name: "Manuell zugestellte Rechnung bestätigen",
    });
    expect(dialog).toHaveTextContent("SMTP-Versand und automatischer Wiederversand sind deaktiviert");
    expect(dialog).toHaveTextContent("manuelle externe Zustellung");

    const confirmButton = within(dialog).getByRole("button", { name: "Manuelle externe Zustellung bestätigen" });
    expect(confirmButton).toBeDisabled();
    await user.click(
      screen.getByRole("checkbox", {
        name: /Ich habe das PDF geprüft und bestätige bewusst die manuelle externe Zustellung/,
      })
    );
    await user.click(confirmButton);

    await waitFor(() =>
      expect(api.put).toHaveBeenCalledWith(
        "/invoices/7/status",
        {
          status: "sent",
          pdf_reviewed: true,
          manual_delivery_confirmed: true,
        }
      )
    );
  });
});
