'use client';

import { useState, useEffect, useCallback } from 'react';
import { BarChart3, TrendingUp, Target, DollarSign, Clock, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { api, websocketManager } from '@/lib/api';
import {
  AnalyticsPerformance,
  AnalyticsEffectiveness,
  AnalyticsBusinessImpact,
  AnalyticsLifecycle
} from '@/lib/api';
import { SkeletonCard, Skeleton } from '@/components/Skeleton';
import { RefreshButton } from '@/components/Loading';
import { useToast } from '@/components/ToastProvider';

export default function AnalyticsPage() {
  const { success, error: showError } = useToast();
  const [performance, setPerformance] = useState<AnalyticsPerformance | null>(null);
  const [effectiveness, setEffectiveness] = useState<AnalyticsEffectiveness | null>(null);
  const [businessImpact, setBusinessImpact] = useState<AnalyticsBusinessImpact | null>(null);
  const [lifecycle, setLifecycle] = useState<AnalyticsLifecycle | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [timeRange, setTimeRange] = useState(30);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(300); // 5 minutes in seconds
  const [nextRefreshIn, setNextRefreshIn] = useState<number | null>(null);

  const fetchAnalytics = useCallback(async (showRefreshState = false) => {
    try {
      if (showRefreshState) setRefreshing(true);
      else setLoading(true);

      const [perfData, effData, impactData, lifeData] = await Promise.all([
        api.getAnalyticsPerformance(timeRange),
        api.getAnalyticsEffectiveness(timeRange),
        api.getAnalyticsBusinessImpact(timeRange),
        api.getAnalyticsLifecycle(timeRange),
      ]);

      setPerformance(perfData);
      setEffectiveness(effData);
      setBusinessImpact(impactData);
      setLifecycle(lifeData);
      setLastUpdated(new Date());

      if (showRefreshState) {
        success('Analytics updated', 'Latest performance data loaded successfully');
      }
    } catch (err) {
      console.error('Failed to fetch analytics data:', err);
      showError('Failed to load analytics', 'Please check your connection and try again');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [timeRange, success, showError]);

  useEffect(() => {
    fetchAnalytics();

    // Connect to WebSocket for real-time updates
    websocketManager.connect();

    // Listen for analytics updates
    const handleAnalyticsUpdate = (data: any) => {
      console.log('Received analytics update:', data);
      // TODO: Update state with real-time data
      // For now, just refresh the data
      fetchAnalytics(true);
    };

    websocketManager.on('analytics_update', handleAnalyticsUpdate);

    let interval: NodeJS.Timeout | null = null;

    if (autoRefreshInterval > 0) {
      // Auto-refresh with configurable interval
      interval = setInterval(() => {
        fetchAnalytics();
      }, autoRefreshInterval * 1000);
    }

    return () => {
      websocketManager.off('analytics_update', handleAnalyticsUpdate);
      if (interval) clearInterval(interval);
    };
  }, [fetchAnalytics, autoRefreshInterval]);

  // Separate effect for countdown timer
  useEffect(() => {
    if (autoRefreshInterval > 0 && lastUpdated) {
      const countdownInterval = setInterval(() => {
        const elapsed = (Date.now() - lastUpdated.getTime()) / 1000;
        const remaining = Math.max(0, autoRefreshInterval - elapsed);
        setNextRefreshIn(Math.floor(remaining));
      }, 1000);

      return () => clearInterval(countdownInterval);
    } else {
      setNextRefreshIn(null);
    }
  }, [autoRefreshInterval, lastUpdated]);

  const formatLastUpdated = (date: Date | null) => {
    if (!date) return 'Never';
    return date.toLocaleString();
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  if (loading) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">Analytics Dashboard</h1>
            <p className="text-gray-400">Trend performance and business impact metrics</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Analytics Dashboard</h1>
            <p className="text-gray-400">Trend performance and business impact metrics</p>
            <p className="text-sm text-gray-500 mt-1">
              Last updated: {formatLastUpdated(lastUpdated)}
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex flex-col items-end gap-1">
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
              <select
                value={autoRefreshInterval}
                onChange={(e) => setAutoRefreshInterval(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value={30}>Refresh: 30s</option>
                <option value={60}>Refresh: 1m</option>
                <option value={300}>Refresh: 5m</option>
                <option value={600}>Refresh: 10m</option>
                <option value={0}>Manual only</option>
              </select>
            </div>
            <div className="flex flex-col items-center gap-1">
              <RefreshButton
                onClick={() => fetchAnalytics(true)}
                loading={refreshing}
              />
              {nextRefreshIn !== null && autoRefreshInterval > 0 && (
                <span className="text-xs text-gray-500">
                  Next: {Math.floor(nextRefreshIn / 60)}:{(nextRefreshIn % 60).toString().padStart(2, '0')}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Alert Accuracy */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <Target className="w-8 h-8 text-blue-400" />
              <span className={`text-sm font-medium ${
                (performance?.alert_accuracy?.accuracy_rate_percent || 0) >= 80 ? 'text-green-400' :
                (performance?.alert_accuracy?.accuracy_rate_percent || 0) >= 60 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {(performance?.alert_accuracy?.accuracy_rate_percent || 0).toFixed(1)}%
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white mb-1">Alert Accuracy</h3>
            <p className="text-gray-400 text-sm">
              {performance?.alert_accuracy?.confirmed_alerts || 0} confirmed of {performance?.alert_accuracy?.resolved_alerts || 0} resolved
            </p>
          </div>

          {/* Response Time */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <Clock className="w-8 h-8 text-green-400" />
              <span className="text-sm font-medium text-green-400">
                {effectiveness?.response_time_metrics.avg_response_hours.toFixed(1)}h
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white mb-1">Avg Response Time</h3>
            <p className="text-gray-400 text-sm">
              Range: {effectiveness?.response_time_metrics.min_response_hours.toFixed(1)}h - {effectiveness?.response_time_metrics.max_response_hours.toFixed(1)}h
            </p>
          </div>

          {/* ROI */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <DollarSign className={`w-8 h-8 ${
                (businessImpact?.roi_metrics?.roi_percentage || 0) >= 0 ? 'text-green-400' : 'text-red-400'
              }`} />
              <span className={`text-sm font-medium ${
                (businessImpact?.roi_metrics?.roi_percentage || 0) >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {(businessImpact?.roi_metrics?.roi_percentage || 0).toFixed(1)}%
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white mb-1">ROI</h3>
            <p className="text-gray-400 text-sm">
              {formatCurrency(businessImpact?.roi_metrics?.net_roi || 0)} net return
            </p>
          </div>

          {/* Active Trends */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <TrendingUp className="w-8 h-8 text-purple-400" />
              <span className="text-sm font-medium text-purple-400">
                {lifecycle?.trend_health.total_active_trends || 0}
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white mb-1">Active Trends</h3>
            <p className="text-gray-400 text-sm">
              {lifecycle?.lifecycle_stages.emerging || 0} emerging, {lifecycle?.lifecycle_stages.growing || 0} growing
            </p>
          </div>
        </div>

        {/* Detailed Analytics Sections */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Alert Effectiveness */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Alert Effectiveness
            </h3>

            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-300">False Positive Rate</span>
                <span className={`font-medium ${
                  (performance?.alert_accuracy?.false_positive_rate_percent || 0) <= 20 ? 'text-green-400' :
                  (performance?.alert_accuracy?.false_positive_rate_percent || 0) <= 40 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {(performance?.alert_accuracy?.false_positive_rate_percent || 0).toFixed(1)}%
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-gray-300">Resolution Rate</span>
                <span className="font-medium text-blue-400">
                  {(performance?.alert_accuracy?.resolution_rate_percent || 0).toFixed(1)}%
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-gray-300">Avg Confidence</span>
                <span className="font-medium text-purple-400">
                  {((performance?.confidence_metrics?.avg_confidence_all_alerts || 0) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>

          {/* Business Impact */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <DollarSign className="w-5 h-5" />
              Business Impact
            </h3>

            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-300">Investigation Costs</span>
                <span className="font-medium text-red-400">
                  {formatCurrency(businessImpact?.roi_metrics.total_investigation_costs || 0)}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-gray-300">Value Captured</span>
                <span className="font-medium text-green-400">
                  {formatCurrency(businessImpact?.roi_metrics.total_value_captured || 0)}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-gray-300">Efficiency Ratio</span>
                <span className="font-medium text-blue-400">
                  {businessImpact?.roi_metrics.efficiency_ratio.toFixed(2)}x
                </span>
              </div>
            </div>
          </div>

          {/* Trend Lifecycle */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Trend Lifecycle
            </h3>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-300 flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-400 rounded-full"></div>
                  Emerging
                </span>
                <span className="font-medium text-blue-400">
                  {lifecycle?.lifecycle_stages.emerging || 0}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-gray-300 flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                  Growing
                </span>
                <span className="font-medium text-green-400">
                  {lifecycle?.lifecycle_stages.growing || 0}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-gray-300 flex items-center gap-2">
                  <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
                  Peaking
                </span>
                <span className="font-medium text-yellow-400">
                  {lifecycle?.lifecycle_stages.peaking || 0}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-gray-300 flex items-center gap-2">
                  <div className="w-3 h-3 bg-red-400 rounded-full"></div>
                  Declining
                </span>
                <span className="font-medium text-red-400">
                  {lifecycle?.lifecycle_stages.declining || 0}
                </span>
              </div>
            </div>
          </div>

          {/* Severity Analysis */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Severity Analysis
            </h3>

            <div className="space-y-3">
              {effectiveness?.outcome_analysis_by_severity && Object.entries(effectiveness.outcome_analysis_by_severity).map(([severity, data]) => (
                <div key={severity} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300 capitalize font-medium">{severity}</span>
                    <span className="text-sm text-gray-400">
                      {data.confirmation_rate_percent.toFixed(1)}% confirmed
                    </span>
                  </div>
                  <div className="flex gap-1">
                    <div
                      className="h-2 bg-green-500 rounded"
                      style={{ width: `${(data.confirmed / data.total) * 100}%` }}
                      title={`${data.confirmed} confirmed`}
                    ></div>
                    <div
                      className="h-2 bg-red-500 rounded"
                      style={{ width: `${(data.dismissed / data.total) * 100}%` }}
                      title={`${data.dismissed} dismissed`}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}