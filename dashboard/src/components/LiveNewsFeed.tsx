'use client';

import { useState, useEffect } from 'react';
import { Newspaper, ExternalLink, RefreshCw, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { api } from '@/lib/api';

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

interface LiveNewsFeedProps {
  className?: string;
}

export default function LiveNewsFeed({ className = '' }: LiveNewsFeedProps) {
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchNews = async (showRefresh = false) => {
    try {
      if (showRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      const data = await api.getNewsFeed(20);
      setNews(data.articles);
    } catch (err) {
      console.error('Error fetching news:', err);
      setError(err instanceof Error ? err.message : 'Failed to load news');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchNews();
    // Refresh news every 2 minutes for live feed
    const interval = setInterval(() => fetchNews(), 2 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const getToneIcon = (tone: number) => {
    if (tone > 0.1) return <TrendingUp className="w-3 h-3 text-green-400" />;
    if (tone < -0.1) return <TrendingDown className="w-3 h-3 text-red-400" />;
    return <Minus className="w-3 h-3 text-gray-400" />;
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

  return (
    <div className={`enterprise-card p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center">
            <Newspaper className="w-4 h-4 text-orange-400" />
          </div>
          <h3 className="text-sm font-semibold">Live News Feed</h3>
        </div>
        <button
          onClick={() => fetchNews(true)}
          disabled={refreshing}
          className="p-1 rounded-md hover:bg-primary/10 transition-colors disabled:opacity-50"
          title="Refresh news"
        >
          <RefreshCw className={`w-4 h-4 text-muted-foreground ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-3">
        {error ? (
          <div className="text-xs text-red-400 p-2 bg-red-500/10 rounded">
            News unavailable
          </div>
        ) : loading ? (
          // Loading skeletons
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="h-3 bg-surface-2 rounded mb-1"></div>
              <div className="h-2 bg-surface-2 rounded w-2/3"></div>
            </div>
          ))
        ) : news.length === 0 ? (
          <div className="text-xs text-muted-foreground p-2">
            No recent news
          </div>
        ) : (
          news.map((article, index) => (
            <a
              key={index}
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-2 rounded-md hover:bg-primary/5 transition-colors group"
              title={article.title}
            >
              <div className="flex items-start gap-2 mb-1">
                {getToneIcon(article.tone)}
                <div className="text-xs font-medium text-foreground group-hover:text-primary truncate leading-tight flex-1">
                  {article.title}
                </div>
                <ExternalLink className="w-3 h-3 text-muted-foreground group-hover:text-primary flex-shrink-0 mt-0.5" />
              </div>
              <div className="text-[10px] text-muted-foreground ml-5">
                {article.source} • {formatTime(article.published_at)}
              </div>
            </a>
          ))
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-border">
        <a
          href="/news"
          className="text-xs text-primary hover:text-primary/80 transition-colors flex items-center gap-1"
        >
          View full news analysis
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
}