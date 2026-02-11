'use client';

import React from 'react';
import { Keyboard, X } from 'lucide-react';
import { useKeyboardShortcuts } from './KeyboardShortcutsProvider';

interface KeyboardShortcutsHelpProps {
  onClose: () => void;
}

export function KeyboardShortcutsHelp({ onClose }: KeyboardShortcutsHelpProps) {
  const { getShortcuts } = useKeyboardShortcuts();

  const shortcuts = getShortcuts();
  const categories = Object.values(shortcuts).reduce((acc, shortcut) => {
    const category = shortcut.category || 'General';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(shortcut);
    return acc;
  }, {} as Record<string, typeof shortcuts[keyof typeof shortcuts][]>);

  const formatKey = (shortcut: typeof shortcuts[keyof typeof shortcuts]) => {
    const parts = [];
    if (shortcut.ctrlKey) parts.push('Ctrl');
    if (shortcut.altKey) parts.push('Alt');
    if (shortcut.shiftKey) parts.push('Shift');
    if (shortcut.metaKey) parts.push('Cmd');
    parts.push(shortcut.key.toUpperCase());
    return parts.join(' + ');
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Keyboard className="h-5 w-5" />
            Keyboard Shortcuts
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-accent rounded-md transition-colors"
            aria-label="Close shortcuts help"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(80vh-120px)]">
          {Object.entries(categories).map(([category, categoryShortcuts]) => (
            <div key={category} className="mb-6 last:mb-0">
              <h3 className="text-lg font-medium mb-3 text-muted-foreground">{category}</h3>
              <div className="space-y-2">
                {categoryShortcuts.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2 px-3 rounded-md bg-muted/50"
                  >
                    <span className="text-sm">{shortcut.description}</span>
                    <kbd className="px-2 py-1 bg-background border border-border rounded text-xs font-mono">
                      {formatKey(shortcut)}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="mt-6 pt-4 border-t border-border">
            <p className="text-sm text-muted-foreground">
              Press <kbd className="px-1 py-0.5 bg-background border border-border rounded text-xs">?</kbd> to toggle this help dialog.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}