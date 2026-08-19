import { render, screen, waitFor } from "@testing-library/react";
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
    postIdempotent: vi.fn(),
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
    vi.mocked(api.postIdempotent).mockResolvedValue({
      ...invoice,
      status: "sent",
      sent_at: "2026-08-19T10:01:00",
    });
  });

  it("requires a PDF review and an accessible detail confirmation", async () => {
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

    const sendButton = await screen.findByRole("button", { name: "Per E-Mail senden" });
    expect(screen.getByText("19.00 %")).toBeInTheDocument();
    expect(screen.getByText("19.00 €")).toBeInTheDocument();
    expect(sendButton).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "PDF öffnen" }));
    expect(openInvoicePdf).toHaveBeenCalledWith(7, "RE-2026-0007");
    await waitFor(() => expect(sendButton).toBeEnabled());
    await user.click(sendButton);

    const dialog = screen.getByRole("dialog", {
      name: "Externen Rechnungsversand bestätigen",
    });
    expect(dialog).toHaveTextContent("billing@example.invalid");
    expect(dialog).toHaveTextContent("RE-2026-0007");
    expect(dialog).toHaveTextContent("119.00 €");
    expect(dialog).toHaveTextContent("Diese Aktion sendet eine externe E-Mail");

    const confirmButton = screen.getByRole("button", { name: "Externe E-Mail senden" });
    expect(confirmButton).toBeDisabled();
    await user.click(
      screen.getByRole("checkbox", {
        name: /Ich habe dieses Rechnungs-PDF geprüft/,
      })
    );
    await user.click(confirmButton);

    await waitFor(() =>
      expect(api.postIdempotent).toHaveBeenCalledWith(
        "/invoices/7/send",
        expect.any(String),
        {
          recipient: "billing@example.invalid",
          invoice_number: "RE-2026-0007",
          total: "119.00",
          pdf_reviewed: true,
          resend: false,
        }
      )
    );
  });
});
