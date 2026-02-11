'use client';

import { useState, useEffect } from 'react';
import { Play, Trash2, Eye, Settings } from 'lucide-react';
import { format } from 'date-fns';
import { api } from '@/lib/api';

interface ReplaySession {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  start_time: string;
  end_time: string;
  parameters: Record<string, any>;
  status: 'created' | 'running' | 'completed' | 'failed';
  progress_percentage?: number;
  alerts_generated: number;
  trades_simulated: number;
  key_insights?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface ReplaySnapshot {
  id: string;
  session_id: string;
  snapshot_time: string;
  sequence_number: number;
  active_signals: Array<Record<string, any>>;
  system_parameters: Record<string, any>;
  market_conditions?: Record<string, any>;
  portfolio_state?: Record<string, any>;
}

interface ReplayDecision {
  id: string;
  session_id: string;
  decision_time: string;
  decision_type: string;
  sequence_number: number;
  decision_data: Record<string, any>;
  confidence_score?: number;
  original_alert_id?: string;
  original_trade_id?: string;
  would_have_occurred?: boolean;
  impact_analysis?: Record<string, any>;
}

interface ReplaySignal {
  id: string;
  session_id: string;
  entity_value: string;
  signal_time: string;
  original_scores: Record<string, any>;
  adjusted_scores: Record<string, any>;
  would_trigger_alert: boolean;
  confidence_level: number;
  signal_metadata?: Record<string, any>;
  parameter_sensitivity?: Record<string, any>;
}

interface ReplaySession {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  start_time: string;
  end_time: string;
  parameters: Record<string, any>;
  status: 'created' | 'running' | 'completed' | 'failed';
  progress_percentage?: number;
  alerts_generated: number;
  trades_simulated: number;
  key_insights?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface ReplaySnapshot {
  id: string;
  session_id: string;
  snapshot_time: string;
  sequence_number: number;
  active_signals: Array<Record<string, any>>;
  system_parameters: Record<string, any>;
  market_conditions?: Record<string, any>;
  portfolio_state?: Record<string, any>;
}

interface ReplayDecision {
  id: string;
  session_id: string;
  decision_time: string;
  decision_type: string;
  sequence_number: number;
  decision_data: Record<string, any>;
  confidence_score?: number;
  original_alert_id?: string;
  original_trade_id?: string;
  would_have_occurred?: boolean;
  impact_analysis?: Record<string, any>;
}

interface ReplaySignal {
  id: string;
  session_id: string;
  entity_value: string;
  signal_time: string;
  original_scores: Record<string, any>;
  adjusted_scores: Record<string, any>;
  would_trigger_alert: boolean;
  confidence_level: number;
  signal_metadata?: Record<string, any>;
  parameter_sensitivity?: Record<string, any>;
}

export default function ReplayPage() {
  const [sessions, setSessions] = useState<ReplaySession[]>([]);
  const [selectedSession, setSelectedSession] = useState<ReplaySession | null>(null);
  const [sessionResults, setSessionResults] = useState<{
    session: ReplaySession;
    snapshots: ReplaySnapshot[];
    decisions: ReplayDecision[];
    signals: ReplaySignal[];
  } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'decisions' | 'signals' | 'snapshots'>('overview');

  // Create session form state
  const [sessionName, setSessionName] = useState('');
  const [sessionDescription, setSessionDescription] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [confidenceThreshold, setConfidenceThreshold] = useState('0.7');
  const [detectorWeights, setDetectorWeights] = useState({
    stl: '0.4',
    iforest: '0.3',
    cusum: '0.3'
  });

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const response = await fetch('/api/replay/sessions');
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      console.error('Failed to load replay sessions:', error);
    }
  };

