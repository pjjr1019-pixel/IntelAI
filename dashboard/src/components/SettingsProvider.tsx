'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { SettingsModal } from './SettingsModal';

interface SettingsContextType {
  openSettings: () => void;
  closeSettings: () => void;
  isSettingsOpen: boolean;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}

interface SettingsProviderProps {
  children: ReactNode;
}

export function SettingsProvider({ children }: SettingsProviderProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const openSettings = () => setIsSettingsOpen(true);
  const closeSettings = () => setIsSettingsOpen(false);

  return (
    <SettingsContext.Provider value={{ openSettings, closeSettings, isSettingsOpen }}>
      {children}
      <SettingsModal isOpen={isSettingsOpen} onClose={closeSettings} />
    </SettingsContext.Provider>
  );
}