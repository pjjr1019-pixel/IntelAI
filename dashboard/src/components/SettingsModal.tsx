'use client';

import React, { useState } from 'react';
import {
  Settings,
  Monitor,
  Bell,
  Eye,
  Shield,
  Accessibility,
  Save,
  RotateCcw,
  X
} from 'lucide-react';
import { useUserPreferences } from './UserPreferencesProvider';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const {
    preferences,
    updateDashboardPrefs,
    updateNotificationPrefs,
    updateDisplayPrefs,
    updatePrivacyPrefs,
    updateAccessibilityPrefs,
    resetPreferences,
  } = useUserPreferences();

  const [activeTab, setActiveTab] = useState<'dashboard' | 'notifications' | 'display' | 'privacy' | 'accessibility'>('dashboard');

  if (!isOpen) return null;

  const tabs = [
    { id: 'dashboard' as const, label: 'Dashboard', icon: Monitor },
    { id: 'notifications' as const, label: 'Notifications', icon: Bell },
    { id: 'display' as const, label: 'Display', icon: Eye },
    { id: 'privacy' as const, label: 'Privacy', icon: Shield },
    { id: 'accessibility' as const, label: 'Accessibility', icon: Accessibility },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-surface-1 border border-white/[0.06] rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <Settings className="w-6 h-6 text-vanguard-400" />
            <h2 className="text-xl font-semibold">Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-2 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex h-[600px]">
          {/* Sidebar */}
          <div className="w-64 border-r border-white/[0.06] p-4">
            <nav className="space-y-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                      activeTab === tab.id
                        ? 'bg-vanguard-600/20 text-vanguard-400'
                        : 'hover:bg-surface-2'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            {activeTab === 'dashboard' && (
              <div className="space-y-6">
                <h3 className="text-lg font-medium">Dashboard Preferences</h3>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Auto Refresh</label>
                      <p className="text-xs text-muted-foreground">Automatically refresh dashboard data</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.dashboard.autoRefresh}
                        onChange={(e) => updateDashboardPrefs({ autoRefresh: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Refresh Interval</label>
                      <p className="text-xs text-muted-foreground">How often to refresh data (seconds)</p>
                    </div>
                    <select
                      value={preferences.dashboard.refreshInterval}
                      onChange={(e) => updateDashboardPrefs({ refreshInterval: parseInt(e.target.value) })}
                      className="px-3 py-2 bg-surface-2 border border-white/[0.06] rounded focus:border-vanguard-400 focus:outline-none"
                    >
                      <option value={30}>30 seconds</option>
                      <option value={60}>1 minute</option>
                      <option value={300}>5 minutes</option>
                      <option value={600}>10 minutes</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Theme</label>
                      <p className="text-xs text-muted-foreground">Choose your preferred theme</p>
                    </div>
                    <select
                      value={preferences.dashboard.theme}
                      onChange={(e) => updateDashboardPrefs({ theme: e.target.value as any })}
                      className="px-3 py-2 bg-surface-2 border border-white/[0.06] rounded focus:border-vanguard-400 focus:outline-none"
                    >
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                      <option value="system">System</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Compact Mode</label>
                      <p className="text-xs text-muted-foreground">Use smaller spacing and components</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.dashboard.compactMode}
                        onChange={(e) => updateDashboardPrefs({ compactMode: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Show Animations</label>
                      <p className="text-xs text-muted-foreground">Enable smooth transitions and animations</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.dashboard.showAnimations}
                        onChange={(e) => updateDashboardPrefs({ showAnimations: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <h3 className="text-lg font-medium">Notification Preferences</h3>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Desktop Notifications</label>
                      <p className="text-xs text-muted-foreground">Show system notifications</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.notifications.desktop}
                        onChange={(e) => updateNotificationPrefs({ desktop: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Sound Notifications</label>
                      <p className="text-xs text-muted-foreground">Play sound for alerts</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.notifications.sound}
                        onChange={(e) => updateNotificationPrefs({ sound: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Email Notifications</label>
                      <p className="text-xs text-muted-foreground">Send alerts via email</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.notifications.email}
                        onChange={(e) => updateNotificationPrefs({ email: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="space-y-3">
                    <h4 className="text-sm font-medium">Alert Types</h4>
                    <div className="space-y-2 pl-4">
                      {Object.entries(preferences.notifications.alertTypes).map(([type, enabled]) => (
                        <div key={type} className="flex items-center justify-between">
                          <label className="text-sm capitalize">{type} Priority Alerts</label>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={enabled}
                              onChange={(e) => updateNotificationPrefs({
                                alertTypes: {
                                  ...preferences.notifications.alertTypes,
                                  [type]: e.target.checked
                                }
                              })}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'display' && (
              <div className="space-y-6">
                <h3 className="text-lg font-medium">Display Preferences</h3>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Date Format</label>
                      <p className="text-xs text-muted-foreground">How dates are displayed</p>
                    </div>
                    <select
                      value={preferences.display.dateFormat}
                      onChange={(e) => updateDisplayPrefs({ dateFormat: e.target.value as any })}
                      className="px-3 py-2 bg-surface-2 border border-white/[0.06] rounded focus:border-vanguard-400 focus:outline-none"
                    >
                      <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                      <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                      <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Time Format</label>
                      <p className="text-xs text-muted-foreground">12-hour or 24-hour format</p>
                    </div>
                    <select
                      value={preferences.display.timeFormat}
                      onChange={(e) => updateDisplayPrefs({ timeFormat: e.target.value as any })}
                      className="px-3 py-2 bg-surface-2 border border-white/[0.06] rounded focus:border-vanguard-400 focus:outline-none"
                    >
                      <option value="12h">12 Hour</option>
                      <option value="24h">24 Hour</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Number Format</label>
                      <p className="text-xs text-muted-foreground">How numbers are displayed</p>
                    </div>
                    <select
                      value={preferences.display.numberFormat}
                      onChange={(e) => updateDisplayPrefs({ numberFormat: e.target.value as any })}
                      className="px-3 py-2 bg-surface-2 border border-white/[0.06] rounded focus:border-vanguard-400 focus:outline-none"
                    >
                      <option value="standard">Standard (1,234)</option>
                      <option value="compact">Compact (1.2K)</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Default Chart Type</label>
                      <p className="text-xs text-muted-foreground">Preferred chart visualization</p>
                    </div>
                    <select
                      value={preferences.display.chartType}
                      onChange={(e) => updateDisplayPrefs({ chartType: e.target.value as any })}
                      className="px-3 py-2 bg-surface-2 border border-white/[0.06] rounded focus:border-vanguard-400 focus:outline-none"
                    >
                      <option value="line">Line Chart</option>
                      <option value="area">Area Chart</option>
                      <option value="bar">Bar Chart</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Show Grid</label>
                      <p className="text-xs text-muted-foreground">Display grid lines on charts</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.display.showGrid}
                        onChange={(e) => updateDisplayPrefs({ showGrid: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Show Legend</label>
                      <p className="text-xs text-muted-foreground">Display chart legends</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.display.showLegend}
                        onChange={(e) => updateDisplayPrefs({ showLegend: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'privacy' && (
              <div className="space-y-6">
                <h3 className="text-lg font-medium">Privacy Preferences</h3>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Analytics</label>
                      <p className="text-xs text-muted-foreground">Help improve the app with usage data</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.privacy.analytics}
                        onChange={(e) => updatePrivacyPrefs({ analytics: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Crash Reports</label>
                      <p className="text-xs text-muted-foreground">Send anonymous crash reports</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.privacy.crashReports}
                        onChange={(e) => updatePrivacyPrefs({ crashReports: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Data Retention</label>
                      <p className="text-xs text-muted-foreground">How long to keep local data (days)</p>
                    </div>
                    <select
                      value={preferences.privacy.dataRetention}
                      onChange={(e) => updatePrivacyPrefs({ dataRetention: parseInt(e.target.value) })}
                      className="px-3 py-2 bg-surface-2 border border-white/[0.06] rounded focus:border-vanguard-400 focus:outline-none"
                    >
                      <option value={30}>30 days</option>
                      <option value={60}>60 days</option>
                      <option value={90}>90 days</option>
                      <option value={365}>1 year</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'accessibility' && (
              <div className="space-y-6">
                <h3 className="text-lg font-medium">Accessibility Preferences</h3>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">High Contrast</label>
                      <p className="text-xs text-muted-foreground">Increase contrast for better visibility</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.accessibility.highContrast}
                        onChange={(e) => updateAccessibilityPrefs({ highContrast: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Reduced Motion</label>
                      <p className="text-xs text-muted-foreground">Minimize animations and transitions</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.accessibility.reducedMotion}
                        onChange={(e) => updateAccessibilityPrefs({ reducedMotion: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium">Large Text</label>
                      <p className="text-xs text-muted-foreground">Increase text size throughout the app</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.accessibility.largeText}
                        onChange={(e) => updateAccessibilityPrefs({ largeText: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vanguard-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-white/[0.06]">
          <button
            onClick={() => {
              if (confirm('Are you sure you want to reset all preferences to defaults?')) {
                resetPreferences();
              }
            }}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset to Defaults
          </button>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm bg-surface-2 hover:bg-surface-3 rounded transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm bg-vanguard-600 hover:bg-vanguard-700 text-white rounded transition-colors"
            >
              <Save className="w-4 h-4 inline mr-2" />
              Save Preferences
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}