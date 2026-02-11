'use client';

import { useState, useEffect } from 'react';
import { Radio, RefreshCw, AlertTriangle, TrendingUp, Clock, BarChart3, Eye, Users, MessageSquare } from 'lucide-react';
import { api } from '@/lib/api';
import { RefreshButton } from '@/components/Loading';
import { SkeletonCard, Skeleton } from '@/components/Skeleton';
import { useToast } from '@/components/ToastProvider';

interface SaturatedNarrative {
  narrative_id: string;
  title: string;
  saturation_score: number;
  lifecycle_stage: string;
  article_count: number;
  source_count: number;
  time_span_hours: number;
  average_tone: number;
  coverage_intensity: number;
  source_concentration: number;
  repetition_score: number;
  temporal_burstiness: number;
  articles: Array<{
    title: string;
    source: string;
    published_at: string;
    tone: number;
    url: string;
  }>;
}

interface NarrativeResponse {
  saturated_narratives: SaturatedNarrative[];
  total_analyzed: number;
  time_window_hours: number;
  saturation_threshold: number;
  returned_count: number;
}

interface NarrativeCluster {
  id: string;
  representative_title: string;
  article_count: number;
  source_count: number;
  average_tone: number;
  coverage_intensity: number;
  time_span_hours: number;
  source_distribution: Record<string, number>;
  created_at: string;
  articles: Array<{
    title: string;
    source: string;
    published_at: string;
    tone: number;
    url: string;
  }>;
}

interface ClustersResponse {
  clusters: NarrativeCluster[];
  total_articles: number;
  time_window_hours: number;
  min_cluster_size: number;
}

