'use client';

import { useState } from 'react';
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  HelpCircle,
  TrendingUp,
  Radio,
  AlertTriangle,
  BarChart3,
  Zap,
  Database,
  Globe,
  Cpu,
  Eye,
  Target,
  Clock,
  Shield,
  Brain,
  DollarSign,
  PieChart,
  Activity,
  FileText,
  Mail,
  Settings,
  Lightbulb,
  Network,
  Lock
} from 'lucide-react';

export default function HowItWorksPage() {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['overview']));

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
          <BookOpen className="w-8 h-8 text-blue-400" />
          <div>
            <h1 className="text-2xl font-bold">How It Works</h1>
            <p className="text-muted-foreground">Understanding the Vanguard Signal system architecture</p>
          </div>
        </div>
      </div>

      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <BookOpen className="w-6 h-6 text-vanguard-400" />
          <h2 className="text-xl font-semibold">System Overview</h2>
        </div>

        {/* System Overview */}
        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('overview')}
          >
            <div className="flex items-center gap-3">
              <Eye className="w-5 h-5 text-vanguard-400" />
              <span className="font-medium">What is Vanguard Signal?</span>
            </div>
            {expandedSections.has('overview') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('overview') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Vanguard Signal is an advanced OSINT (Open Source Intelligence) platform designed for pre-event anomaly detection
                and predictive intelligence. The system continuously monitors global trends, news, and social signals to identify
                emerging patterns that may indicate significant events before they become widely known.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div className="flex items-start gap-3">
                  <Target className="w-5 h-5 text-green-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-green-400">Early Detection</h4>
                    <p className="text-sm text-muted-foreground">Identify emerging trends and anomalies before mainstream awareness</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-blue-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-400">Risk Intelligence</h4>
                    <p className="text-sm text-muted-foreground">Monitor geopolitical, financial, and social risk indicators</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <TrendingUp className="w-5 h-5 text-purple-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-purple-400">Predictive Analytics</h4>
                    <p className="text-sm text-muted-foreground">Use machine learning to forecast trend developments</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Zap className="w-5 h-5 text-yellow-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-yellow-400">Real-time Alerts</h4>
                    <p className="text-sm text-muted-foreground">Instant notifications when critical thresholds are crossed</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Data Sources */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('data-sources')}
          >
            <div className="flex items-center gap-3">
              <Radio className="w-5 h-5 text-vanguard-400" />
              <span className="font-medium">Data Sources & Ingestion</span>
            </div>
            {expandedSections.has('data-sources') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('data-sources') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                The system aggregates data from multiple sources to provide comprehensive coverage of global events and trends.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Globe className="w-4 h-4 text-blue-400" />
                    Google Trends
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Real-time search interest data across 200+ countries and regions, updated hourly
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Radio className="w-4 h-4 text-green-400" />
                    News & Media
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Global news feeds, social media signals, and broadcast monitoring
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Database className="w-4 h-4 text-purple-400" />
                    Historical Data
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Long-term trend analysis with data going back multiple years
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Eye className="w-4 h-4 text-orange-400" />
                    Custom Sources
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Extensible architecture for adding new data sources and APIs
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Processing Pipeline */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('processing')}
          >
            <div className="flex items-center gap-3">
              <Cpu className="w-5 h-5 text-vanguard-400" />
              <span className="font-medium">Data Processing Pipeline</span>
            </div>
            {expandedSections.has('processing') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('processing') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <div className="space-y-4">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-500/20 rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-blue-400">1</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Data Collection</h4>
                    <p className="text-sm text-muted-foreground">
                      Continuous ingestion from multiple sources with automatic retry logic and error handling
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-green-400">2</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Normalization & Storage</h4>
                    <p className="text-sm text-muted-foreground">
                      Data is standardized, deduplicated, and stored in time-series databases for efficient querying
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-purple-400">3</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Analysis & Detection</h4>
                    <p className="text-sm text-muted-foreground">
                      Multiple algorithms analyze patterns, detect anomalies, and identify emerging trends
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-orange-500/20 rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-orange-400">4</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Alert Generation</h4>
                    <p className="text-sm text-muted-foreground">
                      Automated alerts triggered based on configurable rules and risk thresholds
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Prediction Engine */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('prediction')}
          >
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-vanguard-400" />
              <span className="font-medium">Prediction & Forecasting</span>
            </div>
            {expandedSections.has('prediction') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('prediction') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                The prediction engine uses multiple statistical and machine learning algorithms to forecast trend development.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">ARIMA</h4>
                  <p className="text-sm text-muted-foreground">
                    AutoRegressive Integrated Moving Average for stationary time series
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Exponential Smoothing</h4>
                  <p className="text-sm text-muted-foreground">
                    Holt-Winters method for trends with seasonal patterns
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-purple-400">Linear Regression</h4>
                  <p className="text-sm text-muted-foreground">
                    Simple linear models for clear trend patterns
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Ensemble Methods</h4>
                  <p className="text-sm text-muted-foreground">
                    Combines multiple algorithms for improved accuracy
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Alert System */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('alerts')}
          >
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-vanguard-400" />
              <span className="font-medium">Alert System & Notifications</span>
            </div>
            {expandedSections.has('alerts') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('alerts') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Configurable alert rules trigger notifications through multiple channels when risk thresholds are exceeded.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-red-400" />
                    Threshold Alerts
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Triggered when trend values exceed predefined limits
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-yellow-400" />
                    Velocity Alerts
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Detect rapid changes in trend momentum
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Zap className="w-4 h-4 text-blue-400" />
                    Anomaly Detection
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Statistical outliers and unusual patterns
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Clock className="w-4 h-4 text-green-400" />
                    Scheduled Reports
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Automated PDF reports and data exports
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Real-time Features */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('realtime')}
          >
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-vanguard-400" />
              <span className="font-medium">Real-time Monitoring</span>
            </div>
            {expandedSections.has('realtime') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('realtime') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                WebSocket connections provide real-time updates and live data streaming for immediate awareness of emerging trends.
              </p>

              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span className="text-sm">Live trend updates every 15 minutes</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                  <span className="text-sm">Real-time alert notifications</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
                  <span className="text-sm">Live news feed integration</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-orange-400 rounded-full animate-pulse"></div>
                  <span className="text-sm">Dashboard auto-refresh capabilities</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Trading Agent System */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <Brain className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-semibold">AI Trading Agent System</h2>
        </div>

        {/* Trading Overview */}
        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('trading-overview')}
          >
            <div className="flex items-center gap-3">
              <DollarSign className="w-5 h-5 text-green-400" />
              <span className="font-medium">AI-Powered Trading Integration</span>
            </div>
            {expandedSections.has('trading-overview') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('trading-overview') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                The AI Trading Agent integrates anomaly detection signals with automated trading strategies,
                enabling data-driven investment decisions based on emerging market trends and risk patterns.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div className="flex items-start gap-3">
                  <Brain className="w-5 h-5 text-purple-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-purple-400">Signal-Based Trading</h4>
                    <p className="text-sm text-muted-foreground">AI agents execute trades based on anomaly detection signals and trend analysis</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-blue-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-400">Risk Management</h4>
                    <p className="text-sm text-muted-foreground">Advanced risk controls with position sizing, stop-loss, and drawdown limits</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <PieChart className="w-5 h-5 text-green-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-green-400">Portfolio Optimization</h4>
                    <p className="text-sm text-muted-foreground">Dynamic portfolio rebalancing based on market conditions and risk metrics</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Activity className="w-5 h-5 text-orange-400 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-orange-400">Paper Trading</h4>
                    <p className="text-sm text-muted-foreground">Safe simulation environment for testing strategies before live deployment</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Trading Components */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('trading-components')}
          >
            <div className="flex items-center gap-3">
              <Settings className="w-5 h-5 text-green-400" />
              <span className="font-medium">Trading System Components</span>
            </div>
            {expandedSections.has('trading-components') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('trading-components') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h4 className="font-medium flex items-center gap-2">
                    <Database className="w-4 h-4 text-blue-400" />
                    Portfolio Management
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1 ml-6">
                    <li>• Multi-portfolio support with customizable settings</li>
                    <li>• Real-time P&L tracking and performance metrics</li>
                    <li>• Risk limits (position size, drawdown, daily loss)</li>
                    <li>• Currency and margin trading options</li>
                  </ul>
                </div>

                <div className="space-y-4">
                  <h4 className="font-medium flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-green-400" />
                    Order Execution
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1 ml-6">
                    <li>• Market, limit, and stop order types</li>
                    <li>• Automated order routing and execution</li>
                    <li>• Order status tracking and lifecycle management</li>
                    <li>• External broker API integration ready</li>
                  </ul>
                </div>

                <div className="space-y-4">
                  <h4 className="font-medium flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-purple-400" />
                    Position Analytics
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1 ml-6">
                    <li>• Real-time position valuation and P&L</li>
                    <li>• Average cost and market value tracking</li>
                    <li>• Unrealized and realized gains/losses</li>
                    <li>• Position-level risk metrics</li>
                  </ul>
                </div>

                <div className="space-y-4">
                  <h4 className="font-medium flex items-center gap-2">
                    <Shield className="w-4 h-4 text-red-400" />
                    Risk Controls
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1 ml-6">
                    <li>• Sharpe ratio, Sortino ratio, Value at Risk</li>
                    <li>• Maximum drawdown and volatility limits</li>
                    <li>• Beta correlation and portfolio diversification</li>
                    <li>• Automated risk warnings and alerts</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Advanced AI Features */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <Brain className="w-6 h-6 text-blue-400" />
          <h2 className="text-xl font-semibold">Advanced AI Features</h2>
        </div>

        {/* Correlation Analysis */}
        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('correlation')}
          >
            <div className="flex items-center gap-3">
              <BarChart3 className="w-5 h-5 text-purple-400" />
              <span className="font-medium">Trend Correlation Analysis</span>
            </div>
            {expandedSections.has('correlation') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('correlation') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Advanced correlation algorithms identify relationships between different trends and market signals,
                revealing hidden patterns and interconnected events.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Cross-Market Analysis</h4>
                  <p className="text-sm text-muted-foreground">
                    Correlation between search trends, news sentiment, and market movements
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Geographic Correlations</h4>
                  <p className="text-sm text-muted-foreground">
                    Regional trend patterns and cross-border event propagation
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-purple-400">Semantic Clustering</h4>
                  <p className="text-sm text-muted-foreground">
                    AI-powered grouping of related topics and emerging narratives
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Predictive Relationships</h4>
                  <p className="text-sm text-muted-foreground">
                    Leading indicators and predictive correlation patterns
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Counter-Signal Engine */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('counter-signal')}
          >
            <div className="flex items-center gap-3">
              <Shield className="w-5 h-5 text-red-400" />
              <span className="font-medium">Counter-Signal Engine</span>
            </div>
            {expandedSections.has('counter-signal') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('counter-signal') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Advanced contrarian analysis system that actively searches for disconfirming evidence
                and opposing trends to reduce false positives and improve signal accuracy.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-red-400">Historical Failure Analysis</h4>
                  <p className="text-sm text-muted-foreground">
                    Analyzes past cases where similar signals led to losses, applying confidence penalties
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Pattern Matching</h4>
                  <p className="text-sm text-muted-foreground">
                    Fuzzy string matching and semantic similarity to identify counter-narratives
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-yellow-400">Confidence Modulation</h4>
                  <p className="text-sm text-muted-foreground">
                    Multiplicative confidence penalties (0.3-0.8x) based on counter-evidence strength
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Systematic Skepticism</h4>
                  <p className="text-sm text-muted-foreground">
                    Dramatically reduces false positives through active contrarian analysis
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Narrative Saturation Detector */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('narrative-saturation')}
          >
            <div className="flex items-center gap-3">
              <Radio className="w-5 h-5 text-purple-400" />
              <span className="font-medium">Narrative Saturation Detector</span>
            </div>
            {expandedSections.has('narrative-saturation') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('narrative-saturation') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Measures trend progression from emergence to saturation, detecting when narratives
                become overexposed and retail awareness peaks, enabling optimal entry/exit timing.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Lifecycle Tracking</h4>
                  <p className="text-sm text-muted-foreground">
                    Monitors progression from emergence (low volume) to peak saturation (3σ coverage)
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Retail vs Institutional</h4>
                  <p className="text-sm text-muted-foreground">
                    Separates retail enthusiasm (Google Trends) from institutional positioning (news)
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Echo Chamber Detection</h4>
                  <p className="text-sm text-muted-foreground">
                    Identifies when diversity drops below 40%, signaling potential topping patterns
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-red-400">Size Auto-Reduction</h4>
                  <p className="text-sm text-muted-foreground">
                    Automatically reduces position sizes as saturation increases to avoid peaks
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Signal Quality Features */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('signal-quality')}
          >
            <div className="flex items-center gap-3">
              <Target className="w-5 h-5 text-cyan-400" />
              <span className="font-medium">Signal Quality & "Don't Be Wrong" Features</span>
            </div>
            {expandedSections.has('signal-quality') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('signal-quality') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Advanced signal quality assessment prevents trading on stale or over-hyped signals,
                with half-life tracking and momentum exhaustion detection.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-cyan-400">Signal Decay Tracking</h4>
                  <p className="text-sm text-muted-foreground">
                    Estimates half-life for every signal (3 hours vs 3 days) to prevent late trades
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Momentum Exhaustion</h4>
                  <p className="text-sm text-muted-foreground">
                    Detects when trend momentum peaks and begins to reverse
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Persistence Validation</h4>
                  <p className="text-sm text-muted-foreground">
                    Ensures signals maintain strength over time before triggering trades
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Overconfidence Prevention</h4>
                  <p className="text-sm text-muted-foreground">
                    Reduces position sizes for signals showing early signs of topping
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Decision Transparency & Trust */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <Eye className="w-6 h-6 text-indigo-400" />
          <h2 className="text-xl font-semibold">Decision Transparency & Trust</h2>
        </div>

        {/* Replay Mode */}
        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('replay-mode')}
          >
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-indigo-400" />
              <span className="font-medium">Replay Mode (Post-Mortem Simulator)</span>
            </div>
            {expandedSections.has('replay-mode') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('replay-mode') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Time-travel debugging system that rewinds system state to replay signals as they arrived,
                showing decision-changing factors and enabling model training without financial risk.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Historical Replay</h4>
                  <p className="text-sm text-muted-foreground">
                    Simulate real-time conditions with historical data streams and market states
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Decision Analysis</h4>
                  <p className="text-sm text-muted-foreground">
                    Show factors that would have changed decisions with perfect hindsight
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-purple-400">Model Training</h4>
                  <p className="text-sm text-muted-foreground">
                    Train AI models on historical scenarios without risking real capital
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Audit Trails</h4>
                  <p className="text-sm text-muted-foreground">
                    Complete audit logs for compliance and performance analysis
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Why Not Trade Explanations */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('why-not-trade')}
          >
            <div className="flex items-center gap-3">
              <HelpCircle className="w-5 h-5 text-amber-400" />
              <span className="font-medium">"Why Not Trade?" Explanations</span>
            </div>
            {expandedSections.has('why-not-trade') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('why-not-trade') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                AI provides detailed explanations for non-action decisions, documenting conflicting signals,
                insufficient persistence, and risk constraint violations to build user trust.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-red-400">Conflicting Signals</h4>
                  <p className="text-sm text-muted-foreground">
                    Documents when multiple signals contradict each other
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Risk Constraints</h4>
                  <p className="text-sm text-muted-foreground">
                    Explains when position limits or risk thresholds prevent action
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-yellow-400">Insufficient Persistence</h4>
                  <p className="text-sm text-muted-foreground">
                    Shows when signals fail persistence validation tests
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Responsible AI</h4>
                  <p className="text-sm text-muted-foreground">
                    Builds trust through non-reckless, explainable decision making
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Confidence Decomposition */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('confidence-decomp')}
          >
            <div className="flex items-center gap-3">
              <BarChart3 className="w-5 h-5 text-teal-400" />
              <span className="font-medium">Confidence Decomposition</span>
            </div>
            {expandedSections.has('confidence-decomp') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('confidence-decomp') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Breaks down confidence scores into components: data quality, model agreement,
                historical similarity, and execution environment factors.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Data Quality Score</h4>
                  <p className="text-sm text-muted-foreground">
                    Freshness, source reliability, and cross-validation consistency
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Model Agreement</h4>
                  <p className="text-sm text-muted-foreground">
                    Consensus across multiple detection algorithms
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-purple-400">Historical Similarity</h4>
                  <p className="text-sm text-muted-foreground">
                    Pattern matching against successful past trades
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Execution Environment</h4>
                  <p className="text-sm text-muted-foreground">
                    Market volatility, liquidity, and slippage considerations
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Trading Survival & Capital Protection */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-6 h-6 text-red-500" />
          <h2 className="text-xl font-semibold">Trading Survival & Capital Protection</h2>
        </div>

        {/* Kill-Switches */}
        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('kill-switches')}
          >
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              <span className="font-medium">Kill-Switches Triggered by Signal Behavior</span>
            </div>
            {expandedSections.has('kill-switches') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('kill-switches') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Automatic system pauses triggered by anomaly instability, signal volatility collapse,
                or model disagreement spikes to prevent trading in chaotic "weird world" conditions.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-red-400">Anomaly Instability</h4>
                  <p className="text-sm text-muted-foreground">
                    Detects when anomaly patterns become erratic and unpredictable
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Signal Volatility</h4>
                  <p className="text-sm text-muted-foreground">
                    Monitors for sudden confidence collapses in key signals
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-yellow-400">Model Disagreement</h4>
                  <p className="text-sm text-muted-foreground">
                    Triggers when AI models give conflicting or uncertain signals
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-purple-400">Emergency Pause</h4>
                  <p className="text-sm text-muted-foreground">
                    Automatic system halt during extreme market stress events
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Gradual Autonomy Ramp */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('autonomy-ramp')}
          >
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-green-500" />
              <span className="font-medium">Gradual Autonomy Ramp</span>
            </div>
            {expandedSections.has('autonomy-ramp') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('autonomy-ramp') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Progressive AI autonomy levels from alerts-only (0%) to full independence (100%),
                requiring statistical proof and time stability before unlocking higher levels.
              </p>

              <div className="space-y-4">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-gray-500/20 rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-gray-400">0%</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Alert-Only Mode</h4>
                    <p className="text-sm text-muted-foreground">
                      AI provides signals but requires human approval for all trades
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-500/20 rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-blue-400">10-25%</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Limited Execution</h4>
                    <p className="text-sm text-muted-foreground">
                      AI executes small positions with strict risk limits and human oversight
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-green-400">50%</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Semi-Autonomous</h4>
                    <p className="text-sm text-muted-foreground">
                      AI manages positions with human veto power and periodic reviews
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-purple-400">100%</span>
                  </div>
                  <div>
                    <h4 className="font-medium">Full Autonomy</h4>
                    <p className="text-sm text-muted-foreground">
                      AI operates independently with statistical safeguards and emergency stops
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Capital Memory */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('capital-memory')}
          >
            <div className="flex items-center gap-3">
              <Brain className="w-5 h-5 text-amber-500" />
              <span className="font-medium">Capital Memory & Scar Tissue</span>
            </div>
            {expandedSections.has('capital-memory') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('capital-memory') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                AI learns from past drawdowns and painful market environments, developing "scar tissue"
                that makes it more cautious in similar conditions, mimicking human capital preservation instincts.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-red-400">Drawdown Memory</h4>
                  <p className="text-sm text-muted-foreground">
                    Tracks past maximum drawdowns and reduces exposure in similar regimes
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Lethal Signal Detection</h4>
                  <p className="text-sm text-muted-foreground">
                    Identifies patterns that historically led to significant losses
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-yellow-400">Hesitation in Trauma</h4>
                  <p className="text-sm text-muted-foreground">
                    Applies size reduction and increased caution in previously painful conditions
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Adaptive Learning</h4>
                  <p className="text-sm text-muted-foreground">
                    Continuously updates risk parameters based on capital preservation experience
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Sovereign Autonomy Mode */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <Zap className="w-6 h-6 text-yellow-500" />
          <h2 className="text-xl font-semibold">Sovereign Autonomy Mode (Paper Trading Only)</h2>
        </div>

        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('sovereign-autonomy')}
          >
            <div className="flex items-center gap-3">
              <Brain className="w-5 h-5 text-yellow-500" />
              <span className="font-medium">Full AI Independence in Simulation</span>
            </div>
            {expandedSections.has('sovereign-autonomy') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('sovereign-autonomy') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Experimental mode allowing AI to operate with complete independence in paper trading simulation,
                stress-testing advanced features without financial risk.
              </p>

              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <span className="font-medium text-red-400">Paper Trading Only</span>
                </div>
                <p className="text-sm text-red-300">
                  This mode is strictly for simulation and research. No real money is at risk.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-purple-400">Override All Rules</h4>
                  <p className="text-sm text-muted-foreground">
                    AI can ignore counter-signals, saturation warnings, and kill-switches
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Dynamic Strategies</h4>
                  <p className="text-sm text-muted-foreground">
                    AI switches between momentum, mean-reversion, and arbitrage strategies
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Full Position Control</h4>
                  <p className="text-sm text-muted-foreground">
                    Adjusts sizing, leverage, and allocations without human approval
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Detailed Logging</h4>
                  <p className="text-sm text-muted-foreground">
                    Complete audit trails for replay analysis and learning
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Soft Kill-Switch */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('soft-killswitch')}
          >
            <div className="flex items-center gap-3">
              <Settings className="w-5 h-5 text-cyan-500" />
              <span className="font-medium">Optional Soft Kill-Switch (Simulation Safety)</span>
            </div>
            {expandedSections.has('soft-killswitch') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('soft-killswitch') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Research tool allowing mid-scenario AI freezing for inspection, decision analysis,
                and world-state resets during experimental autonomy sessions.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-cyan-400">Mid-Scenario Pause</h4>
                  <p className="text-sm text-muted-foreground">
                    Freeze AI execution to inspect current decisions and market state
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Decision Inspection</h4>
                  <p className="text-sm text-muted-foreground">
                    Analyze AI reasoning, signal weights, and position calculations
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">World State Reset</h4>
                  <p className="text-sm text-muted-foreground">
                    Reset simulation to initial conditions for scenario re-runs
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Learning Validation</h4>
                  <p className="text-sm text-muted-foreground">
                    Test different decision paths and validate AI learning outcomes
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Future Game-Changing Features */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <Lightbulb className="w-6 h-6 text-emerald-400" />
          <h2 className="text-xl font-semibold">Future Game-Changing Features (12-24 Months)</h2>
        </div>

        {/* Federated Anomaly Learning Network */}
        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('faln')}
          >
            <div className="flex items-center gap-3">
              <Network className="w-5 h-5 text-emerald-400" />
              <span className="font-medium">Federated Anomaly Learning Network (FALN)</span>
            </div>
            {expandedSections.has('faln') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('faln') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Privacy-preserving collaborative AI network where anomaly detectors improve through
                federated learning without sharing sensitive data.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Secure Multi-Party Computation</h4>
                  <p className="text-sm text-muted-foreground">
                    Federated averaging of RL detector weights without data exposure
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Differential Privacy</h4>
                  <p className="text-sm text-muted-foreground">
                    Mathematical privacy guarantees for user data protection
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-purple-400">Network Boost</h4>
                  <p className="text-sm text-muted-foreground">
                    Premium subscription tier with enhanced detection accuracy
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Reliability Monitoring</h4>
                  <p className="text-sm text-muted-foreground">
                    Network health tracking and node participation incentives
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Causal Inference Engine */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('causal-inference')}
          >
            <div className="flex items-center gap-3">
              <Target className="w-5 h-5 text-indigo-400" />
              <span className="font-medium">Causal Inference Engine</span>
            </div>
            {expandedSections.has('causal-inference') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('causal-inference') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Advanced causal discovery algorithms identify true cause-and-effect relationships
                between market variables, enabling root cause attribution for anomaly alerts.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-indigo-400">DoWhy Integration</h4>
                  <p className="text-sm text-muted-foreground">
                    Microsoft's causal inference framework for rigorous analysis
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Root Cause Attribution</h4>
                  <p className="text-sm text-muted-foreground">
                    Identify fundamental drivers behind market anomalies
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Impact Prediction</h4>
                  <p className="text-sm text-muted-foreground">
                    Forecast downstream effects of identified causal relationships
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Causal Visualization</h4>
                  <p className="text-sm text-muted-foreground">
                    Interactive graphs showing causal pathways and relationships
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Satellite Imagery Intelligence */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('satellite-imagery')}
          >
            <div className="flex items-center gap-3">
              <Globe className="w-5 h-5 text-teal-400" />
              <span className="font-medium">Proprietary Satellite Imagery Feed</span>
            </div>
            {expandedSections.has('satellite-imagery') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('satellite-imagery') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Computer vision analysis of satellite imagery for geo-economic intelligence,
                detecting supply chain disruptions, agricultural impacts, and infrastructure changes.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-teal-400">Geo-Anomaly Detection</h4>
                  <p className="text-sm text-muted-foreground">
                    AI-powered analysis of satellite images for unusual activity patterns
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Supply Chain Monitoring</h4>
                  <p className="text-sm text-muted-foreground">
                    Track port activity, shipping routes, and logistics infrastructure
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Agricultural Intelligence</h4>
                  <p className="text-sm text-muted-foreground">
                    Monitor crop conditions, weather impacts, and harvest predictions
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Infrastructure Tracking</h4>
                  <p className="text-sm text-muted-foreground">
                    Detect construction, damage, or changes in critical infrastructure
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Multi-Modal Evidence Fusion */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('multimodal-fusion')}
          >
            <div className="flex items-center gap-3">
              <Eye className="w-5 h-5 text-rose-400" />
              <span className="font-medium">Multi-Modal Evidence Fusion</span>
            </div>
            {expandedSections.has('multimodal-fusion') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('multimodal-fusion') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                CLIP-based vision-language models combine text, images, audio, and video data
                for comprehensive anomaly detection across all media types.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-rose-400">CLIP Integration</h4>
                  <p className="text-sm text-muted-foreground">
                    OpenAI's vision-language model for cross-modal understanding
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Attention-Based Weighting</h4>
                  <p className="text-sm text-muted-foreground">
                    Dynamic importance weighting across different data modalities
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Privacy-Preserving Processing</h4>
                  <p className="text-sm text-muted-foreground">
                    On-device processing to protect sensitive media data
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Cross-Modal Anomalies</h4>
                  <p className="text-sm text-muted-foreground">
                    Detect inconsistencies between text descriptions and visual content
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Predictive Event Simulation */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('event-simulation')}
          >
            <div className="flex items-center gap-3">
              <Activity className="w-5 h-5 text-amber-400" />
              <span className="font-medium">Predictive Event Simulation Engine</span>
            </div>
            {expandedSections.has('event-simulation') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('event-simulation') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Agent-based modeling simulates market reactions to anomalies, enabling scenario
                planning, stress testing, and reinforcement learning optimization.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-amber-400">Agent-Based Modeling</h4>
                  <p className="text-sm text-muted-foreground">
                    Mesa framework for simulating market participant behavior
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Scenario Generation</h4>
                  <p className="text-sm text-muted-foreground">
                    Generate thousands of possible market reaction scenarios
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">RL-Optimized Outcomes</h4>
                  <p className="text-sm text-muted-foreground">
                    Train AI agents on simulated market reactions and outcomes
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Stress Testing</h4>
                  <p className="text-sm text-muted-foreground">
                    Test strategies against extreme but plausible market conditions
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Security & Compliance */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-6 h-6 text-slate-400" />
          <h2 className="text-xl font-semibold">Security & Compliance Features</h2>
        </div>

        {/* End-to-End Encryption */}
        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('encryption')}
          >
            <div className="flex items-center gap-3">
              <Lock className="w-5 h-5 text-slate-400" />
              <span className="font-medium">End-to-End Encryption</span>
            </div>
            {expandedSections.has('encryption') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('encryption') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Military-grade encryption for all trading data, communications, and sensitive information
                with zero-knowledge architecture and forward secrecy.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-slate-400">Trading Data Encryption</h4>
                  <p className="text-sm text-muted-foreground">
                    AES-256 encryption for all position, order, and P&L data
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">Communication Security</h4>
                  <p className="text-sm text-muted-foreground">
                    TLS 1.3 with perfect forward secrecy for all API communications
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Zero-Knowledge Proofs</h4>
                  <p className="text-sm text-muted-foreground">
                    Verify data integrity without exposing sensitive information
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Key Management</h4>
                  <p className="text-sm text-muted-foreground">
                    Hardware security modules and automatic key rotation
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Regulatory Compliance */}
        <div className="space-y-4 mt-6">
          <div
            className="flex items-center justify-between p-4 bg-surface-2 rounded-lg cursor-pointer hover:bg-surface-2/80 transition-colors"
            onClick={() => toggleSection('compliance')}
          >
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-emerald-400" />
              <span className="font-medium">Regulatory Compliance & Audit</span>
            </div>
            {expandedSections.has('compliance') ? (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            )}
          </div>

          {expandedSections.has('compliance') && (
            <div className="ml-8 p-4 bg-surface-2/50 rounded-lg space-y-4">
              <p className="text-muted-foreground">
                Comprehensive compliance framework supporting SEC, FINRA, GDPR, and other regulatory
                requirements with automated reporting and audit trails.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-emerald-400">SEC/FINRA Compliance</h4>
                  <p className="text-sm text-muted-foreground">
                    Automated trade reporting and regulatory filing capabilities
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-blue-400">GDPR Compliance</h4>
                  <p className="text-sm text-muted-foreground">
                    Data privacy controls, consent management, and right to erasure
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-green-400">Audit Logging</h4>
                  <p className="text-sm text-muted-foreground">
                    Immutable audit trails for all AI decisions and trading actions
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-orange-400">Multi-Factor Authentication</h4>
                  <p className="text-sm text-muted-foreground">
                    Advanced authentication with biometric and hardware token support
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}