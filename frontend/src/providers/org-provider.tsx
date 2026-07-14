'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

const KEY = 'aiads.org_id';

interface OrgSelection {
  selectedOrgId: string | null;
  setSelectedOrgId: (id: string) => void;
}

const OrgContext = createContext<OrgSelection | null>(null);

export function OrgProvider({ children }: { children: ReactNode }) {
  const [selectedOrgId, setId] = useState<string | null>(null);

  useEffect(() => {
    setId(typeof window !== 'undefined' ? localStorage.getItem(KEY) : null);
  }, []);

  const setSelectedOrgId = (id: string) => {
    if (typeof window !== 'undefined') localStorage.setItem(KEY, id);
    setId(id);
  };

  return (
    <OrgContext.Provider value={{ selectedOrgId, setSelectedOrgId }}>
      {children}
    </OrgContext.Provider>
  );
}

export function useOrgSelection(): OrgSelection {
  const ctx = useContext(OrgContext);
  if (!ctx) throw new Error('useOrgSelection must be used within OrgProvider');
  return ctx;
}
