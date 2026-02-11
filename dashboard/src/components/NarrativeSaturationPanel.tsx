'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, TrendingUp, Clock, Users, Zap, RefreshCw, Globe, Activity } from 'lucide-react';
import { api } from '@/lib/api';
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

export default function NarrativeSaturationPanel() {
  const [saturatedNarratives, setSaturatedNarratives] = useState<SaturatedNarrative[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { error: showError } = useToast();

  useEffect(() => {
    fetchSaturatedNarratives();
    // Refresh every 5 minutes
    const interval = setInterval(fetchSaturatedNarratives, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchSaturatedNarratives = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getSaturatedNarratives();
      setSaturatedNarratives(data.saturated_narratives || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load narrative data';
      setError(errorMessage);
      showError('Failed to load narratives', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getSaturationColor = (score: number) => {
    if (score >= 0.9) return 'text-red-400 border-red-500/20 bg-red-500/5';
    if (score >= 0.8) return 'text-orange-400 border-orange-500/20 bg-orange-500/5';
    if (score >= 0.7) return 'text-yellow-400 border-yellow-500/20 bg-yellow-500/5';
    return 'text-green-400 border-green-500/20 bg-green-500/5';
  };

  const getLifecycleIcon = (stage: string) => {
    switch (stage) {
      case 'emerging': return <TrendingUp className="w-4 h-4 text-blue-400" />;
      case 'rising': return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'peak': return <Zap className="w-4 h-4 text-yellow-400" />;
      case 'declining': return <TrendingUp className="w-4 h-4 text-red-400 transform rotate-180" />;
      default: return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="enterprise-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Skeleton className="h-6 w-48" />
        </div>
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="enterprise-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <AlertTriangle className="w-6 h-6 text-red-400" />
          <h3 className="text-lg font-semibold">Narrative Saturation</h3>
        </div>
        <div className="text-center py-8">
          <div className="text-red-400 mb-2">⚠️ Service unavailable</div>
          <div className="text-sm text-muted-foreground">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="enterprise-card p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-orange-400" />
          <h3 className="text-lg font-semibold">Narrative Saturation</h3>
          <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-1 rounded-full">
            {saturatedNarratives.length} saturated
          </span>
        </div>
        <button
          onClick={fetchSaturatedNarratives}
          className="text-muted-foreground hover:text-foreground transition-colors"
          title="Refresh narratives"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {saturatedNarratives.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-green-400 mb-2">✅ No saturated narratives detected</div>
          <div className="text-sm text-muted-foreground">
            News coverage appears balanced across topics
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {saturatedNarratives.slice(0, 5).map((narrative) => (
            <div
              key={narrative.narrative_id}
              className={`p-4 rounded-lg border ${getSaturationColor(narrative.saturation_score)}`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    {getLifecycleIcon(narrative.lifecycle_stage)}
                    <span className="text-xs font-medium capitalize">
                      {narrative.lifecycle_stage}
                    </span>
                    <span className="text-xs bg-surface-2 px-2 py-1 rounded">
                      {narrative.saturation_score.toFixed(2)} saturation
                    </span>
                  </div>
                  <h4 className="font-medium text-sm leading-tight mb-2">
                    {narrative.title}
                  </h4>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                <div className="flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  <span>{narrative.article_count} articles</span>
                </div>
                <div className="flex items-center gap-1">
                  <Globe className="w-3 h-3" />
                  <span>{narrative.source_count} sources</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{narrative.time_span_hours.toFixed(1)}h span</span>
                </div>
                <div className="flex items-center gap-1">
                  <Activity className="w-3 h-3" />
                  <span>{narrative.coverage_intensity.toFixed(1)}/h</span>
                </div>
              </div>

              {/* Show top 3 articles */}
              <div className="mt-3 space-y-2">
                {narrative.articles.slice(0, 3).map((article, idx) => (
                  <div key={idx} className="text-xs text-muted-foreground truncate">
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-foreground transition-colors"
                    >
                      {article.source}: {article.title}
                    </a>
                  </div>
                ))}
              </div>

              {narrative.source_concentration > 0.7 && (
                <div className="mt-2 text-xs text-orange-400 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  High source concentration ({(narrative.source_concentration * 100).toFixed(0)}%)
                </div>
              )}
            </div>
          ))}

          {saturatedNarratives.length > 5 && (
            <div className="text-center text-sm text-muted-foreground">
              +{saturatedNarratives.length - 5} more saturated narratives
            </div>
          )}
        </div>
      )}
    </div>
  );
}