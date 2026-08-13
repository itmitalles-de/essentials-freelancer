import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageToggle } from "./LanguageToggle";
import { useModules } from "../contexts/ModulesContext";

export function Layout() {
  const { username, logout } = useAuth();
  const { t } = useLanguage();
  const { isEnabled } = useModules();

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <nav
        style={{
          width: 200,
          borderRight: "1px solid var(--border)",
          padding: "1rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.4rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
          <img src="/icon.svg" alt="" width={24} height={24} />
          <span style={{ fontWeight: 700 }}>Essentials+ Freelancer</span>
        </div>
        {isEnabled("core.reporting") && <NavItem to="/">{t("nav.dashboard")}</NavItem>}
        {isEnabled("core.clients") && <NavItem to="/clients">{t("nav.clients")}</NavItem>}
        {isEnabled("core.projects") && <NavItem to="/projects">{t("nav.projects")}</NavItem>}
        {isEnabled("core.time_tracking") && <NavItem to="/time">{t("nav.time")}</NavItem>}
        {isEnabled("sales.quotes") && <NavItem to="/quotes">{t("nav.quotes")}</NavItem>}
        {isEnabled("sales.quote_assistant") && <NavItem to="/quote-assistant">Angebotsassistent</NavItem>}
        {isEnabled("billing.invoices") && <NavItem to="/invoices">{t("nav.invoices")}</NavItem>}
        {isEnabled("expenses.receipts") && <NavItem to="/expenses">{t("nav.expenses")}</NavItem>}
        {isEnabled("core.platform") && <NavItem to="/settings">{t("nav.settings")}</NavItem>}
        <NavItem to="/admin/modules">Admin-Center</NavItem>
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: "0.85rem", color: "var(--fg-muted)" }}>{username}</div>
        <ThemeToggle />
        <LanguageToggle />
        <button className="secondary" onClick={logout}>
          {t("nav.logout")}
        </button>
      </nav>
      <main style={{ flex: 1, padding: "1.5rem" }}>
        <Outlet />
      </main>
    </div>
  );
}

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      style={({ isActive }) => ({
        padding: "0.5rem 0.6rem",
        borderRadius: 6,
        textDecoration: "none",
        color: isActive ? "var(--accent-fg)" : "var(--fg)",
        background: isActive ? "var(--accent)" : "transparent",
        fontWeight: isActive ? 600 : 400,
      })}
    >
      {children}
    </NavLink>
  );
}
