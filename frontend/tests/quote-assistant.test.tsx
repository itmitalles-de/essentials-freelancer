import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../src/api";
import { QuoteAssistant } from "../src/pages/QuoteAssistant";

vi.mock("../src/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const catalog = [{
  id: 1,
  stable_key: "service.synthetic",
  kind: "service",
  name: "Synthetic service",
  active: true,
  created_at: "2026-08-13T00:00:00",
  versions: [{
    id: 11,
    item_id: 1,
    version: 1,
    description: "Synthetic service line",
    unit: "hours",
    net_unit_price: "100.00",
    tax_rate: "19.00",
    valid_from: "2020-01-01",
    valid_until: null,
    created_at: "2026-08-13T00:00:00",
  }],
}];

const preview = {
  pricing_date: "2026-08-13",
  lines: [],
  tax_breakdown: [],
  calculation_steps: [
    { key: "base_net", label: "Positionen netto", expression: "Menge × Nettopreis", amount: "100.00" },
    { key: "gross_total", label: "Gesamtbetrag", expression: "Netto + Steuer", amount: "119.00" },
  ],
  base_net_total: "100.00",
  surcharge_percent: "0.00",
  surcharge_amount: "0.00",
  discount_percent: "0.00",
  discount_amount: "0.00",
  net_total: "100.00",
  tax_total: "19.00",
  total: "119.00",
};

describe("deterministic quote assistant UI", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path === "/clients") return [{ id: 3, name: "Synthetic client", active: true }];
      if (path === "/projects") return [];
      if (path === "/quote-assistant/catalog/items") return catalog;
      if (path === "/quote-assistant/packages") return [];
      if (path === "/quote-assistant/templates") return [];
      if (path === "/quote-assistant/drafts") return [];
      throw new Error(`Unexpected GET ${path}`);
    });
    vi.mocked(api.post).mockImplementation(async (path: string) => {
      if (path === "/quote-assistant/preview") return preview;
      if (path === "/quote-assistant/drafts") return { id: 7 };
      return {};
    });
  });

  it("shows the calculation path and saves an unapproved draft", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><QuoteAssistant /></MemoryRouter>);

    await user.selectOptions(await screen.findByLabelText("Kunde"), "3");
    await user.type(screen.getByLabelText("Titel"), "Synthetic scope");
    await user.click(screen.getByRole("checkbox", { name: "Kalkulationsposition Synthetic service" }));
    await user.click(screen.getByRole("button", { name: "Rechenweg anzeigen" }));

    expect(await screen.findByText("Gesamt: 119.00 €")).toBeInTheDocument();
    expect(screen.getByText("Netto + Steuer")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Als ungeprüften Entwurf speichern" }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith(
      "/quote-assistant/drafts",
      expect.objectContaining({
        client_id: 3,
        title: "Synthetic scope",
        selections: [{ catalog_version_id: 11, quantity: "1" }],
      })
    ));
  });
});
