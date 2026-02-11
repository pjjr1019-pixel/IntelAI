'use client';

import { Shield, AlertTriangle, TrendingUp, Clock, Target, Zap } from 'lucide-react';

export default function SignalQualityGuide() {
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <Shield className="w-8 h-8 text-green-400" />
        <div>
          <h1 className="text-3xl font-bold">Signal Quality & Risk Management</h1>
          <p className="text-muted-foreground">Advanced techniques for reliable signal detection and capital protection</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Counter-Signal Engine */}
        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="w-6 h-6 text-orange-400" />
            <h2 className="text-xl font-semibold">Counter-Signal Engine</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              The counter-signal engine actively searches for disconfirming data and opposing trends
              to validate signal strength and reduce false positives.
            </p>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <Target className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                <span>Analyzes historical cases where similar signals failed</span>
              </li>
              <li className="flex items-start gap-2">
                <Zap className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                <span>Boosts confidence when no counter-evidence is found</span>
              </li>
              <li className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                <span>Dramatically reduces false positives through systematic skepticism</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Narrative Saturation Detector */}
        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold">Narrative Saturation Detector</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              Uses BERT-based topic modeling to detect when narratives become oversaturated,
              indicating potential topping cycles in market trends.
            </p>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <Clock className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span>Measures progression from "early" to "mainstream" awareness</span>
              </li>
              <li className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span>Detects media overexposure and retail awareness peaks</span>
              </li>
              <li className="flex items-start gap-2">
                <Target className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span>Automatically downgrades alerts and reduces trading size</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Signal Decay & Half-Life */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-4">
          <Clock className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-semibold">Signal Decay & Half-Life Tracking</h2>
        </div>
        <div className="space-y-4">
          <p className="text-muted-foreground">
            Every signal has a calculated half-life that determines its relevance over time.
            This prevents late trades on stale narratives and overconfidence in outdated data.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-surface-2 rounded-lg p-4">
              <div className="text-2xl font-bold text-green-400 mb-1">3h</div>
              <div className="text-sm text-muted-foreground">Short-lived spikes</div>
            </div>
            <div className="bg-surface-2 rounded-lg p-4">
              <div className="text-2xl font-bold text-yellow-400 mb-1">3d</div>
              <div className="text-sm text-muted-foreground">Sustained trends</div>
            </div>
            <div className="bg-surface-2 rounded-lg p-4">
              <div className="text-2xl font-bold text-red-400 mb-1">∞</div>
              <div className="text-sm text-muted-foreground">Evergreen signals</div>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Management Features */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <h2 className="text-xl font-semibold mb-4">Risk Management Integration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold mb-3 text-green-400">Signal Validation</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Cross-references multiple data sources</li>
              <li>• Validates against historical patterns</li>
              <li>• Checks for contradictory evidence</li>
              <li>• Applies confidence modifiers</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-3 text-orange-400">Position Sizing</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Automatic size reduction for saturated narratives</li>
              <li>• Confidence-based position scaling</li>
              <li>• Risk-adjusted exposure limits</li>
              <li>• Portfolio correlation checks</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Best Practices */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <h2 className="text-xl font-semibold mb-4">Best Practices</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <h3 className="font-semibold text-green-400">✅ Do This</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Monitor counter-signal strength alongside primary signals</li>
                <li>• Use narrative saturation as an exit signal</li>
                <li>• Respect signal half-life calculations</li>
                <li>• Combine multiple validation methods</li>
              </ul>
            </div>
            <div className="space-y-3">
              <h3 className="font-semibold text-red-400">❌ Avoid This</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Trading signals without counter-signal analysis</li>
                <li>• Ignoring saturation warnings</li>
                <li>• Overconfidence in high-interest but stale signals</li>
                <li>• Single-source signal validation</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}