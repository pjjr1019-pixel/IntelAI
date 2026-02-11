'use client';

import React, { createContext, useContext, useState } from 'react';

interface MobileMenuContextType {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  toggle: () => void;
}

const MobileMenuContext = createContext<MobileMenuContextType | undefined>(undefined);

export function useMobileMenu() {
  const context = useContext(MobileMenuContext);
  if (context === undefined) {
    throw new Error('useMobileMenu must be used within a MobileMenuProvider');
  }
  return context;
}

interface MobileMenuProviderProps {
  children: React.ReactNode;
}

export function MobileMenuProvider({ children }: MobileMenuProviderProps) {
  const [isOpen, setIsOpen] = useState(false);

  const toggle = () => setIsOpen(!isOpen);

  return (
    <MobileMenuContext.Provider value={{ isOpen, setIsOpen, toggle }}>
      {children}
    </MobileMenuContext.Provider>
  );
}