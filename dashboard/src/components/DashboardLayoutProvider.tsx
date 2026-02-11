'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';

export interface DashboardWidget {
  id: string;
  type: 'chart' | 'metric' | 'table' | 'heatmap' | 'alerts';
  title: string;
  position: { x: number; y: number; w: number; h: number };
  config?: Record<string, any>;
  visible: boolean;
}

export interface DashboardLayout {
  id: string;
  name: string;
  widgets: DashboardWidget[];
  isDefault?: boolean;
}

interface DashboardLayoutContextType {
  currentLayout: DashboardLayout;
  availableLayouts: DashboardLayout[];
  isEditMode: boolean;
  setIsEditMode: (edit: boolean) => void;
  updateWidget: (widgetId: string, updates: Partial<DashboardWidget>) => void;
  addWidget: (widget: Omit<DashboardWidget, 'id'>) => void;
  removeWidget: (widgetId: string) => void;
  saveLayout: (name: string) => void;
  loadLayout: (layoutId: string) => void;
  deleteLayout: (layoutId: string) => void;
  resetLayout: () => void;
}

const DashboardLayoutContext = createContext<DashboardLayoutContextType | undefined>(undefined);

export function useDashboardLayout() {
  const context = useContext(DashboardLayoutContext);
  if (context === undefined) {
    throw new Error('useDashboardLayout must be used within a DashboardLayoutProvider');
  }
  return context;
}

const defaultWidgets: DashboardWidget[] = [
  {
    id: 'total-signals',
    type: 'metric',
    title: 'Total Signals',
    position: { x: 0, y: 0, w: 3, h: 2 },
    visible: true,
  },
  {
    id: 'recent-activity',
    type: 'metric',
    title: 'Recent Activity',
    position: { x: 3, y: 0, w: 3, h: 2 },
    visible: true,
  },
  {
    id: 'trending-down',
    type: 'metric',
    title: 'Trending Down',
    position: { x: 6, y: 0, w: 3, h: 2 },
    visible: true,
  },
  {
    id: 'active-alerts',
    type: 'metric',
    title: 'Active Alerts',
    position: { x: 9, y: 0, w: 3, h: 2 },
    visible: true,
  },
  {
    id: 'google-trends',
    type: 'chart',
    title: 'Google Trends',
    position: { x: 0, y: 2, w: 12, h: 6 },
    visible: true,
  },
];

const dashboardTemplates: DashboardLayout[] = [
  {
    id: 'template-analytics',
    name: 'Analytics Dashboard',
    widgets: [
      {
        id: 'total-signals',
        type: 'metric',
        title: 'Total Signals',
        position: { x: 0, y: 0, w: 3, h: 2 },
        visible: true,
      },
      {
        id: 'recent-activity',
        type: 'metric',
        title: 'Recent Activity',
        position: { x: 3, y: 0, w: 3, h: 2 },
        visible: true,
      },
      {
        id: 'active-alerts',
        type: 'metric',
        title: 'Active Alerts',
        position: { x: 6, y: 0, w: 3, h: 2 },
        visible: true,
      },
      {
        id: 'google-trends',
        type: 'chart',
        title: 'Google Trends',
        position: { x: 0, y: 2, w: 9, h: 4 },
        visible: true,
      },
      {
        id: 'trending-down',
        type: 'metric',
        title: 'Trending Down',
        position: { x: 9, y: 0, w: 3, h: 6 },
        visible: true,
      },
    ],
    isDefault: false,
  },
  {
    id: 'template-monitoring',
    name: 'Monitoring Dashboard',
    widgets: [
      {
        id: 'active-alerts',
        type: 'metric',
        title: 'Active Alerts',
        position: { x: 0, y: 0, w: 4, h: 2 },
        visible: true,
      },
      {
        id: 'total-signals',
        type: 'metric',
        title: 'Total Signals',
        position: { x: 4, y: 0, w: 4, h: 2 },
        visible: true,
      },
      {
        id: 'recent-activity',
        type: 'metric',
        title: 'Recent Activity',
        position: { x: 8, y: 0, w: 4, h: 2 },
        visible: true,
      },
      {
        id: 'google-trends',
        type: 'chart',
        title: 'Google Trends',
        position: { x: 0, y: 2, w: 12, h: 4 },
        visible: true,
      },
    ],
    isDefault: false,
  },
  {
    id: 'template-executive',
    name: 'Executive Summary',
    widgets: [
      {
        id: 'total-signals',
        type: 'metric',
        title: 'Total Signals',
        position: { x: 0, y: 0, w: 6, h: 2 },
        visible: true,
      },
      {
        id: 'active-alerts',
        type: 'metric',
        title: 'Active Alerts',
        position: { x: 6, y: 0, w: 6, h: 2 },
        visible: true,
      },
      {
        id: 'google-trends',
        type: 'chart',
        title: 'Google Trends',
        position: { x: 0, y: 2, w: 12, h: 4 },
        visible: true,
      },
    ],
    isDefault: false,
  },
];