  const createSession = async () => {
    if (!sessionName || !startDate || !endDate) return;

    const parameters = {
      confidence_threshold: parseFloat(confidenceThreshold),
      detector_weights: {
        stl_residual_zscore: parseFloat(detectorWeights.stl),
        iforest_score: parseFloat(detectorWeights.iforest),
        cusum_score: parseFloat(detectorWeights.cusum),
      },
      velocity_score: 0.0, // Phase 2
    };

    try {
      const response = await fetch('/api/replay/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: sessionName,
          description: sessionDescription,
          start_time: new Date(startDate).toISOString(),
          end_time: new Date(endDate).toISOString(),
          parameters,
        }),
      });

      if (response.ok) {
        setShowCreateForm(false);
        setSessionName('');
        setSessionDescription('');
        setStartDate('');
        setEndDate('');
        loadSessions();
      }
    } catch (error) {
      console.error('Failed to create replay session:', error);
    }
  };

  const runSession = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/replay/sessions/${sessionId}/run`, {
        method: 'POST',
      });

      if (response.ok) {
        loadSessions();
      }
    } catch (error) {
      console.error('Failed to run replay session:', error);
    }
  };

  const loadSessionResults = async (session: ReplaySession) => {
    setSelectedSession(session);
    try {
      const response = await fetch(`/api/replay/sessions/${session.id}/results`);
      if (response.ok) {
        const data = await response.json();
        setSessionResults(data);
      }
    } catch (error) {
      console.error('Failed to load session results:', error);
    }
  };

  const deleteSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this replay session?')) return;

    try {
      const response = await fetch(`/api/replay/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadSessions();
        if (selectedSession?.id === sessionId) {
          setSelectedSession(null);
          setSessionResults(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete replay session:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'created': return 'bg-gray-100 text-gray-800';
      case 'running': return 'bg-blue-100 text-blue-800';
      case 'completed': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Replay Mode</h1>
          <p className="text-muted-foreground">
            Post-mortem simulator for debugging and training. Rewind system state to analyze past decisions.
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 flex items-center gap-2 transition-colors"
        >
          <Settings className="w-4 h-4" />
          New Replay Session
        </button>
      </div>

      {showCreateForm && (
        <div className="enterprise-card p-6">
          <h2 className="text-xl font-semibold mb-4">Create Replay Session</h2>
          <p className="text-muted-foreground mb-4">
            Configure parameters for historical analysis and decision replay.
          </p>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Session Name</label>
              <input
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
                placeholder="e.g., Q1 2024 Analysis"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description (Optional)</label>
              <textarea
                value={sessionDescription}
                onChange={(e) => setSessionDescription(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
                placeholder="Purpose of this replay analysis..."
                rows={2}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Start Date</label>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">End Date</label>
              <input
                type="datetime-local"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
              />
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Confidence Threshold</label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2"
            />
            <p className="text-sm text-gray-500 mt-1">
              Minimum confidence score for alerts (0.0-1.0)
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Detector Weights</label>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-xs mb-1">STL Decomposition</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={detectorWeights.stl}
                  onChange={(e) => setDetectorWeights(prev => ({ ...prev, stl: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs mb-1">Isolation Forest</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={detectorWeights.iforest}
                  onChange={(e) => setDetectorWeights(prev => ({ ...prev, iforest: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs mb-1">CUSUM</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={detectorWeights.cusum}
                  onChange={(e) => setDetectorWeights(prev => ({ ...prev, cusum: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={createSession}
              disabled={!sessionName || !startDate || !endDate}
              className="bg-primary text-primary-foreground px-4 py-2 rounded hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground transition-colors"
            >
              Create Session
            </button>
            <button
              onClick={() => setShowCreateForm(false)}
              className="bg-secondary text-secondary-foreground px-4 py-2 rounded hover:bg-secondary/80 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sessions List */}
        <div className="lg:col-span-1">
          <div className="enterprise-card p-6">
            <h2 className="text-xl font-semibold mb-4">Replay Sessions</h2>
            <p className="text-muted-foreground mb-4">Historical analysis sessions</p>

            <div className="space-y-4">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-all duration-200 ${
                    selectedSession?.id === session.id ? 'border-primary bg-primary/5 shadow-sm' : 'border-border hover:border-primary/50 hover:bg-primary/5'
                  }`}
                  onClick={() => loadSessionResults(session)}
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-medium">{session.name}</h3>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(session.status)}`}>
                      {session.status}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mb-2">
                    {session.description || 'No description'}
                  </p>
                  <div className="text-xs text-muted-foreground">
                    {format(new Date(session.start_time), 'MMM dd')} - {format(new Date(session.end_time), 'MMM dd, yyyy')}
                  </div>
                  {session.status === 'running' && session.progress_percentage !== undefined && (
                    <div className="mt-2 bg-muted rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all duration-300"
                        style={{ width: `${session.progress_percentage}%` }}
                      ></div>
                    </div>
                  )}
                  <div className="flex gap-2 mt-3">
                    {session.status === 'created' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); runSession(session.id); }}
                        className="bg-primary text-primary-foreground px-2 py-1 rounded text-sm hover:bg-primary/90 flex items-center gap-1 transition-colors"
                      >
                        <Play className="w-3 h-3" />
                        Run
                      </button>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                      className="bg-destructive text-destructive-foreground px-2 py-1 rounded text-sm hover:bg-destructive/90 transition-colors"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
              {sessions.length === 0 && (
                <p className="text-center text-muted-foreground py-8">
                  No replay sessions yet. Create your first session to get started.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Session Details */}
        <div className="lg:col-span-2">
          {selectedSession && sessionResults ? (
            <div className="enterprise-card">
              {/* Tab Navigation */}
              <div className="border-b border-gray-200">
                <div className="flex">
                  {[
                    { id: 'overview', label: 'Overview' },
                    { id: 'decisions', label: 'Decisions' },
                    { id: 'signals', label: 'Signals' },
                    { id: 'snapshots', label: 'Timeline' }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                        activeTab === tab.id
                          ? 'border-primary text-primary'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tab Content */}
              <div className="p-6">
                {activeTab === 'overview' && (
                  <div>
                    <h2 className="text-xl font-semibold mb-4">{sessionResults.session.name}</h2>
                    <p className="text-gray-600 mb-4">{sessionResults.session.description}</p>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Time Range</label>
                        <p className="text-sm">
                          {format(new Date(sessionResults.session.start_time), 'PPP')} -
                          {format(new Date(sessionResults.session.end_time), 'PPP')}
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Status</label>
                        <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${getStatusColor(sessionResults.session.status)}`}>
                          {sessionResults.session.status}
                        </span>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Alerts Generated</label>
                        <p className="text-2xl font-bold">{sessionResults.session.alerts_generated}</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Trades Simulated</label>
                        <p className="text-2xl font-bold">{sessionResults.session.trades_simulated}</p>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'decisions' && (
                  <div>
                    <h2 className="text-lg font-semibold mb-4">Replay Decisions</h2>
                    <p className="text-gray-600 mb-4">
                      Key decisions made during the replay period
                    </p>

                    <div className="space-y-4">
                      {sessionResults.decisions.slice(0, 10).map((decision) => (
                        <div key={decision.id} className="border border-gray-200 rounded-lg p-4">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="font-medium">{decision.decision_type}</h4>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              decision.would_have_occurred ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {decision.would_have_occurred ? 'Would Occur' : 'Would Not Occur'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">
                            {format(new Date(decision.decision_time), 'PPP p')}
                          </p>
                          {decision.confidence_score && (
                            <p className="text-sm">Confidence: {(decision.confidence_score * 100).toFixed(1)}%</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeTab === 'signals' && (
                  <div>
                    <h2 className="text-lg font-semibold mb-4">Signal Analysis</h2>
                    <p className="text-gray-600 mb-4">
                      Signals processed during replay with parameter adjustments
                    </p>

                    <div className="space-y-4">
                      {sessionResults.signals.slice(0, 10).map((signal) => (
                        <div key={signal.id} className="border border-gray-200 rounded-lg p-4">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="font-medium">{signal.entity_value}</h4>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              signal.would_trigger_alert ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                            }`}>
                              {signal.would_trigger_alert ? 'Alert Triggered' : 'No Alert'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">
                            {format(new Date(signal.signal_time), 'PPP p')}
                          </p>
                          <p className="text-sm">Confidence: {(signal.confidence_level * 100).toFixed(1)}%</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeTab === 'snapshots' && (
                  <div>
                    <h2 className="text-lg font-semibold mb-4">System Timeline</h2>
                    <p className="text-gray-600 mb-4">
                      System state snapshots throughout the replay period
                    </p>

                    <div className="space-y-4">
                      {sessionResults.snapshots.map((snapshot) => (
                        <div key={snapshot.id} className="border border-gray-200 rounded-lg p-4">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="font-medium">Snapshot #{snapshot.sequence_number}</h4>
                            <span className="text-sm text-gray-500">
                              {format(new Date(snapshot.snapshot_time), 'PPP p')}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <label className="block text-xs font-medium text-gray-700">Active Signals</label>
                              <p>{snapshot.active_signals.length} signals</p>
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-700">System Parameters</label>
                              <p>{Object.keys(snapshot.system_parameters).length} parameters</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="enterprise-card p-12 text-center">
              <Eye className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium mb-2">Select a Replay Session</h3>
              <p className="text-muted-foreground">
                Choose a session from the list to view detailed results and analysis.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}