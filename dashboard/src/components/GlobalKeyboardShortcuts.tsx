'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useShortcut, useKeyboardShortcuts } from './KeyboardShortcutsProvider';
import { KeyboardShortcutsHelp } from './KeyboardShortcutsHelp';
import { useSettings } from './SettingsProvider';
import { useMobileMenu } from './MobileMenuProvider';

export function GlobalKeyboardShortcuts() {
  const router = useRouter();
  const [showHelp, setShowHelp] = useState(false);
  const { toggle: toggleMobileMenu } = useMobileMenu();
  const { openSettings } = useSettings();

  // Navigation shortcuts
  useShortcut('nav-dashboard', {
    key: 'd',
    ctrlKey: true,
    description: 'Go to Dashboard',
    category: 'Navigation'
  }, () => router.push('/dashboard'));

  useShortcut('nav-settings', {
    key: ',',
    ctrlKey: true,
    description: 'Open Settings',
    category: 'Navigation'
  }, () => openSettings());

  useShortcut('nav-guides', {
    key: 'g',
    ctrlKey: true,
    description: 'Go to Guides',
    category: 'Navigation'
  }, () => router.push('/guides/how-it-works'));

  // Action shortcuts
  useShortcut('refresh-data', {
    key: 'r',
    ctrlKey: true,
    description: 'Refresh page',
    category: 'Actions'
  }, () => window.location.reload());

  useShortcut('toggle-mobile-menu', {
    key: 'm',
    ctrlKey: true,
    description: 'Toggle mobile menu',
    category: 'Navigation'
  }, () => toggleMobileMenu());

  useShortcut('toggle-theme', {
    key: 't',
    ctrlKey: true,
    shiftKey: true,
    description: 'Toggle theme',
    category: 'Appearance'
  }, () => {
    // This will be handled by the theme toggle logic
    const event = new KeyboardEvent('keydown', {
      key: 't',
      ctrlKey: true,
      shiftKey: true
    });
    document.dispatchEvent(event);
  });

  // Show keyboard shortcuts help
  useShortcut('show-help', {
    key: '?',
    description: 'Show keyboard shortcuts help',
    category: 'Help'
  }, () => setShowHelp(true));

  // Close help dialog with Escape
  useShortcut('close-dialog', {
    key: 'Escape',
    description: 'Close dialogs',
    category: 'General'
  }, () => setShowHelp(false));

  return (
    <>
      {showHelp && (
        <KeyboardShortcutsHelp onClose={() => setShowHelp(false)} />
      )}
    </>
  );
}