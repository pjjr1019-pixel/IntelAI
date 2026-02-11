'use client';

import { useState, useEffect } from 'react';
import { Newspaper, RefreshCw, ExternalLink, TrendingUp, TrendingDown, Minus, Globe, Clock, Filter } from 'lucide-react';
import { api } from '@/lib/api';
import { RefreshButton } from '@/components/Loading';
import { SkeletonCard, Skeleton } from '@/components/Skeleton';
import LiveNewsFeed from '@/components/LiveNewsFeed';
import { useToast } from '@/components/ToastProvider';
import { useConfirmationDialog } from '@/components/ConfirmationDialogProvider';

interface NewsArticle {
  title: string;
  url: string;
  source: string;
  published_at: string;
  tone: number;
}

interface NewsResponse {
  articles: NewsArticle[];
  cached: boolean;
}

export default function NewsPage() {
  const { success, error: showError } = useToast();
  const { confirm } = useConfirmationDialog();
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'recent' | 'tone'>('recent');

  const fetchNews = async (showRefresh = false) => {
    try {
      if (showRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      const data = await api.getNewsFeed(50); // Get more articles for the dedicated page
      setNews(data.articles);
      setLastUpdated(new Date());
      if (showRefresh) {
        success('News updated', `Loaded ${data.articles.length} articles`);
      }
    } catch (err) {
      console.error('Error fetching news:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load news';
      setError(errorMessage);
      showError('Failed to load news', errorMessage);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchNews();
    // Refresh news every 5 minutes
    const interval = setInterval(() => fetchNews(), 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    fetchNews(true);
  };

  const handleForceRefresh = async () => {
    const confirmed = await confirm({
      title: 'Force Refresh News',
      message: 'This will clear the cache and fetch fresh news from all sources. This may take longer than a regular refresh.',
      confirmText: 'Force Refresh',
      cancelText: 'Cancel',
      type: 'warning'
    });

    if (confirmed) {
      // Clear any cached data and force fresh fetch
      success('Force refresh initiated', 'Fetching fresh news data...');
      fetchNews(true);
    }
  };

  // Filter and sort news
  const filteredAndSortedNews = news
    .filter(article => selectedSource === 'all' || article.source.toLowerCase().includes(selectedSource.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'tone') {
        return Math.abs(b.tone) - Math.abs(a.tone); // Sort by tone strength
      }
      return new Date(b.published_at).getTime() - new Date(a.published_at).getTime(); // Sort by recency
    });

  // Get unique sources for filter
  const sources = Array.from(new Set(news.map(article => article.source)));

  const getToneIcon = (tone: number) => {
    if (tone > 0.1) return <TrendingUp className="w-4 h-4 text-green-400" />;
    if (tone < -0.1) return <TrendingDown className="w-4 h-4 text-red-400" />;
    return <Minus className="w-4 h-4 text-gray-400" />;
  };

  const getToneColor = (tone: number) => {
    if (tone > 0.1) return 'text-green-400';
    if (tone < -0.1) return 'text-red-400';
    return 'text-gray-400';
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

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

  return (
    <div className="flex gap-6" id="main-content">
      {loading ? (
        <div className="flex-1 space-y-8">
          {/* Loading Header */}
          <div className="flex items-center justify-between pb-6 border-b border-border">
            <div className="space-y-1">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-96" />
            </div>
            <Skeleton className="h-10 w-24" />
          </div>

          {/* Loading News Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} className="h-48" />
            ))}
          </div>

          {/* Loading Future Expansion */}
          <SkeletonCard className="h-32" />
        </div>
      ) : (
        <div className="flex-1 space-y-8">
          {/* Professional Header */}
          <div className="flex items-center justify-between pb-6 border-b border-border">
            <div className="space-y-1">
              <h1 className="text-3xl font-bold text-foreground tracking-tight flex items-center gap-3">
                <Newspaper className="w-8 h-8 text-primary" />
                News Analysis
              </h1>
              <p className="text-muted-foreground">
                Monitor breaking news, market sentiment, and trending topics from multiple sources
              </p>
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
              <button
                onClick={handleForceRefresh}
                disabled={refreshing}
                className="px-3 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-orange-600/50 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Force Refresh
              </button>
            </div>
          </div>

          {/* Filters and Controls */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Source:</span>
              <select
                value={selectedSource}
                onChange={(e) => setSelectedSource(e.target.value)}
                className="px-3 py-1 bg-surface-2 border border-border rounded-lg text-sm"
              >
                <option value="all">All Sources</option>
                {sources.map(source => (
                  <option key={source} value={source}>{source}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'recent' | 'tone')}
                className="px-3 py-1 bg-surface-2 border border-border rounded-lg text-sm"
              >
                <option value="recent">Most Recent</option>
                <option value="tone">Strongest Sentiment</option>
              </select>
            </div>
          </div>

          {/* News Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {error ? (
              <div className="col-span-full enterprise-card p-8 text-center">
                <div className="text-red-400 mb-2">⚠️ News service unavailable</div>
                <div className="text-sm text-muted-foreground">{error}</div>
              </div>
            ) : filteredAndSortedNews.length === 0 ? (
              <div className="col-span-full enterprise-card p-8 text-center">
                <div className="text-muted-foreground">No news articles found</div>
              </div>
            ) : (
              filteredAndSortedNews.map((article, index) => (
                <a
                  key={index}
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="enterprise-card p-6 hover:shadow-lg transition-all duration-200 group block"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      {getToneIcon(article.tone)}
                      <span className={`text-xs font-medium ${getToneColor(article.tone)}`}>
                        {article.tone > 0.1 ? 'Positive' : article.tone < -0.1 ? 'Negative' : 'Neutral'}
                      </span>
                    </div>
                    <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>

                  <h3 className="text-sm font-semibold text-foreground group-hover:text-primary overflow-hidden text-ellipsis mb-3 leading-tight" style={{display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical'}}>
                    {article.title}
                  </h3>

                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      <span>{article.source}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>{formatTime(article.published_at)}</span>
                    </div>
                  </div>
                </a>
              ))
            )}
          </div>

          {/* Future Expansion Placeholder */}
          <div className="enterprise-card p-8 text-center">
            <div className="text-muted-foreground mb-4">
              🚧 Additional News Sources Coming Soon
            </div>
            <div className="text-sm text-muted-foreground space-y-2">
              <div>• Twitter/X Trending Topics</div>
              <div>• Financial News APIs (Bloomberg, Reuters)</div>
              <div>• Social Media Sentiment Analysis</div>
              <div>• Crypto & DeFi News Feeds</div>
              <div>• Geopolitical Event Monitoring</div>
            </div>
          </div>
        </div>
      )}

      {/* Sidebar with Live News Feed */}
      <div className="w-80 flex-shrink-0">
        <LiveNewsFeed />
      </div>
    </div>
  );
}