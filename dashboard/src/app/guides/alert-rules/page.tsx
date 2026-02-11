'use client';

import { useState } from 'react';
import { AlertTriangle, BookOpen, ChevronDown, ChevronRight, HelpCircle, Settings, TrendingUp, Zap } from 'lucide-react';

export default function AlertRulesPage() {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['basics']));

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-8 h-8 text-orange-400" />
          <div>
            <h1 className="text-2xl font-bold">Alert Rules</h1>
            <p className="text-muted-foreground">Create custom conditions for automatic alert generation</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-4 py-2 bg-vanguard-600 hover:bg-vanguard-700 text-white rounded-lg transition-colors flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Create Rule
          </button>
        </div>
      </div>

      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <BookOpen className="w-6 h-6 text-vanguard-400" />
          <h2 className="text-xl font-semibold">Alert Rules Guide</h2>
        </div>

        {/* What Are Alert Rules */}
        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('basics')}
          >
            <div className="flex items-center gap-3">
              <HelpCircle className="w-5 h-5 text-vanguard-400" />
              <h3 className="font-semibold">What Are Alert Rules?</h3>
            </div>
            {expandedSections.has('basics') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('basics') && (
            <div className="ml-8 space-y-3 text-muted-foreground">
              <p>
                Alert Rules are like "if-then" statements for your trend data. Instead of waiting for the anomaly detection system to find patterns, you can define specific rules that trigger alerts when certain thresholds are met.
              </p>
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                <p className="font-medium text-blue-400 mb-2">Example:</p>
                <p><strong>IF</strong> a keyword's interest score goes above 80 in the US</p>
                <p><strong>THEN</strong> create a high-priority alert</p>
              </div>
            </div>
          )}

          {/* How Alert Rules Work */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('how-it-works')}
          >
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-vanguard-400" />
              <h3 className="font-semibold">How Alert Rules Work</h3>
            </div>
            {expandedSections.has('how-it-works') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('how-it-works') && (
            <div className="ml-8 space-y-3 text-muted-foreground">
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div className="text-center">
                  <div className="w-8 h-8 bg-vanguard-600 rounded-full flex items-center justify-center text-white font-bold mx-auto mb-2">1</div>
                  <p className="text-sm font-medium">Rule Definition</p>
                  <p className="text-xs">You create a rule with conditions</p>
                </div>
                <div className="text-center">
                  <div className="w-8 h-8 bg-vanguard-600 rounded-full flex items-center justify-center text-white font-bold mx-auto mb-2">2</div>
                  <p className="text-sm font-medium">Monitoring</p>
                  <p className="text-xs">System checks trend data</p>
                </div>
                <div className="text-center">
                  <div className="w-8 h-8 bg-vanguard-600 rounded-full flex items-center justify-center text-white font-bold mx-auto mb-2">3</div>
                  <p className="text-sm font-medium">Triggering</p>
                  <p className="text-xs">Conditions are met</p>
                </div>
                <div className="text-center">
                  <div className="w-8 h-8 bg-vanguard-600 rounded-full flex items-center justify-center text-white font-bold mx-auto mb-2">4</div>
                  <p className="text-sm font-medium">Alert Creation</p>
                  <p className="text-xs">Alert is generated</p>
                </div>
                <div className="text-center">
                  <div className="w-8 h-8 bg-vanguard-600 rounded-full flex items-center justify-center text-white font-bold mx-auto mb-2">5</div>
                  <p className="text-sm font-medium">Notification</p>
                  <p className="text-xs">You get notified</p>
                </div>
              </div>
            </div>
          )}

          {/* Basic Rule Configuration */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('configuration')}
          >
            <div className="flex items-center gap-3">
              <Settings className="w-5 h-5 text-vanguard-400" />
              <h3 className="font-semibold">Basic Rule Configuration</h3>
            </div>
            {expandedSections.has('configuration') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('configuration') && (
            <div className="ml-8 space-y-4 text-muted-foreground">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-foreground mb-3">Core Settings</h4>
                  <div className="space-y-3">
                    <div className="border border-white/10 rounded-lg p-3">
                      <div className="font-medium text-sm">Name</div>
                      <div className="text-xs text-muted-foreground">Friendly name for the rule</div>
                      <div className="text-xs font-mono bg-black/20 p-1 rounded mt-1">"Bank Run Detector"</div>
                    </div>
                    <div className="border border-white/10 rounded-lg p-3">
                      <div className="font-medium text-sm">Description</div>
                      <div className="text-xs text-muted-foreground">What this rule detects</div>
                      <div className="text-xs font-mono bg-black/20 p-1 rounded mt-1">"Alerts when banking terms spike"</div>
                    </div>
                    <div className="border border-white/10 rounded-lg p-3">
                      <div className="font-medium text-sm">Severity</div>
                      <div className="text-xs text-muted-foreground">Alert importance level</div>
                      <div className="text-xs font-mono bg-black/20 p-1 rounded mt-1">low | medium | high | critical</div>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-foreground mb-3">Condition Settings</h4>
                  <div className="space-y-3">
                    <div className="border border-white/10 rounded-lg p-3">
                      <div className="font-medium text-sm">Condition Type</div>
                      <div className="text-xs text-muted-foreground">What to measure</div>
                      <div className="text-xs space-y-1 mt-1">
                        <div>• <strong>interest_spike</strong> - Raw interest score (0-100)</div>
                        <div>• <strong>velocity_threshold</strong> - Rate of change</div>
                        <div>• <strong>rank_change</strong> - Position improvement</div>
                        <div>• <strong>correlation</strong> - Relationship between terms</div>
                      </div>
                    </div>
                    <div className="border border-white/10 rounded-lg p-3">
                      <div className="font-medium text-sm">Threshold Value</div>
                      <div className="text-xs text-muted-foreground">The trigger number</div>
                      <div className="text-xs font-mono bg-black/20 p-1 rounded mt-1">75.0</div>
                    </div>
                    <div className="border border-white/10 rounded-lg p-3">
                      <div className="font-medium text-sm">Comparison Operator</div>
                      <div className="text-xs text-muted-foreground">How to compare values</div>
                      <div className="text-xs font-mono bg-black/20 p-1 rounded mt-1">&gt; | &gt;= | &lt; | &lt;= | ==</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Targeting Options */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('targeting')}
          >
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-vanguard-400" />
              <h3 className="font-semibold">Targeting Specific Content</h3>
            </div>
            {expandedSections.has('targeting') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('targeting') && (
            <div className="ml-8 space-y-3 text-muted-foreground">
              <p className="text-sm">Focus your rules on specific keywords, categories, or geographic regions. Leave empty to monitor everything.</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border border-white/10 rounded-lg p-4">
                  <div className="font-medium text-sm mb-2">Target Keywords</div>
                  <div className="text-xs text-muted-foreground mb-2">Specific terms to watch</div>
                  <div className="text-xs font-mono bg-black/20 p-2 rounded">["bank run", "deposit flight"]</div>
                </div>
                <div className="border border-white/10 rounded-lg p-4">
                  <div className="font-medium text-sm mb-2">Target Categories</div>
                  <div className="text-xs text-muted-foreground mb-2">Content categories</div>
                  <div className="text-xs font-mono bg-black/20 p-2 rounded">["finance", "economics"]</div>
                </div>
                <div className="border border-white/10 rounded-lg p-4">
                  <div className="font-medium text-sm mb-2">Geo Scope</div>
                  <div className="text-xs text-muted-foreground mb-2">Countries/regions</div>
                  <div className="text-xs font-mono bg-black/20 p-2 rounded">["US", "GB", "DE"]</div>
                </div>
              </div>
            </div>
          )}

          {/* Notification Settings */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('notifications')}
          >
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-vanguard-400" />
              <h3 className="font-semibold">Notification Settings</h3>
            </div>
            {expandedSections.has('notifications') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('notifications') && (
            <div className="ml-8 space-y-3 text-muted-foreground">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-foreground mb-3">Notification Types</h4>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 border border-white/10 rounded-lg">
                      <div>
                        <div className="font-medium text-sm">Email Notifications</div>
                        <div className="text-xs text-muted-foreground">Send email alerts</div>
                      </div>
                      <div className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">Enabled</div>
                    </div>
                    <div className="flex items-center justify-between p-3 border border-white/10 rounded-lg">
                      <div>
                        <div className="font-medium text-sm">Desktop Notifications</div>
                        <div className="text-xs text-muted-foreground">Show desktop popups</div>
                      </div>
                      <div className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">Enabled</div>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="font-medium text-foreground mb-3">Cooldown Settings</h4>
                  <div className="space-y-3">
                    <div className="border border-white/10 rounded-lg p-3">
                      <div className="font-medium text-sm">Cooldown Minutes</div>
                      <div className="text-xs text-muted-foreground mb-2">Wait time between alerts for same entity</div>
                      <div className="text-xs font-mono bg-black/20 p-1 rounded">60</div>
                    </div>
                    <div className="border border-white/10 rounded-lg p-3">
                      <div className="font-medium text-sm">Email Recipients</div>
                      <div className="text-xs text-muted-foreground mb-2">Who gets the emails</div>
                      <div className="text-xs font-mono bg-black/20 p-1 rounded">["analyst@company.com"]</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Example Rules */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('examples')}
          >
            <div className="flex items-center gap-3">
              <BookOpen className="w-5 h-5 text-vanguard-400" />
              <h3 className="font-semibold">Example Rules</h3>
            </div>
            {expandedSections.has('examples') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('examples') && (
            <div className="ml-8 space-y-4 text-muted-foreground">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="border border-white/10 rounded-lg p-4">
                  <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                    Banking Crisis Detector
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div><strong>Condition:</strong> interest_spike &gt; 70</div>
                    <div><strong>Keywords:</strong> "bank run", "deposit insurance"</div>
                    <div><strong>Geo:</strong> US</div>
                    <div><strong>Severity:</strong> critical</div>
                    <div><strong>Cooldown:</strong> 120 min</div>
                  </div>
                </div>

                <div className="border border-white/10 rounded-lg p-4">
                  <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-blue-400" />
                    Viral Content Alert
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div><strong>Condition:</strong> velocity_threshold &gt; 50</div>
                    <div><strong>Categories:</strong> social, entertainment</div>
                    <div><strong>Severity:</strong> medium</div>
                    <div><strong>Cooldown:</strong> 30 min</div>
                  </div>
                </div>

                <div className="border border-white/10 rounded-lg p-4">
                  <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-yellow-400" />
                    Regional Event Monitor
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div><strong>Condition:</strong> rank_change &gt;= 20</div>
                    <div><strong>Geo:</strong> US-CA, US-NY, US-TX</div>
                    <div><strong>Severity:</strong> low</div>
                    <div><strong>Cooldown:</strong> 60 min</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Best Practices */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('best-practices')}
          >
            <div className="flex items-center gap-3">
              <Settings className="w-5 h-5 text-vanguard-400" />
              <h3 className="font-semibold">Best Practices</h3>
            </div>
            {expandedSections.has('best-practices') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('best-practices') && (
            <div className="ml-8 space-y-4 text-muted-foreground">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-green-400 mb-3">✅ Do This</h4>
                  <ul className="space-y-2 text-sm">
                    <li>• Start with 1-2 rules focused on specific scenarios</li>
                    <li>• Use medium severity for initial testing</li>
                    <li>• Set cooldowns of 60+ minutes initially</li>
                    <li>• Monitor trigger history for a week before adjusting</li>
                    <li>• Use specific keywords to reduce false positives</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-red-400 mb-3">❌ Avoid This</h4>
                  <ul className="space-y-2 text-sm">
                    <li>• Don't create too many rules at once</li>
                    <li>• Don't set thresholds too low initially</li>
                    <li>• Don't use critical severity for testing</li>
                    <li>• Don't forget to set appropriate cooldowns</li>
                    <li>• Don't leave targeting fields completely empty</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Troubleshooting */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('troubleshooting')}
          >
            <div className="flex items-center gap-3">
              <HelpCircle className="w-5 h-5 text-vanguard-400" />
              <h3 className="font-semibold">Troubleshooting</h3>
            </div>
            {expandedSections.has('troubleshooting') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('troubleshooting') && (
            <div className="ml-8 space-y-4 text-muted-foreground">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-orange-400 mb-3">Rule Not Triggering</h4>
                  <ul className="space-y-2 text-sm">
                    <li>• Check if the rule is <strong>enabled</strong></li>
                    <li>• Verify <strong>target keywords</strong> match actual trend data</li>
                    <li>• Confirm <strong>geo scope</strong> includes monitored regions</li>
                    <li>• Review <strong>threshold values</strong> against real data</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-red-400 mb-3">Too Many False Alerts</h4>
                  <ul className="space-y-2 text-sm">
                    <li>• Increase <strong>threshold values</strong></li>
                    <li>• Add more specific <strong>target keywords</strong></li>
                    <li>• Extend <strong>cooldown minutes</strong></li>
                    <li>• Use <strong>categories</strong> to narrow focus</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}