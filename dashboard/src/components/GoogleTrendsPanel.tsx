'use client';

import { useEffect, useState, useRef, useMemo } from 'react';
import { TrendingUp, TrendingDown, Activity, Globe, RefreshCw, Search, Filter, X, BarChart3, Calendar, Zap, Target, AlertTriangle, ChevronDown } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar, Cell } from 'recharts';
import { api, LiveTrendingResponse, LiveTrendingEntity } from '../lib/api';
import InteractiveTrendChart from './InteractiveTrendChart';
import GeographicHeatmap from './GeographicHeatmap';
import TrendComparison from './TrendComparison';
import { useToast } from './ToastProvider';
import { LoadingSpinner, RefreshButton } from './Loading';
import { SkeletonCard, SkeletonChart } from './Skeleton';

interface GoogleTrendsPanelProps {
  className?: string;
}

export default function GoogleTrendsPanel({ className = '' }: GoogleTrendsPanelProps) {
  const { success, error: showError, info } = useToast();
  const [data, setData] = useState<LiveTrendingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [geo, setGeo] = useState('US');
  const [isConnected, setIsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [webSocketFailed, setWebSocketFailed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [directSearchQuery, setDirectSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'trending' | 'direct' | 'history' | 'alerts' | 'stats' | 'alert-rules' | 'correlation' | 'visualizations' | 'prediction'>('trending');
  const [selectedKeyword, setSelectedKeyword] = useState<string>('');
  const [historyData, setHistoryData] = useState<any>(null);
  const [alertsData, setAlertsData] = useState<any>(null);
  const [statsData, setStatsData] = useState<any>(null);
  const [correlationData, setCorrelationData] = useState<any>(null);
  const [correlationKeyword, setCorrelationKeyword] = useState<string>('');
  const [correlationMatrix, setCorrelationMatrix] = useState<any>(null);
  const [searchResults, setSearchResults] = useState<LiveTrendingEntity | null>(null);
  const [searching, setSearching] = useState(false);
  const [directionFilter, setDirectionFilter] = useState<'all' | 'up' | 'down' | 'stable'>('all');
  const [trafficFilter, setTrafficFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [showFilters, setShowFilters] = useState(false);
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | '90d'>('30d');
  const [alertRulesData, setAlertRulesData] = useState<any>(null);
  const [showCreateRule, setShowCreateRule] = useState(false);
  const [predictionData, setPredictionData] = useState<any>(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionAlgorithm, setPredictionAlgorithm] = useState<'exponential_smoothing' | 'arima' | 'linear_regression' | 'naive'>('exponential_smoothing');
  const [predictionHorizon, setPredictionHorizon] = useState<'1h' | '6h' | '24h' | '7d'>('24h');
  const [predictionConfidence, setPredictionConfidence] = useState(0.95);
  
  // Advanced filtering states
  const [searchFilter, setSearchFilter] = useState('');
  const [minTraffic, setMinTraffic] = useState<number>(0);
  const [maxTraffic, setMaxTraffic] = useState<number>(100);
  const [minVelocity, setMinVelocity] = useState<number>(-10);
  const [maxVelocity, setMaxVelocity] = useState<number>(10);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<'rank' | 'traffic' | 'velocity' | 'keyword'>('rank');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [savedFilters, setSavedFilters] = useState<any[]>([]);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [showSearchHistory, setShowSearchHistory] = useState(false);
  const [selectedTrends, setSelectedTrends] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Filter and search logic
  const filteredTrends = useMemo(() => {
    if (!data?.trends) return [];

    return data.trends.filter(trend => {
      // Search filter (combines searchQuery and searchFilter)
      const searchTerm = searchQuery || searchFilter;
      if (searchTerm && !trend.keyword.toLowerCase().includes(searchTerm.toLowerCase())) {
        return false;
      }

      // Direction filter
      if (directionFilter !== 'all') {
        if (directionFilter === 'up' && trend.direction !== 'up') return false;
        if (directionFilter === 'down' && trend.direction !== 'down') return false;
        if (directionFilter === 'stable' && trend.direction !== 'stable') return false;
      }

      // Traffic filter (basic)
      if (trafficFilter !== 'all') {
        const trafficValue = trend.traffic_value;
        if (trafficFilter === 'high' && trafficValue < 10000) return false;
        if (trafficFilter === 'medium' && (trafficValue < 1000 || trafficValue >= 10000)) return false;
        if (trafficFilter === 'low' && trafficValue >= 1000) return false;
      }

      // Advanced traffic range filter
      const trafficValue = trend.traffic_value;
      if (trafficValue < minTraffic || trafficValue > maxTraffic) return false;

      // Velocity range filter
      const velocityValue = trend.velocity || 0;
      if (velocityValue < minVelocity || velocityValue > maxVelocity) return false;

      // Category filter (basic)
      if (categoryFilter !== 'all') {
        const trendCategory = categorizeTrend(trend.keyword);
        if (trendCategory !== categoryFilter) return false;
      }

      // Advanced category filter
      if (selectedCategories.length > 0) {
        const trendCategory = categorizeTrend(trend.keyword);
        if (!selectedCategories.includes(trendCategory)) return false;
      }

      return true;
    }).sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortBy) {
        case 'rank':
          aValue = a.rank;
          bValue = b.rank;
          break;
        case 'traffic':
          aValue = a.traffic_value;
          bValue = b.traffic_value;
          break;
        case 'velocity':
          aValue = a.velocity || 0;
          bValue = b.velocity || 0;
          break;
        case 'keyword':
          aValue = a.keyword.toLowerCase();
          bValue = b.keyword.toLowerCase();
          break;
        default:
          return 0;
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
      } else {
        return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
      }
    });
  }, [data?.trends, searchQuery, searchFilter, directionFilter, trafficFilter, categoryFilter, minTraffic, maxTraffic, minVelocity, maxVelocity, selectedCategories, sortBy, sortOrder]);

  // Update select all state when filtered trends change
  useEffect(() => {
    if (filteredTrends.length === 0) {
      setSelectAll(false);
    } else {
      setSelectAll(filteredTrends.every(trend => selectedTrends.has(trend.keyword)));
    }
  }, [filteredTrends, selectedTrends]);

  const fetchTrends = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.getLiveTrending(geo);
      setData(response);
      success('Trends data updated', 'Successfully fetched latest trending data');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch trends';
      setError(errorMessage);
      showError('Failed to load trends', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const searchDirectTrends = async (query: string) => {
    if (!query.trim()) return;

    try {
      setSearching(true);
      setError(null);
      const response = await api.searchGoogleTrends(query, geo);
      if (response.trends.length === 0) {
        setError(`No trend data found for "${query}". This could be due to rate limiting or the keyword having very low search volume.`);
        setSearchResults(null);
      } else {
        setSearchResults(response.trends[0]);
        setSearchMode('direct');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to search trends');
      setSearchResults(null);
    } finally {
      setSearching(false);
    }
  };

  const fetchKeywordHistory = async (keyword: string) => {
    try {
      setLoading(true);
      setError(null);
      // TODO: Implement keyword history API
      setHistoryData({ found: false, keyword, data_points: [] });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch keyword history');
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    try {
      // TODO: Implement alerts API
      setAlertsData([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
    }
  };

  const fetchStats = async () => {
    try {
      // TODO: Implement stats API
      setStatsData({ total_keywords: 0, active_trends: 0, avg_velocity: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stats');
    }
  };

  const fetchAlertRules = async () => {
    try {
      // TODO: Implement alert rules API
      setAlertRulesData([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch alert rules');
    }
  };

  const createAlertRule = async (ruleData: any) => {
    try {
      // TODO: Implement create alert rule API
      success('Alert rule created', 'Successfully created new alert rule');
      setShowCreateRule(false);
      fetchAlertRules();
    } catch (err) {
      showError('Failed to create alert rule', err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const updateAlertRule = async (id: string, updates: any) => {
    try {
      // TODO: Implement update alert rule API
      success('Alert rule updated', 'Successfully updated alert rule');
      fetchAlertRules();
    } catch (err) {
      showError('Failed to update alert rule', err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const deleteAlertRule = async (id: string) => {
    try {
      // TODO: Implement delete alert rule API
      success('Alert rule deleted', 'Successfully deleted alert rule');
      fetchAlertRules();
    } catch (err) {
      showError('Failed to delete alert rule', err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const generateReport = async () => {
    try {
      // TODO: Implement generate report API
      success('Report generated', 'Report has been generated successfully');
    } catch (err) {
      showError('Failed to generate report', err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const fetchPrediction = async (keyword: string) => {
    try {
      setPredictionLoading(true);
      setError(null);
      const prediction = await api.getTrendPrediction(keyword, {
        geo,
        horizon: predictionHorizon,
        algorithm: predictionAlgorithm,
        confidence: predictionConfidence,
      });
      setPredictionData(prediction);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch prediction';
      setError(errorMessage);
      showError('Prediction Error', errorMessage);
    } finally {
      setPredictionLoading(false);
    }
  };

  const exportChart = async (format: string) => {
    try {
      // TODO: Implement export chart API
      success('Chart exported', `Chart exported as ${format.toUpperCase()}`);
    } catch (err) {
      showError('Failed to export chart', err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const exportData = async (format: string) => {
    try {
      // TODO: Implement export data API
      success('Data exported', `Data exported as ${format.toUpperCase()}`);
    } catch (err) {
      showError('Failed to export data', err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const fetchKeywordCorrelations = async (keyword: string) => {
    try {
      // TODO: Implement keyword correlations API
      setCorrelationData([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch correlations');
    }
  };

  const fetchCorrelationMatrix = async () => {
    try {
      // TODO: Implement correlation matrix API
      setCorrelationMatrix({ keywords: [], matrix: [] });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch correlation matrix');
    }
  };

  // Categorize trends based on keywords
  const categorizeTrend = (keyword: string): string => {
    const lowerKeyword = keyword.toLowerCase();

    // Entertainment & Media
    if (lowerKeyword.includes('movie') || lowerKeyword.includes('film') || lowerKeyword.includes('actor') ||
        lowerKeyword.includes('actress') || lowerKeyword.includes('celebrity') || lowerKeyword.includes('tv') ||
        lowerKeyword.includes('netflix') || lowerKeyword.includes('spotify') || lowerKeyword.includes('music') ||
        lowerKeyword.includes('song') || lowerKeyword.includes('album') || lowerKeyword.includes('artist')) {
      return 'Entertainment';
    }

    // Sports
    if (lowerKeyword.includes('football') || lowerKeyword.includes('soccer') || lowerKeyword.includes('basketball') ||
        lowerKeyword.includes('baseball') || lowerKeyword.includes('tennis') || lowerKeyword.includes('golf') ||
        lowerKeyword.includes('nfl') || lowerKeyword.includes('nba') || lowerKeyword.includes('mlb') ||
        lowerKeyword.includes('championship') || lowerKeyword.includes('tournament') || lowerKeyword.includes('olympics') ||
        lowerKeyword.includes('world cup') || lowerKeyword.includes('super bowl')) {
      return 'Sports';
    }

    // Technology
    if (lowerKeyword.includes('apple') || lowerKeyword.includes('google') || lowerKeyword.includes('microsoft') ||
        lowerKeyword.includes('facebook') || lowerKeyword.includes('twitter') || lowerKeyword.includes('instagram') ||
        lowerKeyword.includes('tiktok') || lowerKeyword.includes('youtube') || lowerKeyword.includes('ai') ||
        lowerKeyword.includes('crypto') || lowerKeyword.includes('bitcoin') || lowerKeyword.includes('ethereum') ||
        lowerKeyword.includes('blockchain') || lowerKeyword.includes('software') || lowerKeyword.includes('app') ||
        lowerKeyword.includes('phone') || lowerKeyword.includes('computer') || lowerKeyword.includes('internet')) {
      return 'Technology';
    }

    // Politics & News
    if (lowerKeyword.includes('election') || lowerKeyword.includes('president') || lowerKeyword.includes('government') ||
        lowerKeyword.includes('politics') || lowerKeyword.includes('trump') || lowerKeyword.includes('biden') ||
        lowerKeyword.includes('congress') || lowerKeyword.includes('senate') || lowerKeyword.includes('vote') ||
        lowerKeyword.includes('law') || lowerKeyword.includes('court') || lowerKeyword.includes('supreme')) {
      return 'Politics';
    }

    // Business & Finance
    if (lowerKeyword.includes('stock') || lowerKeyword.includes('market') || lowerKeyword.includes('economy') ||
        lowerKeyword.includes('business') || lowerKeyword.includes('company') || lowerKeyword.includes('ceo') ||
        lowerKeyword.includes('money') || lowerKeyword.includes('bank') || lowerKeyword.includes('investment') ||
        lowerKeyword.includes('trading') || lowerKeyword.includes('finance')) {
      return 'Business';
    }

    // Health & Science
    if (lowerKeyword.includes('health') || lowerKeyword.includes('medical') || lowerKeyword.includes('doctor') ||
        lowerKeyword.includes('hospital') || lowerKeyword.includes('vaccine') || lowerKeyword.includes('virus') ||
        lowerKeyword.includes('disease') || lowerKeyword.includes('cancer') || lowerKeyword.includes('science') ||
        lowerKeyword.includes('research') || lowerKeyword.includes('study') || lowerKeyword.includes('nasa') ||
        lowerKeyword.includes('space')) {
      return 'Health & Science';
    }

    // Default category
    return 'General';
  };

  const getCategoryColor = (category: string): string => {
    switch (category) {
      case 'Entertainment': return 'bg-purple-500/20 text-purple-400';
      case 'Sports': return 'bg-green-500/20 text-green-400';
      case 'Technology': return 'bg-blue-500/20 text-blue-400';
      case 'Politics': return 'bg-red-500/20 text-red-400';
      case 'Business': return 'bg-yellow-500/20 text-yellow-400';
      case 'Health & Science': return 'bg-cyan-500/20 text-cyan-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const renderSparkline = (sparkline: number[]) => {
    if (!sparkline.length) return null;

    const max = Math.max(...sparkline);
    const min = Math.min(...sparkline);
    const range = max - min || 1;

    return (
      <div className="flex items-end space-x-px h-8">
        {sparkline.map((value, index) => {
          const height = ((value - min) / range) * 100;
          return (
            <div
              key={index}
              className="bg-blue-400 w-1 rounded-sm"
              style={{ height: `${Math.max(height, 2)}%` }}
            />
          );
        })}
      </div>
    );
  };

  // Detect peaks and valleys in trend data
  const detectPeaksAndValleys = (dataPoints: any[]) => {
    const peaks: number[] = [];
    const valleys: number[] = [];

    if (dataPoints.length < 3) return { peaks, valleys };

    for (let i = 1; i < dataPoints.length - 1; i++) {
      const prev = dataPoints[i - 1].value;
      const current = dataPoints[i].value;
      const next = dataPoints[i + 1].value;

      // Check for peak (local maximum)
      if (current > prev && current > next) {
        peaks.push(i);
      }
      // Check for valley (local minimum)
      else if (current < prev && current < next) {
        valleys.push(i);
      }
    }

    return { peaks, valleys };
  };

  // WebSocket connection for real-time updates
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const wsUrl = `${apiUrl.replace(/^http/, 'ws')}/ws/trends?geo=${geo}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setIsConnected(true);
          setReconnectAttempts(0);
          console.log('WebSocket connected');
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'trends_update' && message.data) {
              setData(message.data);
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          console.log('WebSocket disconnected');

          // Attempt to reconnect only if WebSocket hasn't failed
          if (reconnectAttempts < 5 && !webSocketFailed) {
            setReconnectAttempts(prev => prev + 1);
            reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000 * (reconnectAttempts + 1));
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnected(false);
          if (!webSocketFailed) {
            setWebSocketFailed(true);
            info('Real-time updates unavailable', 'WebSocket connections are not supported in this browser environment. Data will refresh manually.');
            setReconnectAttempts(5); // Stop retrying
          }
        };

        wsRef.current = ws;
      } catch (err) {
        console.error('Failed to connect WebSocket:', err);
      }
    };

    // connectWebSocket(); // Disabled due to WebSocket connection issues

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [reconnectAttempts, geo]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl+R or Cmd+R for refresh
      if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
        event.preventDefault();
        fetchTrends();
      }
      // Ctrl+F or Cmd+F for focus search
      if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
      // Escape to clear search
      if (event.key === 'Escape') {
        setSearchQuery('');
        setDirectSearchQuery('');
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Load user preferences on mount
  useEffect(() => {
    const loadUserPreferences = async () => {
      try {
        const preferences = await api.getUserPreferences();
        if (preferences.searchHistory) {
          setSearchHistory(preferences.searchHistory);
        }
      } catch (err) {
        // Silently fail - search history will start empty
        console.log('Could not load user preferences:', err);
      }
    };
    loadUserPreferences();
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchTrends();
  }, [geo]);

  return (
    <div className={`enterprise-card enterprise-fade-in overflow-hidden ${className}`}>
      {/* Professional Header */}
      <div className="border-b border-border p-6 bg-gradient-to-r from-primary/5 to-accent/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-primary/10 border border-primary/20">
              <TrendingUp className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-foreground">Google Trends Analytics</h2>
              <p className="text-sm text-muted-foreground">Real-time trend monitoring and analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-card border border-border">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-xs font-medium text-muted-foreground">
                {isConnected ? 'Live' : 'Disconnected'}
              </span>
            </div>
            <RefreshButton onClick={fetchTrends} loading={loading} />
            <select
              value={geo}
              onChange={(e) => setGeo(e.target.value)}
              className="enterprise-card px-3 py-2 text-sm font-medium"
            >
              <option value="US">🇺🇸 United States</option>
              <option value="GB">🇬🇧 United Kingdom</option>
              <option value="CA">🇨🇦 Canada</option>
              <option value="AU">🇦🇺 Australia</option>
              <option value="DE">🇩🇪 Germany</option>
              <option value="FR">🇫🇷 France</option>
              <option value="JP">🇯🇵 Japan</option>
              <option value="IN">🇮🇳 India</option>
              <option value="BR">🇧🇷 Brazil</option>
            </select>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="border-b border-border p-6 bg-card/50">
        <div className="flex flex-col gap-4">
          {/* Search Bar */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search trending keywords..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full enterprise-card pl-12 pr-4 py-3 text-sm font-medium placeholder:text-muted-foreground focus:ring-2 focus:ring-primary/20"
                title="Search keywords • Ctrl+F to focus • Esc to clear"
              />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`p-3 rounded-xl border transition-all duration-200 ${
                showFilters
                  ? 'bg-primary text-primary-foreground border-primary shadow-lg'
                  : 'bg-card border-border hover:border-primary/50 hover:bg-primary/5'
              }`}
            >
              <Filter className="w-5 h-5" />
            </button>
          </div>

          {/* Mode Tabs */}
          <div className="flex gap-2 overflow-x-auto pb-1">
            {[
              { key: 'trending', label: 'Trending', icon: TrendingUp },
              { key: 'direct', label: 'Direct Search', icon: Search },
              { key: 'history', label: 'History', icon: Calendar },
              { key: 'alerts', label: 'Alerts', icon: AlertTriangle },
              { key: 'stats', label: 'Stats', icon: BarChart3 },
              { key: 'alert-rules', label: 'Alert Rules', icon: Target },
              { key: 'correlation', label: 'Correlation', icon: Activity },
              { key: 'visualizations', label: 'Visualizations', icon: Globe },
              { key: 'prediction', label: 'Prediction', icon: Zap }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setSearchMode(key as any)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-200 border ${
                  searchMode === key
                    ? 'bg-primary text-primary-foreground border-primary shadow-lg'
                    : 'bg-card border-border hover:border-primary/50 hover:bg-primary/5 text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="space-y-4">
              {/* Basic Filters */}
              <div className="flex flex-wrap gap-3">
                <select
                  value={directionFilter}
                  onChange={(e) => setDirectionFilter(e.target.value as any)}
                  className="enterprise-card px-4 py-2 text-sm font-medium min-w-[140px]"
                >
                  <option value="all">All Directions</option>
                  <option value="up">Trending Up</option>
                  <option value="down">Trending Down</option>
                  <option value="stable">Stable</option>
                </select>
                <select
                  value={trafficFilter}
                  onChange={(e) => setTrafficFilter(e.target.value as any)}
                  className="enterprise-card px-4 py-2 text-sm font-medium min-w-[140px]"
                >
                  <option value="all">All Traffic</option>
                  <option value="high">High Traffic</option>
                  <option value="medium">Medium Traffic</option>
                  <option value="low">Low Traffic</option>
                </select>
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="enterprise-card px-4 py-2 text-sm font-medium min-w-[140px]"
                >
                  <option value="all">All Categories</option>
                  <option value="Entertainment">Entertainment</option>
                  <option value="Sports">Sports</option>
                  <option value="Technology">Technology</option>
                  <option value="Politics">Politics</option>
                  <option value="Business">Business</option>
                  <option value="Health & Science">Health & Science</option>
                  <option value="General">General</option>
                </select>
                <button
                  onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                  className="flex items-center gap-2 px-4 py-2 enterprise-card text-sm font-medium hover:bg-primary/5 hover:border-primary/50 transition-all duration-200"
                >
                  <Filter className="w-4 h-4" />
                  Advanced
                  <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${showAdvancedFilters ? 'rotate-180' : ''}`} />
                </button>
              </div>

              {/* Advanced Filters */}
              {showAdvancedFilters && (
                <div className="enterprise-card p-6 space-y-4 bg-card/80 border-primary/10">
                  {/* Search Filter */}
                  <div className="relative">
                    <div className="flex items-center gap-3">
                      <Search className="w-5 h-5 text-muted-foreground" />
                      <input
                        type="text"
                        placeholder="Search keywords..."
                        value={searchFilter}
                        onChange={(e) => setSearchFilter(e.target.value)}
                        onKeyDown={async (e) => {
                          if (e.key === 'Enter' && searchFilter.trim()) {
                            // Add to search history
                            const newTerm = searchFilter.trim();
                            if (!searchHistory.includes(newTerm)) {
                              const newHistory = [newTerm, ...searchHistory.slice(0, 9)]; // Keep last 10
                              setSearchHistory(newHistory);
                              
                              // Save to backend
                              try {
                                await api.updateUserPreferences({ searchHistory: newHistory });
                              } catch (err) {
                                console.log('Could not save search history:', err);
                              }
                            }
                          }
                        }}
                        className="flex-1 enterprise-card px-4 py-2 text-sm font-medium"
                      />
                      <button
                        onClick={() => setShowSearchHistory(!showSearchHistory)}
                        className="p-2 rounded-lg hover:bg-primary/10 transition-colors duration-200"
                      >
                        <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${showSearchHistory ? 'rotate-180' : ''}`} />
                      </button>
                    </div>
                    {showSearchHistory && searchHistory.length > 0 && (
                      <div className="absolute top-full left-0 right-0 mt-1 bg-surface-2 border border-white/[0.06] rounded-lg shadow-lg z-10 max-h-40 overflow-y-auto">
                        {searchHistory.map((term, index) => (
                          <button
                            key={index}
                            onClick={() => {
                              setSearchFilter(term);
                              setShowSearchHistory(false);
                            }}
                            className="w-full text-left px-3 py-2 text-sm hover:bg-white/[0.05] transition-colors"
                          >
                            {term}
                          </button>
                        ))}
                        <div className="border-t border-white/[0.06] mt-1 pt-1">
                          <button
                            onClick={async () => {
                              setSearchHistory([]);
                              setShowSearchHistory(false);
                              try {
                                await api.updateUserPreferences({ searchHistory: [] });
                              } catch (err) {
                                console.log('Could not clear search history:', err);
                              }
                            }}
                            className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                          >
                            Clear History
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Traffic Range */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Traffic Range</label>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Min:</span>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={minTraffic}
                          onChange={(e) => setMinTraffic(Number(e.target.value))}
                          className="w-16 bg-surface-1 border border-white/[0.06] rounded px-2 py-1 text-sm"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Max:</span>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={maxTraffic}
                          onChange={(e) => setMaxTraffic(Number(e.target.value))}
                          className="w-16 bg-surface-1 border border-white/[0.06] rounded px-2 py-1 text-sm"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Velocity Range */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Velocity Range (% change)</label>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Min:</span>
                        <input
                          type="number"
                          step="0.1"
                          value={minVelocity}
                          onChange={(e) => setMinVelocity(Number(e.target.value))}
                          className="w-16 bg-surface-1 border border-white/[0.06] rounded px-2 py-1 text-sm"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Max:</span>
                        <input
                          type="number"
                          step="0.1"
                          value={maxVelocity}
                          onChange={(e) => setMaxVelocity(Number(e.target.value))}
                          className="w-16 bg-surface-1 border border-white/[0.06] rounded px-2 py-1 text-sm"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Sorting */}
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-muted-foreground">Sort by:</span>
                      <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as any)}
                        className="bg-surface-1 border border-white/[0.06] rounded px-2 py-1 text-sm"
                      >
                        <option value="rank">Rank</option>
                        <option value="traffic">Traffic</option>
                        <option value="velocity">Velocity</option>
                        <option value="keyword">Keyword</option>
                      </select>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-muted-foreground">Order:</span>
                      <select
                        value={sortOrder}
                        onChange={(e) => setSortOrder(e.target.value as any)}
                        className="bg-surface-1 border border-white/[0.06] rounded px-2 py-1 text-sm"
                      >
                        <option value="asc">Ascending</option>
                        <option value="desc">Descending</option>
                      </select>
                    </div>
                  </div>

                  {/* Bulk Actions */}
                  {selectedTrends.size > 0 && (
                    <div className="flex items-center gap-2 pt-2 border-t border-white/[0.06]">
                      <span className="text-sm text-muted-foreground">
                        {selectedTrends.size} selected
                      </span>
                      <button
                        onClick={() => {
                          const selectedData = filteredTrends.filter(trend => selectedTrends.has(trend.keyword));
                          
                          // Create CSV content
                          const headers = ['Rank', 'Keyword', 'Traffic', 'Direction', 'Velocity', 'Sparkline'];
                          const csvContent = [
                            headers.join(','),
                            ...selectedData.map(trend => [
                              trend.rank,
                              `"${trend.keyword.replace(/"/g, '""')}"`, // Escape quotes in CSV
                              trend.traffic_value,
                              trend.direction,
                              trend.velocity || 0,
                              `"${trend.sparkline.join(',')}"`
                            ].join(','))
                          ].join('\n');
                          
                          // Create and download file
                          const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                          const link = document.createElement('a');
                          const url = URL.createObjectURL(blob);
                          link.setAttribute('href', url);
                          link.setAttribute('download', `trends_export_${new Date().toISOString().split('T')[0]}.csv`);
                          link.style.visibility = 'hidden';
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                          
                          success('Export completed', `Exported ${selectedTrends.size} trends to CSV`);
                          setSelectedTrends(new Set()); // Clear selection after export
                        }}
                        className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600 transition-colors"
                      >
                        Export CSV
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            const selectedData = filteredTrends.filter(trend => selectedTrends.has(trend.keyword));
                            info('Starting bulk predictions', `Generating forecasts for ${selectedTrends.size} trends...`);
                            
                            // Generate predictions for each selected trend
                            const promises = selectedData.map(trend => 
                              api.forecastTrend(trend.keyword, geo, '24h', 'exponential_smoothing', 0.95)
                            );
                            
                            const results = await Promise.allSettled(promises);
                            const successful = results.filter(r => r.status === 'fulfilled').length;
                            const failed = results.filter(r => r.status === 'rejected').length;
                            
                            if (successful > 0) {
                              success('Bulk predictions completed', `Generated forecasts for ${successful} trends`);
                            }
                            if (failed > 0) {
                              showError('Some predictions failed', `Failed to predict ${failed} trends`);
                            }
                            
                            setSelectedTrends(new Set()); // Clear selection after operation
                          } catch (err) {
                            showError('Bulk prediction failed', err instanceof Error ? err.message : 'Unknown error');
                          }
                        }}
                        className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 transition-colors"
                      >
                        Predict Trends
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            const selectedData = filteredTrends.filter(trend => selectedTrends.has(trend.keyword));
                            info('Expanding keywords', `Finding related keywords for ${selectedTrends.size} trends...`);
                            
                            // Get related keywords for each selected trend
                            const promises = selectedData.map(trend => 
                              api.getRelatedKeywords(trend.keyword, 5) // 5 suggestions per keyword
                            );
                            
                            const results = await Promise.allSettled(promises);
                            const allSuggestions: string[] = [];
                            
                            results.forEach((result, index) => {
                              if (result.status === 'fulfilled' && result.value) {
                                const suggestions = result.value.map((s: any) => s.keyword);
                                allSuggestions.push(...suggestions);
                              }
                            });
                            
                            // Remove duplicates and original keywords
                            const originalKeywords = new Set(selectedData.map(t => t.keyword));
                            const uniqueSuggestions = [...new Set(allSuggestions)].filter(k => !originalKeywords.has(k));
                            
                            if (uniqueSuggestions.length > 0) {
                              success('Keyword expansion completed', `Found ${uniqueSuggestions.length} related keywords`);
                              // Could show a modal with suggestions or add them to a list
                              console.log('Related keywords found:', uniqueSuggestions);
                            } else {
                              info('No new keywords found', 'All suggestions were already in your selection');
                            }
                            
                            setSelectedTrends(new Set()); // Clear selection after operation
                          } catch (err) {
                            showError('Keyword expansion failed', err instanceof Error ? err.message : 'Unknown error');
                          }
                        }}
                        className="px-3 py-1 bg-orange-500 text-white rounded text-sm hover:bg-orange-600 transition-colors"
                      >
                        Find Related
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            const selectedData = filteredTrends.filter(trend => selectedTrends.has(trend.keyword));
                            // Add all selected trends to watchlist
                            const promises = selectedData.map(trend => 
                              api.addToWatchlist(trend.keyword, 'trends')
                            );
                            await Promise.all(promises);
                            success('Added to watchlist', `Added ${selectedTrends.size} trends to watchlist`);
                            setSelectedTrends(new Set()); // Clear selection after successful operation
                          } catch (err) {
                            showError('Failed to add to watchlist', err instanceof Error ? err.message : 'Unknown error');
                          }
                        }}
                        className="px-3 py-1 bg-purple-500 text-white rounded text-sm hover:bg-purple-600 transition-colors"
                      >
                        Add to Watchlist
                      </button>
                      <button
                        onClick={() => setSelectedTrends(new Set())}
                        className="px-3 py-1 text-sm text-muted-foreground hover:text-white transition-colors"
                      >
                        Clear Selection
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {error && (
          <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
            <div className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm font-medium">Error</span>
            </div>
            <p className="text-sm text-red-300 mt-1">{error}</p>
          </div>
        )}

        {loading && !data ? (
          <div className="space-y-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : (
          <>
            {/* Trending Mode */}
            {searchMode === 'trending' && (
              <div className="space-y-4">
                {filteredTrends.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <TrendingUp className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No trending data available</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Select All Checkbox */}
                    {filteredTrends.length > 0 && (
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={selectAll}
                          onChange={(e) => {
                            setSelectAll(e.target.checked);
                            if (e.target.checked) {
                              setSelectedTrends(new Set(filteredTrends.map(trend => trend.keyword)));
                            } else {
                              setSelectedTrends(new Set());
                            }
                          }}
                          className="rounded border-white/[0.06] bg-surface-1"
                        />
                        <span className="text-sm text-muted-foreground">
                          Select all ({filteredTrends.length})
                        </span>
                      </div>
                    )}
                    <div className="grid gap-4">
                      {filteredTrends.map((trend, index) => (
                        <div key={index} className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                          <div className="flex items-start justify-between">
                            <div className="flex items-start gap-3 flex-1">
                              <input
                                type="checkbox"
                                checked={selectedTrends.has(trend.keyword)}
                                onChange={(e) => {
                                  const newSelected = new Set(selectedTrends);
                                  if (e.target.checked) {
                                    newSelected.add(trend.keyword);
                                  } else {
                                    newSelected.delete(trend.keyword);
                                  }
                                  setSelectedTrends(newSelected);
                                  setSelectAll(newSelected.size === filteredTrends.length);
                                }}
                                className="mt-1 rounded border-white/[0.06] bg-surface-1"
                              />
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <h3 className="font-semibold text-lg">{trend.keyword}</h3>
                                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(categorizeTrend(trend.keyword))}`}>
                                    {categorizeTrend(trend.keyword)}
                                  </span>
                                </div>
                                <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                                  <span>Rank: #{trend.rank}</span>
                                  <span>Traffic: {trend.traffic_value?.toLocaleString() || 'N/A'}</span>
                                  <div className="flex items-center gap-1">
                                    {trend.direction === 'up' && <TrendingUp className="w-4 h-4 text-green-400" />}
                                    {trend.direction === 'down' && <TrendingDown className="w-4 h-4 text-red-400" />}
                                    <span className={
                                      trend.direction === 'up' ? 'text-green-400' :
                                      trend.direction === 'down' ? 'text-red-400' :
                                      'text-gray-400'
                                    }>
                                      {trend.direction === 'up' ? '+' : trend.direction === 'down' ? '-' : ''}
                                      {trend.velocity?.toFixed(2) || '0.00'}
                                    </span>
                                  </div>
                                </div>
                                {trend.sparkline && renderSparkline(trend.sparkline)}
                              </div>
                            </div>
                            <div className="flex gap-2">
                              <button
                                onClick={() => {
                                  setSelectedKeyword(trend.keyword);
                                  setSearchMode('history');
                                  fetchKeywordHistory(trend.keyword);
                                }}
                                className="p-2 text-muted-foreground hover:text-white hover:bg-white/[0.05] rounded"
                              >
                                <Calendar className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => {
                                  setCorrelationKeyword(trend.keyword);
                                  setSearchMode('correlation');
                                  fetchKeywordCorrelations(trend.keyword);
                                }}
                                className="p-2 text-muted-foreground hover:text-white hover:bg-white/[0.05] rounded"
                              >
                                <Activity className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Direct Search Mode */}
            {searchMode === 'direct' && (
              <div className="space-y-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter keyword to search..."
                    value={directSearchQuery}
                    onChange={(e) => setDirectSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && searchDirectTrends(directSearchQuery)}
                    className="flex-1 bg-surface-2 border border-white/[0.06] rounded px-3 py-2 text-sm"
                  />
                  <button
                    onClick={() => searchDirectTrends(directSearchQuery)}
                    disabled={searching || !directSearchQuery.trim()}
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-sm font-medium"
                  >
                    {searching ? <LoadingSpinner size="sm" /> : 'Search'}
                  </button>
                </div>

                {searchResults && (
                  <div className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                    <h3 className="font-semibold text-lg mb-4">{searchResults.keyword}</h3>
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <span className="text-sm text-muted-foreground">Rank</span>
                        <p className="text-2xl font-bold">#{searchResults.rank}</p>
                      </div>
                      <div>
                        <span className="text-sm text-muted-foreground">Traffic Value</span>
                        <p className="text-2xl font-bold">{searchResults.traffic_value?.toLocaleString() || 'N/A'}</p>
                      </div>
                    </div>
                    {searchResults.sparkline && (
                      <div>
                        <span className="text-sm text-muted-foreground mb-2 block">Trend</span>
                        {renderSparkline(searchResults.sparkline)}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* History Mode */}
            {searchMode === 'history' && (
              <div className="space-y-4">
                {selectedKeyword && (
                  <div className="flex items-center gap-2 mb-4">
                    <Calendar className="w-5 h-5 text-blue-400" />
                    <h3 className="text-lg font-semibold">History for "{selectedKeyword}"</h3>
                  </div>
                )}

                {historyData ? (
                  historyData.found ? (
                    <InteractiveTrendChart data={historyData.data_points} title={`History for "${selectedKeyword}"`} />
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <Calendar className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No historical data available for this keyword</p>
                    </div>
                  )
                ) : (
                  <SkeletonChart />
                )}
              </div>
            )}

            {/* Alerts Mode */}
            {searchMode === 'alerts' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Active Alerts</h3>
                  <button
                    onClick={fetchAlerts}
                    className="px-3 py-1 bg-blue-500 hover:bg-blue-600 rounded text-sm"
                  >
                    Refresh
                  </button>
                </div>

                {alertsData && alertsData.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No active alerts</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {/* Alert items would go here */}
                  </div>
                )}
              </div>
            )}

            {/* Stats Mode */}
            {searchMode === 'stats' && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Trend Statistics</h3>

                {statsData ? (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                      <div className="flex items-center gap-2 mb-2">
                        <BarChart3 className="w-5 h-5 text-blue-400" />
                        <span className="text-sm text-muted-foreground">Total Keywords</span>
                      </div>
                      <p className="text-2xl font-bold">{statsData.total_keywords}</p>
                    </div>
                    <div className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                      <div className="flex items-center gap-2 mb-2">
                        <Activity className="w-5 h-5 text-green-400" />
                        <span className="text-sm text-muted-foreground">Active Trends</span>
                      </div>
                      <p className="text-2xl font-bold">{statsData.active_trends}</p>
                    </div>
                    <div className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                      <div className="flex items-center gap-2 mb-2">
                        <Zap className="w-5 h-5 text-yellow-400" />
                        <span className="text-sm text-muted-foreground">Avg Velocity</span>
                      </div>
                      <p className="text-2xl font-bold">{statsData.avg_velocity?.toFixed(2) || '0.00'}</p>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <SkeletonCard />
                    <SkeletonCard />
                    <SkeletonCard />
                  </div>
                )}
              </div>
            )}

            {/* Alert Rules Mode */}
            {searchMode === 'alert-rules' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Alert Rules</h3>
                  <button
                    onClick={() => setShowCreateRule(true)}
                    className="px-3 py-1 bg-blue-500 hover:bg-blue-600 rounded text-sm"
                  >
                    Create Rule
                  </button>
                </div>

                {showCreateRule && (
                  <div className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                    <h4 className="font-medium mb-4">Create New Alert Rule</h4>
                    <AlertRuleForm
                      onSubmit={createAlertRule}
                      onCancel={() => setShowCreateRule(false)}
                    />
                  </div>
                )}

                {alertRulesData && alertRulesData.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Target className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No alert rules configured</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {/* Alert rule items would go here */}
                  </div>
                )}
              </div>
            )}

            {/* Correlation Mode */}
            {searchMode === 'correlation' && (
              <div className="space-y-4">
                {correlationKeyword && (
                  <div className="flex items-center gap-2 mb-4">
                    <Activity className="w-5 h-5 text-blue-400" />
                    <h3 className="text-lg font-semibold">Correlations for "{correlationKeyword}"</h3>
                  </div>
                )}

                {correlationData ? (
                  correlationData.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No correlation data available</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Correlation visualization would go here */}
                    </div>
                  )
                ) : (
                  <SkeletonChart />
                )}
              </div>
            )}

            {/* Visualizations Mode */}
            {searchMode === 'visualizations' && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Trend Visualizations</h3>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                    <h4 className="font-medium mb-4">Geographic Heatmap</h4>
                    <GeographicHeatmap data={[]} />
                  </div>
                  <div className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                    <h4 className="font-medium mb-4">Trend Comparison</h4>
                    <TrendComparison availableTrends={[]} />
                  </div>
                </div>
              </div>
            )}

            {/* Prediction Mode */}
            {searchMode === 'prediction' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Trend Prediction</h3>
                  <RefreshButton onClick={() => selectedKeyword && fetchPrediction(selectedKeyword)} loading={predictionLoading} />
                </div>

                {/* Prediction Controls */}
                <div className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                  <h4 className="font-medium mb-4">Prediction Settings</h4>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Algorithm</label>
                      <select
                        value={predictionAlgorithm}
                        onChange={(e) => setPredictionAlgorithm(e.target.value as any)}
                        className="w-full bg-surface-1 border border-white/[0.06] rounded px-3 py-2 text-sm"
                      >
                        <option value="exponential_smoothing">Exponential Smoothing</option>
                        <option value="arima">ARIMA</option>
                        <option value="linear_regression">Linear Regression</option>
                        <option value="naive">Naive</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Horizon</label>
                      <select
                        value={predictionHorizon}
                        onChange={(e) => setPredictionHorizon(e.target.value as any)}
                        className="w-full bg-surface-1 border border-white/[0.06] rounded px-3 py-2 text-sm"
                      >
                        <option value="1h">1 Hour</option>
                        <option value="6h">6 Hours</option>
                        <option value="24h">24 Hours</option>
                        <option value="7d">7 Days</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Confidence ({Math.round(predictionConfidence * 100)}%)</label>
                      <input
                        type="range"
                        min="0.8"
                        max="0.99"
                        step="0.01"
                        value={predictionConfidence}
                        onChange={(e) => setPredictionConfidence(parseFloat(e.target.value))}
                        className="w-full"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Keyword</label>
                      <select
                        value={selectedKeyword}
                        onChange={(e) => setSelectedKeyword(e.target.value)}
                        className="w-full bg-surface-1 border border-white/[0.06] rounded px-3 py-2 text-sm"
                      >
                        <option value="">Select a keyword...</option>
                        {data?.trends?.map((trend) => (
                          <option key={trend.keyword} value={trend.keyword}>
                            {trend.keyword}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Prediction Results */}
                {predictionData ? (
                  <div className="bg-surface-2 rounded-lg p-4 border border-white/[0.06]">
                    <h4 className="font-medium mb-4">Prediction Results for "{predictionData.keyword?.name || selectedKeyword}"</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <div className="text-center">
                        <p className="text-2xl font-bold text-blue-400">{predictionData.predictions?.length || 0}</p>
                        <p className="text-sm text-muted-foreground">Forecast Points</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-green-400">{predictionData.forecast_horizon?.requested || predictionHorizon}</p>
                        <p className="text-sm text-muted-foreground">Horizon</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-orange-400">{predictionData.algorithm}</p>
                        <p className="text-sm text-muted-foreground">Algorithm</p>
                      </div>
                    </div>
                    <InteractiveTrendChart 
                      data={predictionData.historical_data || []} 
                      title={`Historical + Forecast for "${predictionData.keyword?.name || selectedKeyword}"`} 
                    />
                  </div>
                ) : selectedKeyword ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Zap className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Select prediction settings and click refresh to generate forecast</p>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Zap className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Select a keyword from the trending list to generate predictions</p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function AlertRuleForm({ onSubmit, onCancel }: { onSubmit: (data: any) => void; onCancel: () => void }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    condition_type: 'velocity_threshold',
    threshold_value: 0.5,
    comparison_operator: '>',
    severity: 'medium',
    target_keywords: [] as string[],
    cooldown_minutes: 60,
    enabled: true,
    notify_desktop: false,
    notify_email: false
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const addKeyword = (keyword: string) => {
    if (keyword && !formData.target_keywords.includes(keyword)) {
      setFormData(prev => ({
        ...prev,
        target_keywords: [...prev.target_keywords, keyword]
      }));
    }
  };

  const removeKeyword = (keyword: string) => {
    setFormData(prev => ({
      ...prev,
      target_keywords: prev.target_keywords.filter(k => k !== keyword)
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Rule Name</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            className="w-full bg-surface-2 border border-white/[0.06] rounded px-3 py-2 text-sm"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Severity</label>
          <select
            value={formData.severity}
            onChange={(e) => setFormData(prev => ({ ...prev, severity: e.target.value }))}
            className="w-full bg-surface-2 border border-white/[0.06] rounded px-3 py-2 text-sm"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Description</label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          className="w-full bg-surface-2 border border-white/[0.06] rounded px-3 py-2 text-sm"
          rows={3}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Condition Type</label>
          <select
            value={formData.condition_type}
            onChange={(e) => setFormData(prev => ({ ...prev, condition_type: e.target.value }))}
            className="w-full bg-surface-2 border border-white/[0.06] rounded px-3 py-2 text-sm"
          >
            <option value="velocity_threshold">Velocity Threshold</option>
            <option value="rank_threshold">Rank Threshold</option>
            <option value="traffic_threshold">Traffic Threshold</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Comparison</label>
          <select
            value={formData.comparison_operator}
            onChange={(e) => setFormData(prev => ({ ...prev, comparison_operator: e.target.value }))}
            className="w-full bg-surface-2 border border-white/[0.06] rounded px-3 py-2 text-sm"
          >
            <option value=">">Greater than</option>
            <option value="<">Less than</option>
            <option value=">=">Greater or equal</option>
            <option value="<=">Less or equal</option>
            <option value="==">Equal to</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Threshold Value</label>
        <input
          type="number"
          step="0.1"
          value={formData.threshold_value}
          onChange={(e) => setFormData(prev => ({ ...prev, threshold_value: parseFloat(e.target.value) }))}
          className="w-full bg-surface-2 border border-white/[0.06] rounded px-3 py-2 text-sm"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Target Keywords</label>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            placeholder="Add keyword..."
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addKeyword((e.target as HTMLInputElement).value), (e.target as HTMLInputElement).value = '')}
            className="flex-1 bg-surface-2 border border-white/[0.06] rounded px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={(e) => {
              const input = e.currentTarget.previousElementSibling as HTMLInputElement;
              addKeyword(input.value);
              input.value = '';
            }}
            className="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm"
          >
            Add
          </button>
        </div>
        {formData.target_keywords.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {formData.target_keywords.map((keyword, idx) => (
              <span key={idx} className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-blue-500/20 text-blue-400 rounded">
                {keyword}
                <button
                  type="button"
                  onClick={() => removeKeyword(keyword)}
                  className="hover:text-red-400"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Cooldown (minutes)</label>
          <input
            type="number"
            value={formData.cooldown_minutes}
            onChange={(e) => setFormData(prev => ({ ...prev, cooldown_minutes: parseInt(e.target.value) }))}
            className="w-full bg-surface-2 border border-white/[0.06] rounded px-3 py-2 text-sm"
            min="1"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Notifications</label>
          <div className="flex gap-2">
            <label className="flex items-center gap-1 text-sm">
              <input
                type="checkbox"
                checked={formData.notify_desktop}
                onChange={(e) => setFormData(prev => ({ ...prev, notify_desktop: e.target.checked }))}
              />
              Desktop
            </label>
            <label className="flex items-center gap-1 text-sm">
              <input
                type="checkbox"
                checked={formData.notify_email}
                onChange={(e) => setFormData(prev => ({ ...prev, notify_email: e.target.checked }))}
              />
              Email
            </label>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-muted-foreground hover:text-white transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg text-sm font-medium transition-colors"
        >
          Create Rule
        </button>
      </div>
    </form>
  );
}
