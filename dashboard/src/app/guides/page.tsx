'use client';

import { BookOpen, AlertTriangle, TrendingUp, Settings, Shield, BarChart3, RefreshCw, Database, Zap } from 'lucide-react';
import Link from 'next/link';

export default function Guides() {
  const guides = [
    {
      title: 'What Is Intel-AI',
      description: 'Simple overview of how our AI platform works and its value proposition',
      icon: Zap,
      href: '/guides/what-is-intel-ai',
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-400/10'
    },
    {
      title: 'How It Works',
      description: 'Overview of anomaly detection, data sources, and core algorithms',
      icon: BookOpen,
      href: '/guides/how-it-works',
      color: 'text-blue-400',
      bgColor: 'bg-blue-400/10'
    },
    {
      title: 'Alert Rules',
      description: 'Create custom conditions for automatic alert generation',
      icon: AlertTriangle,
      href: '/guides/alert-rules',
      color: 'text-orange-400',
      bgColor: 'bg-orange-400/10'
    },
    {
      title: 'Signal Quality',
      description: 'Counter-signals, narrative saturation, and risk management',
      icon: Shield,
      href: '/guides/signal-quality',
      color: 'text-green-400',
      bgColor: 'bg-green-400/10'
    },
    {
      title: 'Decision Transparency',
      description: 'Why not trade explanations, confidence decomposition, replay mode',
      icon: BarChart3,
      href: '/guides/decision-transparency',
      color: 'text-purple-400',
      bgColor: 'bg-purple-400/10'
    },
    {
      title: 'Trading Survival',
      description: 'Kill-switches, gradual autonomy, and capital memory',
      icon: RefreshCw,
      href: '/guides/trading-survival',
      color: 'text-red-400',
      bgColor: 'bg-red-400/10'
    },
    {
      title: 'Architecture',
      description: 'System architecture, API, database, and deployment',
      icon: Database,
      href: '/guides/architecture',
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-400/10'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen className="w-8 h-8 text-vanguard-400" />
          <div>
            <h1 className="text-2xl font-bold">Guides</h1>
            <p className="text-muted-foreground">Learn how to use Vanguard Signal effectively</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {guides.map((guide) => {
          const Icon = guide.icon;
          return (
            <Link
              key={guide.href}
              href={guide.href}
              className="block p-6 bg-surface-1 rounded-xl border border-white/[0.06] hover:border-white/[0.12] hover:bg-surface-1/80 cursor-pointer transition-all duration-200"
            >
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-lg ${guide.bgColor}`}>
                  <Icon className={`w-6 h-6 ${guide.color}`} />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold mb-2">{guide.title}</h3>
                  <p className="text-sm text-muted-foreground mb-3">{guide.description}</p>
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <h2 className="text-xl font-semibold mb-4">Getting Started</h2>
        <div className="space-y-4 text-muted-foreground">
          <p>
            Welcome to Vanguard Signal! This platform helps you detect market anomalies and trends
            before they become major events. Our comprehensive guide system covers everything from
            basic setup to advanced trading strategies.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div>
              <h3 className="font-semibold text-foreground mb-2">Start Here:</h3>
              <ul className="space-y-1 text-sm">
                <li>• <strong>How It Works</strong> - Understand the core concepts</li>
                <li>• <strong>Alert Rules</strong> - Set up your first custom alerts</li>
                <li>• <strong>Signal Quality</strong> - Learn about risk management</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-foreground mb-2">Advanced Topics:</h3>
              <ul className="space-y-1 text-sm">
                <li>• <strong>Decision Transparency</strong> - Understand AI reasoning</li>
                <li>• <strong>Trading Survival</strong> - Capital protection strategies</li>
                <li>• <strong>Architecture</strong> - Technical implementation details</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}