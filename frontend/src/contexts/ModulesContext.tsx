import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

import { api } from "../api";
import { ModuleStatus } from "../types";

interface ModulesContextValue {
  modules: ModuleStatus[];
  loading: boolean;
  refresh: () => Promise<void>;
  isEnabled: (moduleId: string) => boolean;
}

const ModulesContext = createContext<ModulesContextValue | null>(null);

export function ModulesProvider({ children }: { children: ReactNode }) {
  const [modules, setModules] = useState<ModuleStatus[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const result = await api.get<ModuleStatus[]>("/admin/modules");
    setModules(result);
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  const value = useMemo<ModulesContextValue>(
    () => ({
      modules,
      loading,
      refresh,
      isEnabled: (moduleId: string) =>
        modules.some(
          (item) => item.manifest.id === moduleId && item.state === "enabled"
        ),
    }),
    [modules, loading]
  );

  return <ModulesContext.Provider value={value}>{children}</ModulesContext.Provider>;
}

export function useModules() {
  const context = useContext(ModulesContext);
  if (!context) throw new Error("useModules must be used within ModulesProvider");
  return context;
}
