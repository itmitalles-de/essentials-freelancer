import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { ThemeToggle } from "./ThemeToggle";

export function Layout() {
  const { username, logout } = useAuth();

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
        <div style={{ fontWeight: 700, marginBottom: "1rem" }}>tracker</div>
        <NavItem to="/">Dashboard</NavItem>
        <NavItem to="/clients">Kunden</NavItem>
        <NavItem to="/time">Zeiterfassung</NavItem>
        <NavItem to="/invoices">Rechnungen</NavItem>
        <NavItem to="/settings">Einstellungen</NavItem>
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: "0.85rem", color: "var(--fg-muted)" }}>{username}</div>
        <ThemeToggle />
        <button className="secondary" onClick={logout}>
          Abmelden
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
