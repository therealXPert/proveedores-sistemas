"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, EconomicGroup } from "./api";

type GroupContextValue = {
  groups: EconomicGroup[];
  activeGroupId: number | null; // null = "Todos los grupos"
  setActiveGroupId: (id: number | null) => void;
  reloadGroups: () => Promise<void>;
  loading: boolean;
};

const GroupContext = createContext<GroupContextValue | null>(null);
const STORAGE_KEY = "active_economic_group_id";

export function GroupProvider({ children }: { children: ReactNode }) {
  const [groups, setGroups] = useState<EconomicGroup[]>([]);
  const [activeGroupId, setActiveGroupIdState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  async function reloadGroups() {
    try {
      const data = await api.listEconomicGroups();
      setGroups(data);
    } catch {
      setGroups([]);
    }
  }

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) setActiveGroupIdState(Number(stored));
    reloadGroups().finally(() => setLoading(false));
  }, []);

  function setActiveGroupId(id: number | null) {
    setActiveGroupIdState(id);
    if (id === null) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, String(id));
    }
  }

  return (
    <GroupContext.Provider value={{ groups, activeGroupId, setActiveGroupId, reloadGroups, loading }}>
      {children}
    </GroupContext.Provider>
  );
}

export function useGroup() {
  const ctx = useContext(GroupContext);
  if (!ctx) throw new Error("useGroup debe usarse dentro de <GroupProvider>");
  return ctx;
}
