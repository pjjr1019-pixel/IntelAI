'use client';

import { useState } from 'react';
import {
  Target,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  Shield,
  Zap,
  DollarSign,
  Eye,
  Brain,
  BarChart3
} from 'lucide-react';

export default function WhatIsIntelAIPage() {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['problem']));

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
          <Target className="w-8 h-8 text-emerald-400" />
          <div>
            <h1 className="text-2xl font-bold">What Is Intel-AI?</h1>
            <p className="text-muted-foreground">The future of intelligent market intelligence</p>
          </div>
        </div>
      </div>

      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <Target className="w-6 h-6 text-emerald-400" />
          <h2 className="text-xl font-semibold">Simple Overview for Everyone</h2>
        </div>

        {/* The Problem */}
        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('problem')}
          >
            <div className="flex items-center gap-3">
              <Eye className="w-5 h-5 text-red-400" />
              <span className="font-medium">The Problem: Markets Move Faster Than Humans Can Process</span>
            </div>
            {expandedSections.has('problem') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('problem') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Traditional market analysis relies on humans reading news, watching charts, and making decisions.
                But markets react to information in milliseconds. By the time you read a news headline, the smart money
                has already moved. Intel-AI solves this by continuously monitoring everything, 24/7, and alerting you
                to emerging trends before they become obvious.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div className="flex items-start gap-3">
                  <TrendingUp className="w-5 h-5 text-red-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-red-400">Information Overload</h4>
                    <p className="text-sm text-muted-foreground">Too much news, too many charts, impossible to monitor everything</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-orange-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-orange-400">Reaction Time</h4>
                    <p className="text-sm text-muted-foreground">By the time you see a trend, it's often too late to act</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* The Solution */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('solution')}
          >
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-yellow-400" />
              <span className="font-medium">The Solution: AI That Thinks Like a Professional Trader</span>
            </div>
            {expandedSections.has('solution') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('solution') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Intel-AI is like having a team of expert analysts working around the clock. Our AI continuously scans
                news, social media, economic data, and market movements to identify patterns that indicate major events
                before they happen. It's not just faster—it's smarter, learning from millions of historical examples
                to recognize the early warning signs of market-moving events.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div className="flex items-start gap-3">
                  <Brain className="w-5 h-5 text-purple-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-purple-400">24/7 Monitoring</h4>
                    <p className="text-sm text-muted-foreground">Never misses important developments, even while you sleep</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <BarChart3 className="w-5 h-5 text-blue-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-400">Pattern Recognition</h4>
                    <p className="text-sm text-muted-foreground">Learns from history to spot emerging trends early</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* How It Makes Money */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('value')}
          >
            <div className="flex items-center gap-3">
              <DollarSign className="w-5 h-5 text-green-400" />
              <span className="font-medium">How It Creates Value: Early Detection = Better Decisions</span>
            </div>
            {expandedSections.has('value') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('value') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                The value comes from timing. When you know about a trend before the crowd, you can position your
                portfolio advantageously. Whether it's avoiding a downturn or capturing an upside opportunity,
                early awareness translates directly to better investment outcomes.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                <div className="text-center p-4 bg-surface-3 rounded-lg">
                  <div className="text-2xl font-bold text-green-400 mb-2">Early</div>
                  <p className="text-sm text-muted-foreground">Detect trends before mainstream awareness</p>
                </div>
                <div className="text-center p-4 bg-surface-3 rounded-lg">
                  <div className="text-2xl font-bold text-blue-400 mb-2">Smart</div>
                  <p className="text-sm text-muted-foreground">AI validates signals with historical patterns</p>
                </div>
                <div className="text-center p-4 bg-surface-3 rounded-lg">
                  <div className="text-2xl font-bold text-purple-400 mb-2">Actionable</div>
                  <p className="text-sm text-muted-foreground">Clear alerts with confidence scores</p>
                </div>
              </div>
            </div>
          )}

          {/* Key Features */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('features')}
          >
            <div className="flex items-center gap-3">
              <Target className="w-5 h-5 text-emerald-400" />
              <span className="font-medium">Key Features That Matter</span>
            </div>
            {expandedSections.has('features') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('features') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h4 className="font-semibold text-emerald-400">Intelligence Gathering</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li>• Monitors news from 1000+ sources globally</li>
                    <li>• Tracks social media trends and sentiment</li>
                    <li>• Analyzes economic indicators and reports</li>
                    <li>• Processes satellite imagery for real-world events</li>
                  </ul>
                </div>

                <div className="space-y-3">
                  <h4 className="font-semibold text-blue-400">Smart Analysis</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li>• AI learns from millions of historical events</li>
                    <li>• Cross-references multiple data sources</li>
                    <li>• Eliminates false signals automatically</li>
                    <li>• Provides confidence scores for every alert</li>
                  </ul>
                </div>

                <div className="space-y-3">
                  <h4 className="font-semibold text-purple-400">Risk Management</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li>• Built-in safeguards prevent reckless decisions</li>
                    <li>• Gradual automation builds trust over time</li>
                    <li>• Remembers past mistakes to avoid repetition</li>
                    <li>• Paper trading mode for safe testing</li>
                  </ul>
                </div>

                <div className="space-y-3">
                  <h4 className="font-semibold text-orange-400">Easy to Use</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li>• Clean, intuitive dashboard interface</li>
                    <li>• Customizable alerts and notifications</li>
                    <li>• Mobile-responsive design</li>
                    <li>• API access for integration with other tools</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Why It Works */}
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('why')}
          >
            <div className="flex items-center gap-3">
              <Brain className="w-5 h-5 text-indigo-400" />
              <span className="font-medium">Why This Approach Works: Learning from History</span>
            </div>
            {expandedSections.has('why') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('why') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Markets follow patterns. Every major event—from economic crises to product launches—has early warning
                signs. Our AI has studied thousands of these events to recognize the patterns. It's like having a
                trader with decades of experience who never sleeps and never forgets.
              </p>

              <div className="bg-surface-3 rounded-lg p-4 mt-4">
                <h4 className="font-semibold text-indigo-400 mb-2">The Learning Advantage</h4>
                <p className="text-sm text-muted-foreground">
                  While humans get tired and make emotional decisions, our AI continuously improves. Every market
                  event teaches it something new, making it better at predicting the next one. This compounding
                  knowledge advantage is what creates sustainable value.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Call to Action */}
      <div className="bg-gradient-to-r from-emerald-400/10 to-blue-400/10 rounded-xl border border-emerald-400/20 p-6">
        <div className="text-center">
          <h3 className="text-xl font-semibold mb-2">Ready to Get Started?</h3>
          <p className="text-muted-foreground mb-4">
            Intel-AI is more than just another analytics tool—it's your edge in an increasingly complex market.
            Start with our free tier and experience the difference AI-powered intelligence can make.
          </p>
          <div className="flex justify-center gap-4">
            <button className="px-6 py-2 bg-emerald-400 text-black font-semibold rounded-lg hover:bg-emerald-300 transition-colors">
              Start Free Trial
            </button>
            <button className="px-6 py-2 border border-white/20 text-white font-semibold rounded-lg hover:bg-white/10 transition-colors">
              Schedule Demo
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}