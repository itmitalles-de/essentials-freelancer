import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Clients } from "./pages/Clients";
import { TimeTracking } from "./pages/TimeTracking";
import { Invoices } from "./pages/Invoices";
import { InvoiceDetail } from "./pages/InvoiceDetail";
import { Expenses } from "./pages/Expenses";
import { Settings } from "./pages/Settings";
import { Projects } from "./pages/Projects";
import { Quotes } from "./pages/Quotes";
import { AdminModules } from "./pages/AdminModules";
import { ModulesProvider, useModules } from "./contexts/ModulesContext";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function ModuleGate({ moduleId, children }: { moduleId: string; children: React.ReactNode }) {
  const { loading, isEnabled } = useModules();
  if (loading) return null;
  if (!isEnabled(moduleId)) return <Navigate to="/admin/modules" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <ModulesProvider>
              <Layout />
            </ModulesProvider>
          </RequireAuth>
        }
      >
        <Route index element={<ModuleGate moduleId="core.reporting"><Dashboard /></ModuleGate>} />
        <Route path="clients" element={<ModuleGate moduleId="core.clients"><Clients /></ModuleGate>} />
        <Route path="projects" element={<ModuleGate moduleId="core.projects"><Projects /></ModuleGate>} />
        <Route path="time" element={<ModuleGate moduleId="core.time_tracking"><TimeTracking /></ModuleGate>} />
        <Route path="quotes" element={<ModuleGate moduleId="sales.quotes"><Quotes /></ModuleGate>} />
        <Route path="invoices" element={<ModuleGate moduleId="billing.invoices"><Invoices /></ModuleGate>} />
        <Route path="invoices/:id" element={<ModuleGate moduleId="billing.invoices"><InvoiceDetail /></ModuleGate>} />
        <Route path="expenses" element={<ModuleGate moduleId="expenses.receipts"><Expenses /></ModuleGate>} />
        <Route path="settings" element={<ModuleGate moduleId="core.platform"><Settings /></ModuleGate>} />
        <Route path="admin/modules" element={<AdminModules />} />
      </Route>
    </Routes>
  );
}