const defaultLayout: DashboardLayout = {
  id: 'default',
  name: 'Default Layout',
  widgets: defaultWidgets,
  isDefault: true,
};

interface DashboardLayoutProviderProps {
  children: React.ReactNode;
  storageKey?: string;
}

export function DashboardLayoutProvider({
  children,
  storageKey = 'vanguard-dashboard-layout',
}: DashboardLayoutProviderProps) {
  const [currentLayout, setCurrentLayout] = useState<DashboardLayout>(defaultLayout);
  const [availableLayouts, setAvailableLayouts] = useState<DashboardLayout[]>([defaultLayout, ...dashboardTemplates]);
  const [isEditMode, setIsEditMode] = useState(false);

  // Load saved layouts from localStorage
  React.useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const layouts = JSON.parse(stored);
        setAvailableLayouts(layouts);

        // Load the last used layout or default
        const lastLayoutId = localStorage.getItem(`${storageKey}-current`);
        const lastLayout = layouts.find((l: DashboardLayout) => l.id === lastLayoutId);
        if (lastLayout) {
          setCurrentLayout(lastLayout);
        }
      }
    } catch (error) {
      console.warn('Failed to load dashboard layouts:', error);
    }
  }, [storageKey]);

  const saveLayoutsToStorage = useCallback((layouts: DashboardLayout[]) => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(layouts));
    } catch (error) {
      console.warn('Failed to save dashboard layouts:', error);
    }
  }, [storageKey]);

  const updateWidget = useCallback((widgetId: string, updates: Partial<DashboardWidget>) => {
    setCurrentLayout(current => ({
      ...current,
      widgets: current.widgets.map(widget =>
        widget.id === widgetId ? { ...widget, ...updates } : widget
      ),
    }));
  }, []);

  const addWidget = useCallback((widget: Omit<DashboardWidget, 'id'>) => {
    const newWidget: DashboardWidget = {
      ...widget,
      id: `widget-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    };

    setCurrentLayout(current => ({
      ...current,
      widgets: [...current.widgets, newWidget],
    }));
  }, []);

  const removeWidget = useCallback((widgetId: string) => {
    setCurrentLayout(current => ({
      ...current,
      widgets: current.widgets.filter(widget => widget.id !== widgetId),
    }));
  }, []);

  const saveLayout = useCallback((name: string) => {
    const newLayout: DashboardLayout = {
      ...currentLayout,
      id: `layout-${Date.now()}`,
      name,
      isDefault: false,
    };

    setAvailableLayouts(current => {
      const updated = [...current, newLayout];
      saveLayoutsToStorage(updated);
      return updated;
    });
  }, [currentLayout, saveLayoutsToStorage]);

  const loadLayout = useCallback((layoutId: string) => {
    const layout = availableLayouts.find(l => l.id === layoutId);
    if (layout) {
      setCurrentLayout(layout);
      localStorage.setItem(`${storageKey}-current`, layoutId);
    }
  }, [availableLayouts, storageKey]);

  const deleteLayout = useCallback((layoutId: string) => {
    const layout = availableLayouts.find(l => l.id === layoutId);
    if (!layout || layout.isDefault) return; // Don't delete default layouts

    setAvailableLayouts(current => {
      const updated = current.filter(l => l.id !== layoutId);
      saveLayoutsToStorage(updated);
      return updated;
    });

    // If we're deleting the current layout, switch to default
    if (currentLayout.id === layoutId) {
      setCurrentLayout(defaultLayout);
      localStorage.removeItem(`${storageKey}-current`);
    }
  }, [availableLayouts, currentLayout.id, defaultLayout, saveLayoutsToStorage, storageKey]);

  const resetLayout = useCallback(() => {
    setCurrentLayout(defaultLayout);
    localStorage.removeItem(`${storageKey}-current`);
  }, []);

  const value = {
    currentLayout,
    availableLayouts,
    isEditMode,
    setIsEditMode,
    updateWidget,
    addWidget,
    removeWidget,
    saveLayout,
    loadLayout,
    deleteLayout,
    resetLayout,
  };

  return (
    <DashboardLayoutContext.Provider value={value}>
      {children}
    </DashboardLayoutContext.Provider>
  );
}