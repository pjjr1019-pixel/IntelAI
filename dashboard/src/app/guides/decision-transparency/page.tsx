'use client';

import { BarChart3, RotateCcw, Eye, Brain, AlertCircle, CheckCircle } from 'lucide-react';

export default function DecisionTransparencyGuide() {
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <BarChart3 className="w-8 h-8 text-purple-400" />
        <div>
          <h1 className="text-3xl font-bold">Decision Transparency & Trust</h1>
          <p className="text-muted-foreground">Understanding AI reasoning, confidence levels, and decision-making processes</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Why Not Trade Explanations */}
        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <AlertCircle className="w-6 h-6 text-orange-400" />
            <h2 className="text-xl font-semibold">"Why Not Trade?" Explanations</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              When the system decides not to generate an alert or recommend a trade, it provides
              detailed explanations for complete transparency.
            </p>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <Eye className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                <span>Documents conflicting signals and insufficient persistence</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                <span>Includes risk constraint violations in explanations</span>
              </li>
              <li className="flex items-start gap-2">
                <Brain className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                <span>Builds user trust through responsible, non-reckless AI behavior</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Confidence Decomposition */}
        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <BarChart3 className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold">Confidence Decomposition</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              Confidence scores are broken down into specific components, giving users
              visibility into what factors influence the system's decision-making.
            </p>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <BarChart3 className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span>Data quality assessment</span>
              </li>
              <li className="flex items-start gap-2">
                <Brain className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span>Model agreement analysis</span>
              </li>
              <li className="flex items-start gap-2">
                <Eye className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span>Historical similarity scoring</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span>Execution environment confidence</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Replay Mode */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-4">
          <RotateCcw className="w-6 h-6 text-green-400" />
          <h2 className="text-xl font-semibold">Replay Mode (Post-Mortem Simulator)</h2>
        </div>
        <div className="space-y-4">
          <p className="text-muted-foreground">
            Replay mode allows you to rewind the system state after alerts or trades to analyze
            decision-making processes and identify factors that influenced outcomes.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <RotateCcw className="w-8 h-8 text-green-400 mx-auto mb-2" />
              <h3 className="font-semibold mb-1">State Rewind</h3>
              <p className="text-sm text-muted-foreground">System state rewind after alerts/trades</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <BarChart3 className="w-8 h-8 text-green-400 mx-auto mb-2" />
              <h3 className="font-semibold mb-1">Signal Replay</h3>
              <p className="text-sm text-muted-foreground">Signals as they arrived in real-time</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <Eye className="w-8 h-8 text-green-400 mx-auto mb-2" />
              <h3 className="font-semibold mb-1">Factor Analysis</h3>
              <p className="text-sm text-muted-foreground">Decision-changing factors and timelines</p>
            </div>
          </div>
          <div className="mt-4 p-4 bg-surface-2 rounded-lg">
            <h4 className="font-semibold mb-2">Use Cases:</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Debugging and audits</li>
              <li>• Model training and improvement</li>
              <li>• Investor confidence building</li>
              <li>• Learning from past decisions</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Trust Building Features */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <h2 className="text-xl font-semibold mb-4">Trust Building Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold mb-3 text-blue-400">Transparency Tools</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Complete audit trails of decisions</li>
              <li>• Confidence score breakdowns</li>
              <li>• Counter-signal analysis visibility</li>
              <li>• Risk assessment explanations</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-3 text-green-400">Accountability Measures</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Clear reasoning for all actions/inactions</li>
              <li>• Historical performance tracking</li>
              <li>• Error acknowledgment and learning</li>
              <li>• Conservative default behavior</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Implementation Status */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <h2 className="text-xl font-semibold mb-4">Implementation Status</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-green-400/10 border border-green-400/20 rounded-lg p-4">
              <CheckCircle className="w-6 h-6 text-green-400 mb-2" />
              <h3 className="font-semibold text-green-400 mb-1">Completed</h3>
              <p className="text-sm text-muted-foreground">Basic confidence scoring and alert explanations</p>
            </div>
            <div className="bg-yellow-400/10 border border-yellow-400/20 rounded-lg p-4">
              <RotateCcw className="w-6 h-6 text-yellow-400 mb-2" />
              <h3 className="font-semibold text-yellow-400 mb-1">In Progress</h3>
              <p className="text-sm text-muted-foreground">Replay mode development</p>
            </div>
            <div className="bg-blue-400/10 border border-blue-400/20 rounded-lg p-4">
              <BarChart3 className="w-6 h-6 text-blue-400 mb-2" />
              <h3 className="font-semibold text-blue-400 mb-1">Planned</h3>
              <p className="text-sm text-muted-foreground">Advanced confidence decomposition</p>
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
                <li>• Always review "why not trade" explanations</li>
                <li>• Use replay mode to understand past decisions</li>
                <li>• Monitor confidence score components</li>
                <li>• Validate AI reasoning against your judgment</li>
              </ul>
            </div>
            <div className="space-y-3">
              <h3 className="font-semibold text-red-400">❌ Avoid This</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Blindly following AI recommendations</li>
                <li>• Ignoring low confidence signals</li>
                <li>• Not reviewing decision explanations</li>
                <li>• Over-relying on single confidence metrics</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}