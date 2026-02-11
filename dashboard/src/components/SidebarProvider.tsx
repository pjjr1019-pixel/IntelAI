'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

interface SidebarContextType {
  isSidebarVisible: boolean;
  setIsSidebarVisible: (visible: boolean) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isSidebarVisible, setIsSidebarVisible] = useState(false);

  return (
    <SidebarContext.Provider value={{ isSidebarVisible, setIsSidebarVisible }}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (context === undefined) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
}