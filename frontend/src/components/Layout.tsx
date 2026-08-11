import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageToggle } from "./LanguageToggle";

export function Layout() {
  const { username, logout } = useAuth();
  const { t } = useLanguage();

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
          <span style={{ fontWeight: 700 }}>freelancer</span>
        </div>
        <NavItem to="/">{t("nav.dashboard")}</NavItem>
        <NavItem to="/clients">{t("nav.clients")}</NavItem>
        <NavItem to="/time">{t("nav.time")}</NavItem>
        <NavItem to="/invoices">{t("nav.invoices")}</NavItem>
        <NavItem to="/expenses">{t("nav.expenses")}</NavItem>
        <NavItem to="/settings">{t("nav.settings")}</NavItem>
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
