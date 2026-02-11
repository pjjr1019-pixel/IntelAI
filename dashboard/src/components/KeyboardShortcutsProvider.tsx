'use client';

import { createContext, useContext, useEffect, useCallback } from 'react';

interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
  metaKey?: boolean;
  action: () => void;
  description: string;
  category?: string;
}

interface KeyboardShortcutsContextType {
  registerShortcut: (id: string, shortcut: KeyboardShortcut) => void;
  unregisterShortcut: (id: string) => void;
  getShortcuts: () => Record<string, KeyboardShortcut>;
}

const KeyboardShortcutsContext = createContext<KeyboardShortcutsContextType | undefined>(undefined);

export function useKeyboardShortcuts() {
  const context = useContext(KeyboardShortcutsContext);
  if (context === undefined) {
    throw new Error('useKeyboardShortcuts must be used within a KeyboardShortcutsProvider');
  }
  return context;
}

interface KeyboardShortcutsProviderProps {
  children: React.ReactNode;
}

export function KeyboardShortcutsProvider({ children }: KeyboardShortcutsProviderProps) {
  const shortcuts = new Map<string, KeyboardShortcut>();

  const registerShortcut = useCallback((id: string, shortcut: KeyboardShortcut) => {
    shortcuts.set(id, shortcut);
  }, []);

  const unregisterShortcut = useCallback((id: string) => {
    shortcuts.delete(id);
  }, []);

  const getShortcuts = useCallback(() => {
    return Object.fromEntries(shortcuts);
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement ||
        (event.target as HTMLElement)?.contentEditable === 'true'
      ) {
        return;
      }

      for (const [id, shortcut] of shortcuts) {
        const matches =
          event.key.toLowerCase() === shortcut.key.toLowerCase() &&
          !!event.ctrlKey === !!shortcut.ctrlKey &&
          !!event.altKey === !!shortcut.altKey &&
          !!event.shiftKey === !!shortcut.shiftKey &&
          !!event.metaKey === !!shortcut.metaKey;

        if (matches) {
          event.preventDefault();
          event.stopPropagation();
          shortcut.action();
          break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);

  const value = {
    registerShortcut,
    unregisterShortcut,
    getShortcuts,
  };

  return (
    <KeyboardShortcutsContext.Provider value={value}>
      {children}
    </KeyboardShortcutsContext.Provider>
  );
}

// Hook for registering shortcuts in components
export function useShortcut(
  id: string,
  shortcut: Omit<KeyboardShortcut, 'action'>,
  action: () => void,
  deps: React.DependencyList = []
) {
  const { registerShortcut, unregisterShortcut } = useKeyboardShortcuts();

  useEffect(() => {
    registerShortcut(id, { ...shortcut, action });
    return () => unregisterShortcut(id);
  }, [id, shortcut, action, registerShortcut, unregisterShortcut, ...deps]);
}