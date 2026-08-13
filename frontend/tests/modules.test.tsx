import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../src/api";
import { Layout } from "../src/components/Layout";
import { ModulesProvider } from "../src/contexts/ModulesContext";
import { ThemeProvider } from "../src/contexts/ThemeContext";
import { AdminModules } from "../src/pages/AdminModules";
import { ModuleStatus } from "../src/types";

vi.mock("../src/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

vi.mock("../src/contexts/AuthContext", () => ({
  useAuth: () => ({ username: "test-admin", logout: vi.fn() }),
}));

vi.mock("../src/contexts/LanguageContext", () => ({
  useLanguage: () => ({
    t: (key: string) => ({
      "nav.dashboard": "Dashboard",
      "nav.clients": "Kunden",
      "nav.projects": "Projekte",
      "nav.time": "Zeiten",
      "nav.quotes": "Angebote",
      "nav.invoices": "Rechnungen",
      "nav.expenses": "Ausgaben",
      "nav.settings": "Einstellungen",
      "nav.logout": "Abmelden",
    }[key] ?? key),
    choice: "de",
    lang: "de",
    setChoice: vi.fn(),
  }),
}));

function status(id: string, state: ModuleStatus["state"], group = "Arbeit"): ModuleStatus {
  return {
    state,
    configuration: [],
    secrets: [],
    health: { status: state, message: "Synthetic health result" },
    manifest: {
      id,
      schema_version: 1,
      display_name: id,
      description: "Synthetic module",
      group,
      module_type: "built_in",
      required: id.startsWith("core."),
      default_state: state,
      dependencies: [],
      conflicts: [],
      compatible_product_versions: ">=0.2,<1.0",
      compatible_schema_versions: ">=0003_modules",
      configuration_fields: [],
      secret_requirements: [],
      api_boundaries: ["/api/example"],
      navigation_boundaries: ["/example"],
      job_boundaries: [],
      healthcheck: "Synthetic check",
      data_ownership: [],
      export_behavior: "included",
      backup_behavior: "included",
      restore_behavior: "restored",
      activation_behavior: "enable",
      deactivation_behavior: "retain data",
      update_behavior: "migrate",
    },
  };
}

const catalog = [
  status("core.platform", "enabled"),
  status("core.reporting", "enabled"),
  status("core.clients", "enabled"),
  status("core.projects", "enabled"),
  status("core.time_tracking", "enabled"),
  status("sales.quotes", "disabled", "Verkauf und Angebote"),
  status("billing.invoices", "enabled", "Abrechnung"),
  status("expenses.receipts", "enabled", "Ausgaben"),
];

describe("module-aware administration and navigation", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue(catalog);
    vi.mocked(api.post).mockResolvedValue({});
  });

  it("removes disabled modules from normal navigation", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter>
          <ModulesProvider>
            <Routes>
              <Route path="/" element={<Layout />}>
                <Route index element={<div>Workspace</div>} />
              </Route>
            </Routes>
          </ModulesProvider>
        </MemoryRouter>
      </ThemeProvider>
    );

    expect(await screen.findByText("Essentials+ Freelancer")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Angebote" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Rechnungen" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Admin-Center" })).toBeInTheDocument();
  });

  it("activates a catalog module through the admin center", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ModulesProvider>
          <AdminModules />
        </ModulesProvider>
      </MemoryRouter>
    );

    await user.click(await screen.findByRole("button", { name: "Aktivieren" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/admin/modules/sales.quotes/enable")
    );
  });
});
