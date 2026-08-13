import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../src/contexts/AuthContext";
import { LanguageProvider } from "../src/contexts/LanguageContext";
import { ThemeProvider } from "../src/contexts/ThemeContext";
import { Login } from "../src/pages/Login";

describe("login flow", () => {
  it("stores the token and enters the authenticated application", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ access_token: "synthetic-token" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <LanguageProvider>
          <MemoryRouter initialEntries={["/login"]}>
            <AuthProvider>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/" element={<div>Authenticated workspace</div>} />
              </Routes>
            </AuthProvider>
          </MemoryRouter>
        </LanguageProvider>
      </ThemeProvider>
    );

    await user.type(screen.getByPlaceholderText("Benutzername"), "test-admin");
    await user.type(screen.getByPlaceholderText("Passwort"), "test-password");
    await user.click(screen.getByRole("button", { name: "Anmelden" }));

    expect(await screen.findByText("Authenticated workspace")).toBeInTheDocument();
    expect(localStorage.getItem("tracker-token")).toBe("synthetic-token");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          username: "test-admin",
          password: "test-password",
        }),
      })
    );
  });
});
