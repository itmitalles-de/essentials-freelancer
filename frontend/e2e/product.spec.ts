import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const username = process.env.E2E_USERNAME ?? "admin";
const password = process.env.E2E_PASSWORD;
if (!password) throw new Error("E2E_PASSWORD is required");

async function login(page: import("@playwright/test").Page) {
  await page.addInitScript(() => localStorage.setItem("tracker-lang", "de"));
  await page.goto("/login");
  await page.getByLabel("Benutzername").fill(username);
  await page.getByLabel("Passwort").fill(password);
  await page.getByRole("button", { name: "Anmelden" }).click();
  await expect(page.getByText("Essentials+ Freelancer")).toBeVisible();
}

async function expectNoSeriousAccessibilityViolations(
  page: import("@playwright/test").Page
) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const theme of ["light", "dark"] as const) {
    await page.evaluate((selectedTheme) => {
      document.documentElement.dataset.theme = selectedTheme;
    }, theme);
    await page.waitForFunction(
      (selectedTheme) => {
        const expected = selectedTheme === "dark" ? "rgb(20, 22, 26)" : "rgb(245, 246, 248)";
        return getComputedStyle(document.body).backgroundColor === expected;
      },
      theme
    );
    const result = await new AxeBuilder({ page }).analyze();
    const serious = result.violations.filter((item) =>
      ["serious", "critical"].includes(item.impact ?? "")
    );
    expect(
      serious,
      `${theme} theme:\n${JSON.stringify(serious, null, 2)}`
    ).toEqual([]);
  }
}

test("normal navigation follows module state and core data is visible", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await page.getByRole("combobox", { name: "Kunde", exact: true }).selectOption({
    label: "Synthetic Full Check Client",
  });
  await page.getByRole("button", { name: "Filter anwenden" }).click();
  const dashboardClientCells = page.getByRole("cell", {
    name: "Synthetic Full Check Client",
    exact: true,
  });
  await expect(dashboardClientCells).toHaveCount(2);
  await expect(dashboardClientCells.first()).toBeVisible();
  await expect(dashboardClientCells.nth(1)).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);

  await page.getByRole("link", { name: "Admin-Center" }).click();
  await expect(page.getByRole("heading", { name: "Admin-Center" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kundenspezifisch" })).toBeVisible();
  await expect(page.getByText("sales.quote_assistant", { exact: true })).toBeVisible();
  const smtpModule = page.locator("article").filter({ hasText: "communication.smtp" });
  await expect(smtpModule.getByText("Deaktiviert", { exact: true })).toBeVisible();
  await expect(smtpModule.getByRole("button", { name: "Pilotgesperrt" })).toBeDisabled();
  await expectNoSeriousAccessibilityViolations(page);

  await page.getByRole("link", { name: "Angebotsassistent" }).click();
  await expect(page.getByRole("heading", { name: "Angebotsassistent" })).toBeVisible();
  await expect(page.getByText("Deterministische Kalkulation ohne KI.", { exact: false })).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);
});

test("core data remains visible through the browser", async ({ page }) => {
  await login(page);
  await page.getByRole("link", { name: "Kunden" }).click();
  await expect(page.getByRole("heading", { name: "Kunden" })).toBeVisible();
  const clientCells = page.getByRole("cell", {
    name: "Synthetic Full Check Client",
    exact: true,
  });
  await expect(clientCells).toHaveCount(1);
  await expect(clientCells).toBeVisible();
  await page.getByRole("link", { name: "Rechnungen" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await page.locator("tbody tr").first().getByRole("link").click();
  await expect(page.getByText("31 min", { exact: true })).toBeVisible();
  await expect(page.getByText("45 min", { exact: true })).toBeVisible();
  await expect(page.getByText("small_business_section_19", { exact: false })).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);
  await page.getByRole("link", { name: "Rechnungen" }).click();
  await page.getByRole("link", { name: "Ausgaben" }).click();
  await expect(page.getByText("Synthetic PNG receipt")).toBeVisible();
  await expect(page.getByText("Synthetic JPEG receipt")).toBeVisible();
  await expect(page.getByText("Synthetic PDF receipt")).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);
});