export default function NarrativePage() {
  const { success, error: showError } = useToast();
  const [saturatedNarratives, setSaturatedNarratives] = useState<SaturatedNarrative[]>([]);
  const [allClusters, setAllClusters] = useState<NarrativeCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [timeWindow, setTimeWindow] = useState(24);
  const [saturationThreshold, setSaturationThreshold] = useState(0.7);
  const [viewMode, setViewMode] = useState<'saturated' | 'all'>('saturated');

  const fetchNarratives = async (showRefresh = false) => {
    try {
      if (showRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      if (viewMode === 'saturated') {
        const data: NarrativeResponse = await api.getSaturatedNarratives(timeWindow, saturationThreshold);
        setSaturatedNarratives(data.saturated_narratives);
      } else {
        const data: ClustersResponse = await api.getNarrativeClusters(timeWindow, 2);
        setAllClusters(data.clusters);
      }

      setLastUpdated(new Date());
      if (showRefresh) {
        success('Narratives updated', `Analyzed ${viewMode === 'saturated' ? 'saturated narratives' : 'all clusters'}`);
      }
    } catch (err) {
      console.error('Error fetching narratives:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load narratives';
      setError(errorMessage);
      showError('Failed to load narratives', errorMessage);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchNarratives();
  }, [timeWindow, saturationThreshold, viewMode]);

  const getSaturationColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600 bg-red-50';
    if (score >= 0.6) return 'text-orange-600 bg-orange-50';
    if (score >= 0.4) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
  };

  const getLifecycleColor = (stage: string) => {
    switch (stage) {
      case 'emerging': return 'text-blue-600 bg-blue-50';
      case 'rising': return 'text-cyan-600 bg-cyan-50';
      case 'peak': return 'text-purple-600 bg-purple-50';
      case 'declining': return 'text-gray-600 bg-gray-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const formatTimeSpan = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${Math.round(hours)}h`;
    return `${Math.round(hours / 24)}d`;
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Narrative Analysis</h1>
            <p className="text-gray-600">Detect oversaturated news narratives</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Narrative Analysis</h1>
          <p className="text-gray-600">Detect oversaturated news narratives using BERT-based clustering</p>
        </div>
        <RefreshButton
          onClick={() => fetchNarratives(true)}
          loading={refreshing}
        />
      </div>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">View:</label>
            <select
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value as 'saturated' | 'all')}
              className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="saturated">Saturated Narratives</option>
              <option value="all">All Clusters</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Time Window:</label>
            <select
              value={timeWindow}
              onChange={(e) => setTimeWindow(Number(e.target.value))}
              className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value={6}>6 hours</option>
              <option value={12}>12 hours</option>
              <option value={24}>24 hours</option>
              <option value={48}>48 hours</option>
              <option value={72}>72 hours</option>
            </select>
          </div>

          {viewMode === 'saturated' && (
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">Saturation Threshold:</label>
              <select
                value={saturationThreshold}
                onChange={(e) => setSaturationThreshold(Number(e.target.value))}
                className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value={0.5}>0.5</option>
                <option value={0.6}>0.6</option>
                <option value={0.7}>0.7</option>
                <option value={0.8}>0.8</option>
                <option value={0.9}>0.9</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error loading narratives</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Narratives Grid */}
      {viewMode === 'saturated' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {saturatedNarratives.map((narrative) => (
            <div key={narrative.narrative_id} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                    {narrative.title}
                  </h3>
                  <div className="flex items-center space-x-2 mt-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSaturationColor(narrative.saturation_score)}`}>
                      {narrative.saturation_score.toFixed(2)} saturation
                    </span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getLifecycleColor(narrative.lifecycle_stage)}`}>
                      {narrative.lifecycle_stage}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <div className="flex items-center space-x-1">
                    <Eye className="h-4 w-4" />
                    <span>{narrative.article_count} articles</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Users className="h-4 w-4" />
                    <span>{narrative.source_count} sources</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm text-gray-600">
                  <div className="flex items-center space-x-1">
                    <Clock className="h-4 w-4" />
                    <span>{formatTimeSpan(narrative.time_span_hours)} span</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <BarChart3 className="h-4 w-4" />
                    <span>{narrative.coverage_intensity.toFixed(1)}/hour</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-gray-200">
                  <div className="text-xs text-gray-500 mb-2">Recent Articles:</div>
                  <div className="space-y-1">
                    {narrative.articles.slice(0, 3).map((article, idx) => (
                      <div key={idx} className="text-xs text-gray-600 truncate">
                        {article.source}: {article.title}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {allClusters.map((cluster) => (
            <div key={cluster.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                    {cluster.representative_title}
                  </h3>
                  <div className="flex items-center space-x-2 mt-2">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-gray-600 bg-gray-50">
                      {cluster.article_count} articles
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <div className="flex items-center space-x-1">
                    <Users className="h-4 w-4" />
                    <span>{cluster.source_count} sources</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Clock className="h-4 w-4" />
                    <span>{formatTimeSpan(cluster.time_span_hours)} span</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm text-gray-600">
                  <div className="flex items-center space-x-1">
                    <BarChart3 className="h-4 w-4" />
                    <span>{cluster.coverage_intensity.toFixed(1)}/hour</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <TrendingUp className="h-4 w-4" />
                    <span>{cluster.average_tone.toFixed(2)} tone</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-gray-200">
                  <div className="text-xs text-gray-500 mb-2">Source Distribution:</div>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(cluster.source_distribution).slice(0, 4).map(([source, count]) => (
                      <span key={source} className="inline-flex items-center px-2 py-1 rounded text-xs bg-blue-50 text-blue-700">
                        {source}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {((viewMode === 'saturated' && saturatedNarratives.length === 0) ||
        (viewMode === 'all' && allClusters.length === 0)) && !loading && (
        <div className="text-center py-12">
          <Radio className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No narratives found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {viewMode === 'saturated'
              ? `No saturated narratives detected in the last ${timeWindow} hours.`
              : `No narrative clusters found in the last ${timeWindow} hours.`
            }
          </p>
        </div>
      )}
    </div>
  );
}