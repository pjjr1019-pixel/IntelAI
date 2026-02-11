'use client';

import { useEffect, useState, useMemo } from 'react';
import { RefreshCw, BarChart3, Zap, Star, Filter, TrendingUp, TrendingDown, Search } from 'lucide-react';
import { SkeletonCard, SkeletonTable } from '../../components/Skeleton';

interface TrendData {
  keyword: string;
  interest: number;
  change: number;
  timestamp: string;
  velocity?: number; // rate of change
  popularity?: number; // overall score
}

type FilterType = 'volume' | 'velocity' | 'popularity';

export default function SourcesPage() {
  const [trends, setTrends] = useState<TrendData[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  
  // Filter states
  const [volumeFilter, setVolumeFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [velocityFilter, setVelocityFilter] = useState<'all' | 'rising' | 'falling' | 'stable'>('all');
  const [popularityFilter, setPopularityFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [sortBy, setSortBy] = useState<FilterType>('volume');

  const fetchTrends = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/sources/google-trends/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keywords: searchTerm || 'artificial intelligence' }),
      });
      const data = await response.json();
      // Enhance data with computed fields
      const enhancedTrends = (data.trends || []).map((trend: any) => ({
        ...trend,
        velocity: Math.abs(trend.change), // absolute change as velocity
        popularity: trend.interest + Math.abs(trend.change) * 10, // combined score
      }));
      setTrends(enhancedTrends);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch trends:', error);
    }
    setLoading(false);
  };

  // Filtered and sorted trends
  const filteredTrends = useMemo(() => {
    let filtered = trends.filter(trend => {
      // Volume filter
      if (volumeFilter !== 'all') {
        const volume = trend.interest;
        if (volumeFilter === 'high' && volume < 70) return false;
        if (volumeFilter === 'medium' && (volume < 40 || volume >= 70)) return false;
        if (volumeFilter === 'low' && volume >= 40) return false;
      }

      // Velocity filter
      if (velocityFilter !== 'all') {
        if (velocityFilter === 'rising' && trend.change <= 0) return false;
        if (velocityFilter === 'falling' && trend.change >= 0) return false;
        if (velocityFilter === 'stable' && Math.abs(trend.change) > 10) return false;
      }

      // Popularity filter
      if (popularityFilter !== 'all') {
        const pop = trend.popularity || 0;
        if (popularityFilter === 'high' && pop < 100) return false;
        if (popularityFilter === 'medium' && (pop < 50 || pop >= 100)) return false;
        if (popularityFilter === 'low' && pop >= 50) return false;
      }

      return true;
    });

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'volume':
          return b.interest - a.interest;
        case 'velocity':
          return (b.velocity || 0) - (a.velocity || 0);
        case 'popularity':
          return (b.popularity || 0) - (a.popularity || 0);
        default:
          return 0;
      }
    });

    return filtered;
  }, [trends, volumeFilter, velocityFilter, popularityFilter, sortBy]);

  useEffect(() => {
    fetchTrends();
    const interval = setInterval(fetchTrends, 30000);
    return () => clearInterval(interval);
  }, [searchTerm]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Sources</h1>
      </div>

      <div className="bg-surface-1 p-6 rounded-xl border border-white/[0.06]">
        <h2 className="text-xl font-semibold mb-4">Google Trends</h2>

        <div className="flex gap-4 mb-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Enter keywords (comma separated)"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 bg-surface-2 border border-white/[0.06] rounded-lg focus:outline-none focus:border-vanguard-400"
            />
          </div>
          <button
            onClick={fetchTrends}
            disabled={loading}
            className="px-4 py-2 bg-vanguard-600 hover:bg-vanguard-700 disabled:opacity-50 rounded-lg flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {lastUpdate && (
          <p className="text-sm text-muted-foreground mb-4">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </p>
        )}

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium mb-2 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Volume
            </label>
            <select
              value={volumeFilter}
              onChange={(e) => setVolumeFilter(e.target.value as any)}
              className="w-full px-3 py-2 bg-surface-2 border border-white/[0.06] rounded-lg focus:outline-none focus:border-vanguard-400"
            >
              <option value="all">All</option>
              <option value="high">High (70+)</option>
              <option value="medium">Medium (40-69)</option>
              <option value="low">Low (0-39)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2 flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Velocity
            </label>
            <select
              value={velocityFilter}
              onChange={(e) => setVelocityFilter(e.target.value as any)}
              className="w-full px-3 py-2 bg-surface-2 border border-white/[0.06] rounded-lg focus:outline-none focus:border-vanguard-400"
            >
              <option value="all">All</option>
              <option value="rising">Rising</option>
              <option value="falling">Falling</option>
              <option value="stable">Stable</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2 flex items-center gap-2">
              <Star className="w-4 h-4" />
              Popularity
            </label>
            <select
              value={popularityFilter}
              onChange={(e) => setPopularityFilter(e.target.value as any)}
              className="w-full px-3 py-2 bg-surface-2 border border-white/[0.06] rounded-lg focus:outline-none focus:border-vanguard-400"
            >
              <option value="all">All</option>
              <option value="high">High (100+)</option>
              <option value="medium">Medium (50-99)</option>
              <option value="low">Low (0-49)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2 flex items-center gap-2">
              <Filter className="w-4 h-4" />
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as FilterType)}
              className="w-full px-3 py-2 bg-surface-2 border border-white/[0.06] rounded-lg focus:outline-none focus:border-vanguard-400"
            >
              <option value="volume">Volume</option>
              <option value="velocity">Velocity</option>
              <option value="popularity">Popularity</option>
            </select>
          </div>
        </div>

        <div className="space-y-4">
          {loading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : filteredTrends.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No trends match the current filters
            </p>
          ) : (
            filteredTrends.map((trend, index) => (
              <div key={index} className="flex items-center justify-between p-4 bg-surface-2 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-vanguard-600/20 rounded-lg flex items-center justify-center">
                    {trend.change > 0 ? (
                      <TrendingUp className="w-5 h-5 text-green-400" />
                    ) : trend.change < 0 ? (
                      <TrendingDown className="w-5 h-5 text-red-400" />
                    ) : (
                      <Search className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-medium">{trend.keyword}</h3>
                    <div className="flex gap-4 text-sm text-muted-foreground">
                      <span>Volume: {trend.interest}</span>
                      <span>Velocity: {trend.velocity?.toFixed(1) || 'N/A'}</span>
                      <span>Popularity: {trend.popularity?.toFixed(1) || 'N/A'}</span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-medium ${
                    trend.change > 0 ? 'text-green-400' :
                    trend.change < 0 ? 'text-red-400' : 'text-gray-400'
                  }`}>
                    {trend.change > 0 ? '+' : ''}{trend.change}%
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Change
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
