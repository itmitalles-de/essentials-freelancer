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
  const result = await new AxeBuilder({ page }).analyze();
  const serious = result.violations.filter((item) =>
    ["serious", "critical"].includes(item.impact ?? "")
  );
  expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
}

test("normal navigation follows module state and core data is visible", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await page.getByRole("combobox", { name: "Kunde", exact: true }).selectOption({
    label: "Synthetic Full Check Client",
  });
  await page.getByRole("button", { name: "Filter anwenden" }).click();
  await expect(
    page.getByRole("cell", { name: "Synthetic Full Check Client", exact: true })
  ).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);

  await page.getByRole("link", { name: "Admin-Center" }).click();
  await expect(page.getByRole("heading", { name: "Admin-Center" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kundenspezifisch" })).toBeVisible();
  await expect(page.getByText("sales.quote_assistant", { exact: true })).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);

  await page.getByRole("link", { name: "Angebotsassistent" }).click();
  await expect(page.getByRole("heading", { name: "Angebotsassistent" })).toBeVisible();
  await expect(page.getByText("Deterministische Kalkulation ohne KI.", { exact: false })).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);
});

test("restored core data remains visible through the browser", async ({ page }) => {
  test.skip(process.env.E2E_PHASE !== "restore", "restore-only assertion");
  await login(page);
  await page.getByRole("link", { name: "Kunden" }).click();
  await expect(page.getByRole("cell", { name: "Synthetic Full Check Client", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Rechnungen" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await page.getByRole("link", { name: "Ausgaben" }).click();
  await expect(page.getByText("Synthetic PNG receipt")).toBeVisible();
  await expect(page.getByText("Synthetic JPEG receipt")).toBeVisible();
  await expect(page.getByText("Synthetic PDF receipt")).toBeVisible();
  await expectNoSeriousAccessibilityViolations(page);
});
