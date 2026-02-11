'use client';

import { RefreshCw, Shield, TrendingDown, Zap, Target, DollarSign } from 'lucide-react';

export default function TradingSurvivalGuide() {
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <RefreshCw className="w-8 h-8 text-red-400" />
        <div>
          <h1 className="text-3xl font-bold">Trading Survival & Capital Protection</h1>
          <p className="text-muted-foreground">Advanced risk management and capital preservation strategies</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Kill-Switches */}
        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <Shield className="w-6 h-6 text-red-400" />
            <h2 className="text-xl font-semibold">Kill-Switches</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              Automatic system pause triggers that activate during anomalous market conditions
              or when signal behavior indicates potential problems.
            </p>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <Zap className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                <span>Anomaly instability detection</span>
              </li>
              <li className="flex items-start gap-2">
                <TrendingDown className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                <span>Signal volatility collapse triggers</span>
              </li>
              <li className="flex items-start gap-2">
                <Target className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                <span>Model disagreement spike detection</span>
              </li>
              <li className="flex items-start gap-2">
                <RefreshCw className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                <span>Automatic system pause for "weird world" conditions</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Gradual Autonomy Ramp */}
        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <Target className="w-6 h-6 text-orange-400" />
            <h2 className="text-xl font-semibold">Gradual Autonomy Ramp</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              Progressive feature unlocking based on statistical proof and system stability,
              preventing overconfidence from single good performance periods.
            </p>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                <span>0% → 10% → 25% → 50% → 100% autonomy progression</span>
              </li>
              <li className="flex items-start gap-2">
                <Target className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                <span>Requires statistical proof and time stability</span>
              </li>
              <li className="flex items-start gap-2">
                <RefreshCw className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                <span>No violations allowed for feature unlocks</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Capital Memory */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-4">
          <DollarSign className="w-6 h-6 text-green-400" />
          <h2 className="text-xl font-semibold">Capital Memory</h2>
        </div>
        <div className="space-y-4">
          <p className="text-muted-foreground">
            The system tracks past drawdowns and painful market environments to implement
            size reduction and hesitation in similar conditions, mimicking human "scar tissue" learning.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <TrendingDown className="w-8 h-8 text-red-400 mx-auto mb-2" />
              <h3 className="font-semibold mb-1">Drawdown Tracking</h3>
              <p className="text-sm text-muted-foreground">Records past losses and recovery periods</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <Target className="w-8 h-8 text-red-400 mx-auto mb-2" />
              <h3 className="font-semibold mb-1">Lethal Signal ID</h3>
              <p className="text-sm text-muted-foreground">Identifies conditions that caused major losses</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <Shield className="w-8 h-8 text-red-400 mx-auto mb-2" />
              <h3 className="font-semibold mb-1">Adaptive Sizing</h3>
              <p className="text-sm text-muted-foreground">Reduces position size in similar regimes</p>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Management Integration */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <h2 className="text-xl font-semibold mb-4">Risk Management Integration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold mb-3 text-red-400">Protection Mechanisms</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Automatic position reduction in high-risk conditions</li>
              <li>• Correlation-based exposure limits</li>
              <li>• Volatility-adjusted stop losses</li>
              <li>• Maximum drawdown circuit breakers</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-3 text-orange-400">Recovery Protocols</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Gradual position rebuilding after losses</li>
              <li>• Reduced risk-taking during recovery periods</li>
              <li>• Conservative signal filtering post-drawdown</li>
              <li>• Performance-based autonomy adjustments</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Implementation Status */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <h2 className="text-xl font-semibold mb-4">Implementation Status</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-yellow-400/10 border border-yellow-400/20 rounded-lg p-4">
              <Shield className="w-6 h-6 text-yellow-400 mb-2" />
              <h3 className="font-semibold text-yellow-400 mb-1">Basic Kill-Switches</h3>
              <p className="text-sm text-muted-foreground">Signal volatility and anomaly detection</p>
            </div>
            <div className="bg-blue-400/10 border border-blue-400/20 rounded-lg p-4">
              <Target className="w-6 h-6 text-blue-400 mb-2" />
              <h3 className="font-semibold text-blue-400 mb-1">Planned</h3>
              <p className="text-sm text-muted-foreground">Gradual autonomy ramp</p>
            </div>
            <div className="bg-blue-400/10 border border-blue-400/20 rounded-lg p-4">
              <DollarSign className="w-6 h-6 text-blue-400 mb-2" />
              <h3 className="font-semibold text-blue-400 mb-1">Planned</h3>
              <p className="text-sm text-muted-foreground">Capital memory system</p>
            </div>
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
                <li>• Respect kill-switch activations</li>
                <li>• Monitor capital memory warnings</li>
                <li>• Use gradual autonomy progression</li>
                <li>• Review risk management settings regularly</li>
                <li>• Maintain emergency manual override capability</li>
              </ul>
            </div>
            <div className="space-y-3">
              <h3 className="font-semibold text-red-400">❌ Avoid This</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Overriding kill-switch activations</li>
                <li>• Rapid autonomy increases without testing</li>
                <li>• Ignoring capital memory signals</li>
                <li>• Trading through high-volatility periods</li>
                <li>• Excessive position sizing during recovery</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Emergency Procedures */}
      <div className="bg-red-400/10 border border-red-400/20 rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 text-red-400">Emergency Procedures</h2>
        <div className="space-y-4">
          <p className="text-muted-foreground">
            When kill-switches activate or capital memory triggers warnings, follow these procedures:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-semibold mb-2">Immediate Actions</h3>
              <ul className="space-y-1 text-sm text-muted-foreground">
                <li>• Stop all automated trading</li>
                <li>• Reduce position sizes by 50%</li>
                <li>• Enable maximum stop losses</li>
                <li>• Notify risk management team</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-2">Post-Incident Review</h3>
              <ul className="space-y-1 text-muted-foreground">
                <li>• Analyze trigger conditions</li>
                <li>• Review system settings</li>
                <li>• Update risk parameters</li>
                <li>• Document lessons learned</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}