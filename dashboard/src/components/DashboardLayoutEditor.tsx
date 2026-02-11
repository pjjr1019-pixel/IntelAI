'use client';

import React from 'react';
import { Edit3, Save, RotateCcw, Plus, Settings } from 'lucide-react';
import { useDashboardLayout } from './DashboardLayoutProvider';

interface DashboardLayoutEditorProps {
  onAddWidget?: () => void;
  onSettings?: () => void;
}

export function DashboardLayoutEditor({ onAddWidget, onSettings }: DashboardLayoutEditorProps) {
  const {
    isEditMode,
    setIsEditMode,
    saveLayout,
    resetLayout,
    currentLayout
  } = useDashboardLayout();

  const handleSave = () => {
    saveLayout(`${currentLayout.name} (Modified)`);
    setIsEditMode(false);
  };

  const handleReset = () => {
    resetLayout();
    setIsEditMode(false);
  };

  if (!isEditMode) {
    return (
      <div className="flex items-center gap-2">
        <button
          onClick={() => setIsEditMode(true)}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface-2 hover:bg-surface-3 rounded-lg transition-colors"
          title="Edit dashboard layout"
        >
          <Edit3 className="w-4 h-4" />
          Edit Layout
        </button>
        <button
          onClick={onSettings}
          className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-surface-2 transition-colors"
          title="Dashboard settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 bg-vanguard-600/10 border border-vanguard-600/20 rounded-lg p-2">
      <div className="flex items-center gap-1 text-sm text-vanguard-400 font-medium">
        <Edit3 className="w-4 h-4" />
        Edit Mode
      </div>

      <div className="flex items-center gap-1 ml-4">
        <button
          onClick={onAddWidget}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-surface-2 hover:bg-surface-3 rounded transition-colors"
          title="Add new widget"
        >
          <Plus className="w-3 h-3" />
          Add Widget
        </button>

        <button
          onClick={handleSave}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-green-600/20 hover:bg-green-600/30 text-green-400 rounded transition-colors"
          title="Save layout changes"
        >
          <Save className="w-3 h-3" />
          Save
        </button>

        <button
          onClick={handleReset}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-orange-600/20 hover:bg-orange-600/30 text-orange-400 rounded transition-colors"
          title="Reset to default layout"
        >
          <RotateCcw className="w-3 h-3" />
          Reset
        </button>

        <button
          onClick={() => setIsEditMode(false)}
          className="px-2 py-1 text-xs bg-surface-2 hover:bg-surface-3 rounded transition-colors"
          title="Exit edit mode"
        >
          Done
        </button>
      </div>
    </div>
  );
}