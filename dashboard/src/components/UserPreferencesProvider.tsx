'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

export interface UserPreferences {
  // Dashboard preferences
  dashboard: {
    autoRefresh: boolean;
    refreshInterval: number; // in seconds
    theme: 'light' | 'dark' | 'system';
    compactMode: boolean;
    showAnimations: boolean;
    defaultLayout: string;
  };

  // Notification preferences
  notifications: {
    desktop: boolean;
    sound: boolean;
    email: boolean;
    alertTypes: {
      high: boolean;
      medium: boolean;
      low: boolean;
    };
  };

  // Data display preferences
  display: {
    dateFormat: 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD';
    timeFormat: '12h' | '24h';
    numberFormat: 'standard' | 'compact';
    chartType: 'line' | 'area' | 'bar';
    showGrid: boolean;
    showLegend: boolean;
  };

  // Privacy preferences
  privacy: {
    analytics: boolean;
    crashReports: boolean;
    dataRetention: number; // days
  };

  // Accessibility preferences
  accessibility: {
    highContrast: boolean;
    reducedMotion: boolean;
    largeText: boolean;
  };
}

const defaultPreferences: UserPreferences = {
  dashboard: {
    autoRefresh: true,
    refreshInterval: 60,
    theme: 'system',
    compactMode: false,
    showAnimations: true,
    defaultLayout: 'default',
  },
  notifications: {
    desktop: true,
    sound: true,
    email: false,
    alertTypes: {
      high: true,
      medium: true,
      low: false,
    },
  },
  display: {
    dateFormat: 'MM/DD/YYYY',
    timeFormat: '12h',
    numberFormat: 'standard',
    chartType: 'area',
    showGrid: true,
    showLegend: true,
  },
  privacy: {
    analytics: true,
    crashReports: true,
    dataRetention: 90,
  },
  accessibility: {
    highContrast: false,
    reducedMotion: false,
    largeText: false,
  },
};

interface UserPreferencesContextType {
  preferences: UserPreferences;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  updateDashboardPrefs: (updates: Partial<UserPreferences['dashboard']>) => void;
  updateNotificationPrefs: (updates: Partial<UserPreferences['notifications']>) => void;
  updateDisplayPrefs: (updates: Partial<UserPreferences['display']>) => void;
  updatePrivacyPrefs: (updates: Partial<UserPreferences['privacy']>) => void;
  updateAccessibilityPrefs: (updates: Partial<UserPreferences['accessibility']>) => void;
  resetPreferences: () => void;
}

const UserPreferencesContext = createContext<UserPreferencesContextType | undefined>(undefined);

export function useUserPreferences() {
  const context = useContext(UserPreferencesContext);
  if (context === undefined) {
    throw new Error('useUserPreferences must be used within a UserPreferencesProvider');
  }
  return context;
}

interface UserPreferencesProviderProps {
  children: React.ReactNode;
  storageKey?: string;
}

export function UserPreferencesProvider({
  children,
  storageKey = 'vanguard-preferences',
}: UserPreferencesProviderProps) {
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load preferences from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        setPreferences({ ...defaultPreferences, ...parsed });
      }
    } catch (error) {
      console.warn('Failed to load user preferences:', error);
    } finally {
      setIsLoaded(true);
    }
  }, [storageKey]);

  // Save preferences to localStorage
  const savePreferences = useCallback((newPreferences: UserPreferences) => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(newPreferences));
    } catch (error) {
      console.warn('Failed to save user preferences:', error);
    }
  }, [storageKey]);

  const updatePreferences = useCallback((updates: Partial<UserPreferences>) => {
    setPreferences(current => {
      const newPreferences = { ...current, ...updates };
      savePreferences(newPreferences);
      return newPreferences;
    });
  }, [savePreferences]);

  const updateDashboardPrefs = useCallback((updates: Partial<UserPreferences['dashboard']>) => {
    setPreferences(current => {
      const newPrefs = {
        ...current,
        dashboard: { ...current.dashboard, ...updates }
      };
      savePreferences(newPrefs);
      return newPrefs;
    });
  }, [savePreferences]);

  const updateNotificationPrefs = useCallback((updates: Partial<UserPreferences['notifications']>) => {
    setPreferences(current => {
      const newPrefs = {
        ...current,
        notifications: { ...current.notifications, ...updates }
      };
      savePreferences(newPrefs);
      return newPrefs;
    });
  }, [savePreferences]);

  const updateDisplayPrefs = useCallback((updates: Partial<UserPreferences['display']>) => {
    setPreferences(current => {
      const newPrefs = {
        ...current,
        display: { ...current.display, ...updates }
      };
      savePreferences(newPrefs);
      return newPrefs;
    });
  }, [savePreferences]);

  const updatePrivacyPrefs = useCallback((updates: Partial<UserPreferences['privacy']>) => {
    setPreferences(current => {
      const newPrefs = {
        ...current,
        privacy: { ...current.privacy, ...updates }
      };
      savePreferences(newPrefs);
      return newPrefs;
    });
  }, [savePreferences]);

  const updateAccessibilityPrefs = useCallback((updates: Partial<UserPreferences['accessibility']>) => {
    setPreferences(current => {
      const newPrefs = {
        ...current,
        accessibility: { ...current.accessibility, ...updates }
      };
      savePreferences(newPrefs);
      return newPrefs;
    });
  }, [savePreferences]);

  const resetPreferences = useCallback(() => {
    setPreferences(defaultPreferences);
    savePreferences(defaultPreferences);
  }, [savePreferences]);

  // Apply theme preference
  useEffect(() => {
    if (!isLoaded) return;

    const root = document.documentElement;
    const theme = preferences.dashboard.theme;

    if (theme === 'dark') {
      root.classList.add('dark');
    } else if (theme === 'light') {
      root.classList.remove('dark');
    } else {
      // System preference
      const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (systemDark) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    }
  }, [preferences.dashboard.theme, isLoaded]);

  // Apply accessibility preferences
  useEffect(() => {
    if (!isLoaded) return;

    const root = document.documentElement;

    if (preferences.accessibility.highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }

    if (preferences.accessibility.reducedMotion) {
      root.classList.add('reduced-motion');
    } else {
      root.classList.remove('reduced-motion');
    }

    if (preferences.accessibility.largeText) {
      root.classList.add('large-text');
    } else {
      root.classList.remove('large-text');
    }
  }, [preferences.accessibility, isLoaded]);

  const value = {
    preferences,
    updatePreferences,
    updateDashboardPrefs,
    updateNotificationPrefs,
    updateDisplayPrefs,
    updatePrivacyPrefs,
    updateAccessibilityPrefs,
    resetPreferences,
  };

  // Don't render children until preferences are loaded to prevent hydration mismatches
  if (!isLoaded) {
    return null;
  }

  return (
    <UserPreferencesContext.Provider value={value}>
      {children}
    </UserPreferencesContext.Provider>
  );
}