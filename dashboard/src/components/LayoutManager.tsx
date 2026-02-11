'use client';

import React, { useState } from 'react';
import { ChevronDown, FolderOpen, Save, Trash2, Edit3, Copy, Download, Upload } from 'lucide-react';
import { useDashboardLayout } from './DashboardLayoutProvider';
import { DashboardLayout } from './DashboardLayoutProvider';

interface LayoutManagerProps {
  className?: string;
}

export function LayoutManager({ className = '' }: LayoutManagerProps) {
  const {
    currentLayout,
    availableLayouts,
    loadLayout,
    saveLayout,
    deleteLayout,
    resetLayout
  } = useDashboardLayout();

  const [isOpen, setIsOpen] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [showManageDialog, setShowManageDialog] = useState(false);

  const handleLoadLayout = (layout: DashboardLayout) => {
    loadLayout(layout.id);
    setIsOpen(false);
  };

  const handleSaveCurrent = () => {
    if (saveName.trim()) {
      saveLayout(saveName.trim());
      setSaveName('');
      setShowSaveDialog(false);
      setIsOpen(false);
    }
  };

  const handleExportLayout = () => {
    const layoutData = JSON.stringify(currentLayout, null, 2);
    const blob = new Blob([layoutData], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentLayout.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_layout.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleImportLayout = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const layoutData = JSON.parse(e.target?.result as string);
        // Validate layout structure
        if (layoutData.id && layoutData.name && layoutData.widgets) {
          const importedLayout: DashboardLayout = {
            ...layoutData,
            id: `imported-${Date.now()}`,
            name: `${layoutData.name} (Imported)`,
            isDefault: false,
          };
          saveLayout(importedLayout.name);
          loadLayout(importedLayout.id);
        }
      } catch (error) {
        console.error('Failed to import layout:', error);
        alert('Invalid layout file format');
      }
    };
    reader.readAsText(file);
    event.target.value = '';
  };

  const copyLayoutToClipboard = () => {
    const layoutData = JSON.stringify(currentLayout, null, 2);
    navigator.clipboard.writeText(layoutData).then(() => {
      alert('Layout configuration copied to clipboard!');
    });
  };

  return (
    <div className={`relative ${className}`}>
      {/* Main Dropdown Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface-2 hover:bg-surface-3 rounded-lg transition-colors"
        title="Manage dashboard layouts"
      >
        <FolderOpen className="w-4 h-4" />
        Layouts
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-surface-1 border border-white/[0.06] rounded-lg shadow-xl z-50">
          <div className="p-2">
            {/* Current Layout */}
            <div className="px-3 py-2 text-xs text-muted-foreground border-b border-white/[0.06] mb-2">
              Current: <span className="text-foreground font-medium">{currentLayout.name}</span>
            </div>

            {/* Saved Layouts */}
            <div className="space-y-1 mb-3">
              <div className="px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Your Layouts
              </div>
              {availableLayouts.filter(l => !l.isDefault && !l.id.startsWith('template-')).length > 0 ? (
                availableLayouts
                  .filter(l => !l.isDefault && !l.id.startsWith('template-'))
                  .map((layout) => (
                    <button
                      key={layout.id}
                      onClick={() => handleLoadLayout(layout)}
                      className={`w-full text-left px-3 py-2 text-sm rounded hover:bg-surface-2 transition-colors ${
                        layout.id === currentLayout.id ? 'bg-vanguard-600/20 text-vanguard-400' : ''
                      }`}
                    >
                      {layout.name}
                    </button>
                  ))
              ) : (
                <div className="px-3 py-2 text-sm text-muted-foreground italic">
                  No saved layouts
                </div>
              )}
            </div>

            {/* Templates */}
            <div className="space-y-1 mb-3">
              <div className="px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Templates
              </div>
              {availableLayouts.filter(l => l.id.startsWith('template-')).map((layout) => (
                <button
                  key={layout.id}
                  onClick={() => handleLoadLayout(layout)}
                  className={`w-full text-left px-3 py-2 text-sm rounded hover:bg-surface-2 transition-colors ${
                    layout.id === currentLayout.id ? 'bg-vanguard-600/20 text-vanguard-400' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span>{layout.name}</span>
                    <span className="text-xs text-muted-foreground bg-surface-3 px-1.5 py-0.5 rounded">
                      Template
                    </span>
                  </div>
                </button>
              ))}
            </div>

            {/* Actions */}
            <div className="border-t border-white/[0.06] pt-2 space-y-1">
              <button
                onClick={() => {
                  setShowSaveDialog(true);
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded hover:bg-surface-2 transition-colors"
              >
                <Save className="w-4 h-4" />
                Save Current Layout
              </button>

              <button
                onClick={() => {
                  setShowManageDialog(true);
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded hover:bg-surface-2 transition-colors"
              >
                <Edit3 className="w-4 h-4" />
                Manage Layouts
              </button>

              <div className="border-t border-white/[0.06] my-2"></div>

              <button
                onClick={copyLayoutToClipboard}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded hover:bg-surface-2 transition-colors"
              >
                <Copy className="w-4 h-4" />
                Copy Layout JSON
              </button>

              <button
                onClick={handleExportLayout}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded hover:bg-surface-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                Export Layout
              </button>

              <label className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded hover:bg-surface-2 transition-colors cursor-pointer">
                <Upload className="w-4 h-4" />
                Import Layout
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImportLayout}
                  className="hidden"
                />
              </label>

              <button
                onClick={() => {
                  resetLayout();
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded hover:bg-red-500/20 text-red-400 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Reset to Default
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-1 border border-white/[0.06] rounded-lg p-6 w-96 max-w-[90vw]">
            <h3 className="text-lg font-semibold mb-4">Save Layout</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Layout Name</label>
                <input
                  type="text"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  placeholder="Enter layout name..."
                  className="w-full px-3 py-2 bg-surface-2 border border-white/[0.06] rounded focus:border-vanguard-400 focus:outline-none"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveCurrent();
                    if (e.key === 'Escape') setShowSaveDialog(false);
                  }}
                  autoFocus
                />
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowSaveDialog(false)}
                  className="px-4 py-2 text-sm bg-surface-2 hover:bg-surface-3 rounded transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveCurrent}
                  disabled={!saveName.trim()}
                  className="px-4 py-2 text-sm bg-vanguard-600 hover:bg-vanguard-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
                >
                  Save Layout
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Manage Dialog */}
      {showManageDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-1 border border-white/[0.06] rounded-lg p-6 w-[600px] max-w-[90vw] max-h-[80vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4">Manage Layouts</h3>
            <div className="space-y-3">
              {/* User Layouts */}
              {availableLayouts
                .filter(l => !l.isDefault && !l.id.startsWith('template-'))
                .map((layout) => (
                  <div
                    key={layout.id}
                    className={`flex items-center justify-between p-3 rounded border ${
                      layout.id === currentLayout.id
                        ? 'border-vanguard-400 bg-vanguard-600/10'
                        : 'border-white/[0.06] bg-surface-2'
                    }`}
                  >
                    <div className="flex-1">
                      <div className="font-medium">{layout.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {layout.widgets.length} widgets • Custom
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          loadLayout(layout.id);
                          setShowManageDialog(false);
                        }}
                        className="px-3 py-1 text-xs bg-vanguard-600 hover:bg-vanguard-700 text-white rounded transition-colors"
                      >
                        Load
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Are you sure you want to delete "${layout.name}"?`)) {
                            deleteLayout(layout.id);
                          }
                        }}
                        className="px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}

              {/* Templates */}
              {availableLayouts
                .filter(l => l.id.startsWith('template-'))
                .map((layout) => (
                  <div
                    key={layout.id}
                    className={`flex items-center justify-between p-3 rounded border ${
                      layout.id === currentLayout.id
                        ? 'border-vanguard-400 bg-vanguard-600/10'
                        : 'border-white/[0.06] bg-surface-2'
                    }`}
                  >
                    <div className="flex-1">
                      <div className="font-medium">{layout.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {layout.widgets.length} widgets • Template
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          loadLayout(layout.id);
                          setShowManageDialog(false);
                        }}
                        className="px-3 py-1 text-xs bg-vanguard-600 hover:bg-vanguard-700 text-white rounded transition-colors"
                      >
                        Load
                      </button>
                    </div>
                  </div>
                ))}
            </div>
            <div className="flex justify-end mt-6">
              <button
                onClick={() => setShowManageDialog(false)}
                className="px-4 py-2 text-sm bg-surface-2 hover:bg-surface-3 rounded transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}