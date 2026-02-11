'use client';

import { useState, useEffect, useCallback } from 'react';
import { Activity, RefreshCw, AlertTriangle, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';
import { DashboardOverview } from '@/lib/api';
import { SkeletonCard, Skeleton } from '@/components/Skeleton';
import { RefreshButton } from '@/components/Loading';
import { useToast } from '@/components/ToastProvider';
import NarrativeSaturationPanel from '@/components/NarrativeSaturationPanel';

export default function Dashboard() {
  const { success, error: showError } = useToast();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchOverview = useCallback(async (showRefreshState = false) => {
    try {
      if (showRefreshState) setRefreshing(true);
      else setLoading(true);

      const data = await api.getDashboardOverview();
      setOverview(data);
      setLastUpdated(new Date());
      if (showRefreshState) {
        success('Dashboard updated', 'Latest data loaded successfully');
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      showError('Failed to load dashboard', 'Please check your connection and try again');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();

    // Auto-refresh every 60 seconds
    const interval = setInterval(() => {
      fetchOverview();
    }, 60000);

    return () => clearInterval(interval);
  }, [fetchOverview]);

  const formatLastUpdated = (date: Date | null) => {
    if (!date) return 'Never';
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMinutes / 60);

    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  const handleRefresh = () => {
    fetchOverview(true);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-48 mb-2" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-10 w-24" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonCard className="h-80" />
          <SkeletonCard className="h-80" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8" id="main-content">
      {/* Professional Header */}
      <div className="flex items-center justify-between pb-6 border-b border-border">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold text-foreground tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Monitor your signals and analyze trends in real-time</p>
          {lastUpdated && (
            <p className="text-xs text-muted-foreground">Last updated: {formatLastUpdated(lastUpdated)}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <RefreshButton
            onClick={handleRefresh}
            loading={refreshing}
            size="sm"
            className="enterprise-card"
          />
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="md:col-span-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Status Cards */}
            <div className="enterprise-card p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-green-100 dark:bg-green-900/20">
                  <Activity className="w-6 h-6 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">System Status</p>
                  <p className="text-lg font-semibold text-green-600 dark:text-green-400">Operational</p>
                </div>
              </div>
            </div>

            <div className="enterprise-card p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-blue-100 dark:bg-blue-900/20">
                  <RefreshCw className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Last Updated</p>
                  <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">Just now</p>
                </div>
              </div>
            </div>

            <div className="enterprise-card p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-orange-100 dark:bg-orange-900/20">
                  <AlertTriangle className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Active Alerts</p>
                  <p className="text-lg font-semibold text-orange-600 dark:text-orange-400">
                    {overview?.active_alerts || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="enterprise-card p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-purple-100 dark:bg-purple-900/20">
                  <TrendingUp className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Signals Today</p>
                  <p className="text-lg font-semibold text-purple-600 dark:text-purple-400">
                    {overview?.alerts_24h || 0}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Narrative Saturation Analysis */}
      <NarrativeSaturationPanel />
    </div>
  );
}