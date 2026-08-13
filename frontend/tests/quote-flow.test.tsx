import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../src/api";
import { LanguageProvider } from "../src/contexts/LanguageContext";
import { Quotes } from "../src/pages/Quotes";

vi.mock("../src/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
  openQuotePdf: vi.fn(),
}));

describe("quote flow", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path === "/quotes") return [];
      if (path === "/projects") return [];
      if (path === "/clients") {
        return [{ id: 3, name: "Example Client", active: true }];
      }
      throw new Error(`Unexpected GET ${path}`);
    });
    vi.mocked(api.post).mockResolvedValue({});
  });

  it("creates a quote with an explicit line item", async () => {
    const user = userEvent.setup();
    render(
      <LanguageProvider>
        <MemoryRouter>
          <Quotes />
        </MemoryRouter>
      </LanguageProvider>
    );

    await user.click(screen.getByRole("button", { name: "Neues Angebot" }));
    await user.selectOptions(screen.getAllByRole("combobox")[0], "3");
    await user.type(screen.getByPlaceholderText("Positionsbeschreibung"), "Synthetic workshop");
    await user.clear(screen.getByPlaceholderText("Einzelpreis"));
    await user.type(screen.getByPlaceholderText("Einzelpreis"), "125");
    await user.click(screen.getByRole("button", { name: "Angebot erstellen" }));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/quotes", {
        client_id: 3,
        project_id: null,
        valid_in_days: 14,
        notes: "",
        line_items: [
          {
            description: "Synthetic workshop",
            quantity: 1,
            unit: "hours",
            unit_price: 125,
          },
        ],
      })
    );
  });
});
