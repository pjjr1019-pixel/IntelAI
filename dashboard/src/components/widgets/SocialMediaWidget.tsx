'use client';

import React, { useState, useEffect } from 'react';
import { MessageSquare, TrendingUp, Heart, BarChart3 } from 'lucide-react';
import { api, AnalyticsSocialMedia } from '@/lib/api';
import { Skeleton } from '@/components/Skeleton';
import { RefreshButton } from '@/components/Loading';
import { useToast } from '@/components/ToastProvider';

interface SocialMediaWidgetProps {
  className?: string;
}

export default function SocialMediaWidget({ className = '' }: SocialMediaWidgetProps) {
  const { success, error: showError } = useToast();
  const [data, setData] = useState<AnalyticsSocialMedia | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [timeRange, setTimeRange] = useState(7);

  const fetchData = async (showRefreshState = false) => {
    try {
      if (showRefreshState) setRefreshing(true);
      else setLoading(true);

      const result = await api.getAnalyticsSocialMedia(timeRange);
      setData(result);

      if (showRefreshState) {
        success('Social media data updated', 'Latest engagement metrics loaded');
      }
    } catch (err) {
      console.error('Failed to fetch social media data:', err);
      showError('Failed to load social media data', 'Please check your connection');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [timeRange]);

  if (loading) {
    return (
      <div className={`enterprise-card ${className}`}>
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <MessageSquare className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Social Media Analytics</h3>
                <p className="text-sm text-muted-foreground">Engagement and mention trends</p>
              </div>
            </div>
            <Skeleton className="h-8 w-20" />
          </div>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-2 gap-4 mb-6">
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
          </div>
          <Skeleton className="h-32" />
        </div>
      </div>
    );
  }

  return (
    <div className={`enterprise-card ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <MessageSquare className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Social Media Analytics</h3>
              <p className="text-sm text-muted-foreground">Engagement and mention trends</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(Number(e.target.value))}
              className="bg-background border border-border rounded px-2 py-1 text-sm"
            >
              <option value={1}>1 day</option>
              <option value={3}>3 days</option>
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
            </select>
            <RefreshButton onClick={() => fetchData(true)} loading={refreshing} />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {data?.social_sources.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">No social media sources configured</p>
            <p className="text-sm text-muted-foreground mt-1">Configure Reddit or Twitter connectors to see analytics</p>
          </div>
        ) : (
          <>
            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-card/50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-4 h-4 text-green-400" />
                  <span className="text-sm font-medium text-muted-foreground">Total Mentions</span>
                </div>
                <div className="text-2xl font-bold text-foreground">
                  {data?.engagement_metrics.total_mentions.toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">
                  {data?.engagement_metrics.avg_daily_mentions.toFixed(1)} per day
                </div>
              </div>

              <div className="bg-card/50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Heart className="w-4 h-4 text-red-400" />
                  <span className="text-sm font-medium text-muted-foreground">Active Sources</span>
                </div>
                <div className="text-2xl font-bold text-foreground">
                  {data?.social_sources.length}
                </div>
                <div className="text-sm text-muted-foreground">
                  {data?.engagement_metrics.most_active_source || 'N/A'}
                </div>
              </div>
            </div>

            {/* Top Keywords */}
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Top Keywords
              </h4>
              <div className="space-y-2">
                {data?.top_keywords.slice(0, 5).map((keyword, index) => (
                  <div key={keyword.keyword} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs bg-muted px-2 py-1 rounded">
                        #{index + 1}
                      </span>
                      <span className="text-sm font-medium text-foreground">
                        {keyword.keyword}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {keyword.total_mentions} mentions
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Sentiment Distribution */}
            <div>
              <h4 className="text-sm font-semibold text-foreground mb-3">Sentiment Distribution</h4>
              <div className="space-y-2">
                {Object.entries(data?.sentiment_distribution || {}).map(([sentiment, percentage]) => (
                  <div key={sentiment} className="flex items-center gap-3">
                    <div className="w-16 text-sm capitalize text-muted-foreground">
                      {sentiment}
                    </div>
                    <div className="flex-1 bg-muted rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          sentiment === 'positive' ? 'bg-green-500' :
                          sentiment === 'neutral' ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${percentage * 100}%` }}
                      />
                    </div>
                    <div className="w-12 text-sm text-right text-muted-foreground">
                      {(percentage * 100).toFixed(1)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}