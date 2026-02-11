'use client';

import { Database, Server, Zap, Globe, Shield, BarChart3, Code, Layers, Brain, Cpu } from 'lucide-react';

export default function ArchitectureGuide() {
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <Database className="w-8 h-8 text-cyan-400" />
        <div>
          <h1 className="text-3xl font-bold">System Architecture & Technical Implementation</h1>
          <p className="text-muted-foreground">Complete technical overview of Vanguard Signal's architecture, APIs, and deployment</p>
        </div>
      </div>

      {/* Architecture Overview */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-6">
          <Layers className="w-6 h-6 text-cyan-400" />
          <h2 className="text-xl font-semibold">Architecture Overview</h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div>
            <h3 className="font-semibold mb-4 text-cyan-400">Frontend Layer</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Code className="w-5 h-5 text-cyan-400" />
                <div>
                  <div className="font-medium">Next.js 14</div>
                  <div className="text-sm text-muted-foreground">React 18, TypeScript, TailwindCSS</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <BarChart3 className="w-5 h-5 text-cyan-400" />
                <div>
                  <div className="font-medium">Real-time Dashboard</div>
                  <div className="text-sm text-muted-foreground">WebSocket updates, Recharts visualization</div>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h3 className="font-semibold mb-4 text-green-400">Backend Layer</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Server className="w-5 h-5 text-green-400" />
                <div>
                  <div className="font-medium">FastAPI</div>
                  <div className="text-sm text-muted-foreground">28+ endpoints, async operations</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Zap className="w-5 h-5 text-green-400" />
                <div>
                  <div className="font-medium">Real-time Processing</div>
                  <div className="text-sm text-muted-foreground">WebSocket, background tasks</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Data Sources & Ingestion */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <Globe className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold">Data Sources</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>The system ingests data from multiple sources for comprehensive coverage:</p>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <Globe className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span><strong>Google Trends:</strong> Real-time search interest data</span>
              </li>
              <li className="flex items-start gap-2">
                <Globe className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span><strong>Wikipedia:</strong> Edit activity and page view metrics</span>
              </li>
              <li className="flex items-start gap-2">
                <Globe className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span><strong>Reddit:</strong> Social sentiment and discussion volume</span>
              </li>
              <li className="flex items-start gap-2">
                <Globe className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <span><strong>GDELT:</strong> Global event tracking and media analysis</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <Database className="w-6 h-6 text-purple-400" />
            <h2 className="text-xl font-semibold">Database Schema</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>PostgreSQL with 4 specialized schemas for optimal data organization:</p>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <Database className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
                <span><strong>ingestion.*:</strong> Raw data from all sources</span>
              </li>
              <li className="flex items-start gap-2">
                <Database className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
                <span><strong>signal.*:</strong> Processed signals and anomalies</span>
              </li>
              <li className="flex items-start gap-2">
                <Database className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
                <span><strong>alert.*:</strong> Alert history and user interactions</span>
              </li>
              <li className="flex items-start gap-2">
                <Database className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
                <span><strong>backtest.*:</strong> Historical replay data</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Detection Pipeline */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-4">
          <BarChart3 className="w-6 h-6 text-orange-400" />
          <h2 className="text-xl font-semibold">Detection Pipeline</h2>
        </div>
        <div className="space-y-4">
          <p className="text-muted-foreground">
            Multi-stage anomaly detection combining statistical and semantic analysis:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <div className="text-lg font-bold text-orange-400 mb-1">1</div>
              <h3 className="font-semibold mb-1">STL Decomposition</h3>
              <p className="text-sm text-muted-foreground">Seasonal-trend decomposition</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <div className="text-lg font-bold text-orange-400 mb-1">2</div>
              <h3 className="font-semibold mb-1">Isolation Forest</h3>
              <p className="text-sm text-muted-foreground">Unsupervised anomaly detection</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <div className="text-lg font-bold text-orange-400 mb-1">3</div>
              <h3 className="font-semibold mb-1">CUSUM</h3>
              <p className="text-sm text-muted-foreground">Change point detection</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <div className="text-lg font-bold text-orange-400 mb-1">4</div>
              <h3 className="font-semibold mb-1">Ensemble</h3>
              <p className="text-sm text-muted-foreground">Combined scoring</p>
            </div>
          </div>
          <div className="mt-4 p-4 bg-surface-2 rounded-lg">
            <h4 className="font-semibold mb-2">Semantic Layer:</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• SBERT embeddings for text analysis</li>
              <li>• HDBSCAN clustering for topic modeling</li>
              <li>• Drift detection for semantic shifts</li>
              <li>• Narrative saturation analysis</li>
            </ul>
          </div>
        </div>
      </div>

      {/* API Architecture */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <h2 className="text-xl font-semibold mb-4">API Architecture</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold mb-3 text-green-400">Core Endpoints</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/alerts</code> - Alert management</li>
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/dashboard</code> - Dashboard data</li>
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/evidence</code> - Evidence chains</li>
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/feedback</code> - User feedback</li>
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/sources</code> - Data source status</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-3 text-blue-400">Specialized Endpoints</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/narrative/saturation</code> - Narrative analysis</li>
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/replay</code> - Post-mortem analysis</li>
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/backtest</code> - Historical replay</li>
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/watchlist</code> - Custom monitoring</li>
              <li><code className="bg-surface-2 px-2 py-1 rounded">/api/auth</code> - Authentication</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Deployment & Infrastructure */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="w-6 h-6 text-red-400" />
          <h2 className="text-xl font-semibold">Deployment & Infrastructure</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 className="font-semibold mb-3 text-cyan-400">Development</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Docker Compose for local development</li>
              <li>• SQLite for development database</li>
              <li>• Hot reload for both frontend and backend</li>
              <li>• Integrated testing with pytest</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-3 text-green-400">Production</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• PostgreSQL for production database</li>
              <li>• Redis for caching and sessions</li>
              <li>• Nginx reverse proxy</li>
              <li>• Docker containers for deployment</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-3 text-orange-400">Monitoring</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Prometheus metrics collection</li>
              <li>• Grafana dashboards</li>
              <li>• Structured JSON logging</li>
              <li>• Health check endpoints</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Security & Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <Shield className="w-6 h-6 text-green-400" />
            <h2 className="text-xl font-semibold">Security Features</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                <span>JWT authentication with refresh tokens</span>
              </li>
              <li className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                <span>CORS protection and rate limiting</span>
              </li>
              <li className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                <span>Input validation and sanitization</span>
              </li>
              <li className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                <span>SQL injection prevention with SQLAlchemy</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
          <div className="flex items-center gap-3 mb-4">
            <Zap className="w-6 h-6 text-yellow-400" />
            <h2 className="text-xl font-semibold">Performance Optimization</h2>
          </div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <Zap className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                <span>Async database operations with SQLAlchemy</span>
              </li>
              <li className="flex items-start gap-2">
                <Zap className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                <span>WebSocket for real-time updates</span>
              </li>
              <li className="flex items-start gap-2">
                <Zap className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                <span>Background task processing</span>
              </li>
              <li className="flex items-start gap-2">
                <Zap className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                <span>API response caching and optimization</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Development Workflow */}
      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <h2 className="text-xl font-semibold mb-4">Development Workflow</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <div className="text-lg font-bold text-blue-400 mb-1">1</div>
              <h3 className="font-semibold mb-1">Local Development</h3>
              <p className="text-sm text-muted-foreground">Docker Compose setup</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <div className="text-lg font-bold text-blue-400 mb-1">2</div>
              <h3 className="font-semibold mb-1">Testing</h3>
              <p className="text-sm text-muted-foreground">pytest + integration tests</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <div className="text-lg font-bold text-blue-400 mb-1">3</div>
              <h3 className="font-semibold mb-1">CI/CD</h3>
              <p className="text-sm text-muted-foreground">Automated deployment</p>
            </div>
            <div className="bg-surface-2 rounded-lg p-4 text-center">
              <div className="text-lg font-bold text-blue-400 mb-1">4</div>
              <h3 className="font-semibold mb-1">Monitoring</h3>
              <p className="text-sm text-muted-foreground">Production observability</p>
            </div>
          </div>
        </div>
      </div>

      {/* AI System Guide Section */}
      <div className="bg-gradient-to-r from-purple-400/10 to-cyan-400/10 rounded-xl border border-purple-400/20 p-6">
        <div className="flex items-center gap-3 mb-6">
          <Brain className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-semibold">AI System Technical Guide</h2>
          <span className="text-xs bg-purple-400/20 text-purple-400 px-2 py-1 rounded">AI-Only Content</span>
        </div>

        <div className="space-y-6">
          <div className="bg-surface-1 rounded-lg p-4 border border-purple-400/20">
            <h3 className="font-semibold text-purple-400 mb-3 flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              System Overview for AI Systems
            </h3>
            <div className="text-sm text-muted-foreground space-y-2">
              <p><strong>Architecture:</strong> Real-time anomaly detection system processing 4 data streams (Google Trends, Wikipedia, Reddit, GDELT) with ML-driven ensemble detection.</p>
              <p><strong>Core Components:</strong> 4-stage ML pipeline (STL + IForest + CUSUM + SBERT/HDBSCAN), real-time WebSocket processing, risk management with counter-signal analysis.</p>
              <p><strong>Performance Targets:</strong> API response &lt;200ms, detection accuracy &gt;95%, false positive rate &lt;5%, WebSocket latency &lt;50ms.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-surface-1 rounded-lg p-4 border border-cyan-400/20">
              <h4 className="font-semibold text-cyan-400 mb-2">Machine Learning Components</h4>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li><strong>Ensemble System:</strong> Thompson Sampling (α=0.05, ε=0.1)</li>
                <li><strong>Narrative Detector:</strong> BERT clustering (min_cluster_size=3)</li>
                <li><strong>Counter-Signals:</strong> Semantic similarity (radius=0.3)</li>
                <li><strong>Signal Decay:</strong> Exponential models (half-life categories)</li>
              </ul>
            </div>

            <div className="bg-surface-1 rounded-lg p-4 border border-green-400/20">
              <h4 className="font-semibold text-green-400 mb-2">API Endpoints for AI</h4>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li><code className="bg-surface-2 px-1 rounded">POST /api/ml/retrain</code> - Model updates</li>
                <li><code className="bg-surface-2 px-1 rounded">GET /api/ml/metrics</code> - Performance stats</li>
                <li><code className="bg-surface-2 px-1 rounded">POST /api/ml/weights</code> - Ensemble tuning</li>
                <li><code className="bg-surface-2 px-1 rounded">GET /api/health</code> - System monitoring</li>
              </ul>
            </div>
          </div>

          <div className="bg-surface-1 rounded-lg p-4 border border-orange-400/20">
            <h4 className="font-semibold text-orange-400 mb-3">AI Optimization Strategies</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div className="text-xs">
                <div className="font-medium text-orange-400">Strategy 1: Multi-Modal Correlation</div>
                <div className="text-muted-foreground">Cross-source analysis with Granger causality (30-day windows)</div>
                <div className="text-green-400 mt-1">Expected: 25-35% accuracy improvement</div>
              </div>
              <div className="text-xs">
                <div className="font-medium text-orange-400">Strategy 2: Narrative Positioning</div>
                <div className="text-muted-foreground">BERT lifecycle tracking (saturation threshold 0.7)</div>
                <div className="text-green-400 mt-1">Expected: 50% better timing</div>
              </div>
              <div className="text-xs">
                <div className="font-medium text-orange-400">Strategy 3: Ensemble Weighting</div>
                <div className="text-muted-foreground">Thompson Sampling optimization (α=0.05)</div>
                <div className="text-green-400 mt-1">Expected: 20-30% accuracy boost</div>
              </div>
              <div className="text-xs">
                <div className="font-medium text-orange-400">Strategy 4: Counter-Validation</div>
                <div className="text-muted-foreground">Semantic similarity cascade (confidence ×0.7)</div>
                <div className="text-green-400 mt-1">Expected: 45% FP reduction</div>
              </div>
              <div className="text-xs">
                <div className="font-medium text-orange-400">Strategy 5: Adaptive Thresholding</div>
                <div className="text-muted-foreground">Bayesian updates (α=0.2, 24h windows)</div>
                <div className="text-green-400 mt-1">Expected: 35% volatility adaptation</div>
              </div>
              <div className="text-xs">
                <div className="font-medium text-orange-400">Strategy 6: Temporal Prediction</div>
                <div className="text-muted-foreground">LSTM networks (2-layer, 64 units)</div>
                <div className="text-green-400 mt-1">Expected: 40% persistence accuracy</div>
              </div>
            </div>
          </div>

          <div className="bg-surface-1 rounded-lg p-4 border border-red-400/20">
            <h4 className="font-semibold text-red-400 mb-3">Implementation Priorities</h4>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
              <div>
                <div className="font-medium text-red-400">Week 1-2</div>
                <div className="text-muted-foreground">Multi-Modal Correlation + Counter-Signal Validation</div>
              </div>
              <div>
                <div className="font-medium text-red-400">Month 1</div>
                <div className="text-muted-foreground">Ensemble Weighting + Narrative Positioning</div>
              </div>
              <div>
                <div className="font-medium text-red-400">Month 2-3</div>
                <div className="text-muted-foreground">Temporal Prediction + Cross-Modal Fusion</div>
              </div>
              <div>
                <div className="font-medium text-red-400">Month 3-6</div>
                <div className="text-muted-foreground">Autonomous Risk Management + Predictive Maintenance</div>
              </div>
            </div>
          </div>

          <div className="bg-surface-1 rounded-lg p-4 border border-blue-400/20">
            <h4 className="font-semibold text-blue-400 mb-3">Performance Metrics Targets</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div className="text-center">
                <div className="text-lg font-bold text-blue-400">95%</div>
                <div className="text-muted-foreground">Signal Accuracy</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-blue-400">90%</div>
                <div className="text-muted-foreground">Precision</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-blue-400">85%</div>
                <div className="text-muted-foreground">Recall</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-blue-400">2.0</div>
                <div className="text-muted-foreground">Sharpe Ratio</div>
              </div>
            </div>
          </div>

          <div className="bg-surface-1 rounded-lg p-4 border border-yellow-400/20">
            <h4 className="font-semibold text-yellow-400 mb-3">System Constraints & Limits</h4>
            <ul className="text-xs text-muted-foreground space-y-1">
              <li><strong>API Rate Limits:</strong> Respect source-specific limits (Google Trends, GDELT, etc.)</li>
              <li><strong>Memory Usage:</strong> Monitor for leaks in long-running background processes</li>
              <li><strong>Database Connections:</strong> Max 20 concurrent async connections</li>
              <li><strong>WebSocket:</strong> Automatic reconnection with 30s timeout</li>
              <li><strong>Model Updates:</strong> Balance accuracy vs computational cost</li>
            </ul>
          </div>

          <div className="bg-gradient-to-r from-red-400/10 to-orange-400/10 rounded-lg p-4 border border-red-400/20">
            <h4 className="font-semibold text-red-400 mb-3">Emergency Procedures</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div>
                <div className="font-medium text-red-400">Warning Level (2σ)</div>
                <div className="text-muted-foreground">Reduce position sizes by 25%</div>
              </div>
              <div>
                <div className="font-medium text-red-400">Pause Level (3σ)</div>
                <div className="text-muted-foreground">Complete halt with 50% reduction</div>
              </div>
              <div>
                <div className="font-medium text-red-400">Emergency Level (4σ)</div>
                <div className="text-muted-foreground">Full system shutdown</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}