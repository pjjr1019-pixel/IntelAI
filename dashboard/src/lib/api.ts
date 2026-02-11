const BASE = process.env.NEXT_PUBLIC_API_URL || '';

// Simple in-memory cache for API responses
const cache = new Map<string, { data: any; timestamp: number }>();
const CACHE_DURATION = 120000; // 2 minutes (increased for dashboard responsiveness)

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('vs_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }
  return headers;
}

export async function apiRequest(endpoint: string, options: RequestInit = {}, useCache = true) {
  const url = `${BASE}${endpoint}`;
  const cacheKey = `${options.method || 'GET'}-${url}`;

  // Check cache for GET requests
  if (useCache && (!options.method || options.method === 'GET')) {
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      return cached.data;
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        ...getAuthHeaders(),
        ...options.headers,
      },
      // Add timeout for API requests (30 seconds)
      signal: AbortSignal.timeout(30000),
    });
  } catch (err) {
    // Network errors (DNS, refused connection, CORS preflight failure, etc.)
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`Network error while fetching ${url}: ${message}`);
  }

  if (!response.ok) {
    // Attempt to include response body if available for debugging
    let bodyText = '';
    try {
      bodyText = await response.text();
    } catch (_) {
      /* ignore */
    }
    throw new Error(`API request failed: ${response.status} ${response.statusText}${bodyText ? ` - ${bodyText}` : ''}`);
  }

  const data = await response.json();

  // Cache successful GET responses
  if (useCache && (!options.method || options.method === 'GET')) {
    cache.set(cacheKey, { data, timestamp: Date.now() });
  }

  return data;
}

// Types
export interface DashboardOverview {
  total_alerts: number;
  active_alerts: number;
  alerts_24h: number;
  alerts_7d: number;
  last_update: string;
}

export interface TimelinePoint {
  timestamp: string;
  value: number;
}

export interface TopEntity {
  name: string;
  score: number;
  change: number;
}

export interface TrendingEntity {
  name: string;
  trend: 'up' | 'down' | 'stable';
  confidence: number;
}

export interface TrendingResponse {
  entities: TrendingEntity[];
  timestamp: string;
}

export interface TrendingNewsItem {
  title: string;
  url: string;
  source: string;
  snippet: string;
}

export interface LiveTrendingEntity {
  rank: number;
  keyword: string;
  approx_traffic: string;
  traffic_value: number;
  sparkline: number[];
  current_interest: number;
  peak_interest: number;
  velocity: number;
  acceleration: number;
  pct_change_24h: number;
  direction: string;
  news: TrendingNewsItem[];
  published_at: string;
  geo: string;
}

export interface LiveTrendingResponse {
  trends: LiveTrendingEntity[];
  total: number;
  geo: string;
  generated_at: string;
  cached: boolean;
}

// Analytics interfaces
export interface AnalyticsPerformance {
  time_period_days: number;
  alert_accuracy: {
    total_alerts: number;
    resolved_alerts: number;
    confirmed_alerts: number;
    dismissed_alerts: number;
    accuracy_rate_percent: number;
    false_positive_rate_percent: number;
    resolution_rate_percent: number;
  };
  confidence_metrics: {
    avg_confidence_all_alerts: number;
    avg_confidence_confirmed_alerts: number;
  };
  trend_metrics: {
    total_trends_detected: number;
    active_trends: number;
    avg_detection_latency_hours: number;
  };
}

export interface AnalyticsEffectiveness {
  time_period_days: number;
  response_time_metrics: {
    avg_response_hours: number;
    min_response_hours: number;
    max_response_hours: number;
  };
  severity_distribution: Record<string, number>;
  outcome_analysis_by_severity: Record<string, {
    confirmed: number;
    dismissed: number;
    total: number;
    confirmation_rate_percent: number;
  }>;
}

export interface AnalyticsBusinessImpact {
  time_period_days: number;
  business_outcomes: {
    completed_cases: number;
    outcome_distribution: Record<string, number>;
  };
  roi_metrics: {
    total_investigation_costs: number;
    total_value_captured: number;
    net_roi: number;
    roi_percentage: number;
    efficiency_ratio: number;
    avg_cost_per_alert: number;
    avg_value_per_signal: number;
  };
  alert_efficiency: {
    confirmed_signals: number;
    false_positives: number;
    accuracy_rate_percent: number;
  };
}

export interface AnalyticsLifecycle {
  time_period_days: number;
  lifecycle_stages: {
    emerging: number;
    growing: number;
    peaking: number;
    declining: number;
  };
  trend_characteristics: {
    avg_lifespan_days: number;
    high_velocity_trends: number;
  };
  trend_health: {
    total_active_trends: number;
    trend_diversity_score: number;
  };
}

// Google Trends interfaces
export interface TrendsPreviewRequest {
  keywords: string[];
  timeframe: string;
  geo: string;
}

export interface TrendDataPoint {
  timestamp: string;
  scores: Record<string, number>;
}

export interface TrendsPreviewResponse {
  keywords: string[];
  timeframe: string;
  geo: string;
  data_points: TrendDataPoint[];
  total_points: number;
  elapsed_seconds: number;
}

export interface TrendsIngestResponse {
  status: string;
  keywords: string[];
  events_created: number;
  elapsed_seconds: number;
}

// API functions
export const api = {
  getDashboardOverview: () => apiRequest('/api/dashboard/overview'),
  getTimelineData: () => apiRequest('/api/dashboard/timeline'),
  getTopEntities: () => apiRequest('/api/dashboard/top-entities'),
  getTrending: () => apiRequest('/api/trending'),
  getLiveTrending: (geo?: string) => apiRequest(`/api/trending/live${geo ? `?geo=${geo}&enrich=false` : '?enrich=false'}`),
  searchGoogleTrends: (query: string, geo?: string) => apiRequest(`/api/trending/search?q=${encodeURIComponent(query)}${geo ? `&geo=${geo}` : ''}`),
  getNewsFeed: (limit?: number) => apiRequest(`/api/news/feed${limit ? `?limit=${limit}` : ''}`),
  getSaturatedNarratives: (timeWindowHours?: number, minSaturationScore?: number) => {
    const params = new URLSearchParams();
    if (timeWindowHours) params.append('time_window_hours', timeWindowHours.toString());
    if (minSaturationScore) params.append('min_saturation_score', minSaturationScore.toString());
    return apiRequest(`/api/narrative/saturation${params.toString() ? `?${params.toString()}` : ''}`);
  },
  getNarrativeClusters: (timeWindowHours?: number, minClusterSize?: number) => {
    const params = new URLSearchParams();
    if (timeWindowHours) params.append('time_window_hours', timeWindowHours.toString());
    if (minClusterSize) params.append('min_cluster_size', minClusterSize.toString());
    return apiRequest(`/api/narrative/clusters${params.toString() ? `?${params.toString()}` : ''}`);
  },
  getTrendPrediction: (keyword: string, options?: { geo?: string; horizon?: string; algorithm?: string; confidence?: number }) => {
    const params = new URLSearchParams();
    if (options?.geo) params.append('geo', options.geo);
    if (options?.horizon) params.append('horizon', options.horizon);
    if (options?.algorithm) params.append('algorithm', options.algorithm);
    if (options?.confidence) params.append('confidence_level', options.confidence.toString());
    return apiRequest(`/api/prediction/forecast/${encodeURIComponent(keyword)}${params.toString() ? `?${params.toString()}` : ''}`);
  },
  // Google Trends specific functions
  previewGoogleTrends: (request: TrendsPreviewRequest) => apiRequest('/api/sources/google-trends/preview', {
    method: 'POST',
    body: JSON.stringify(request),
  }),
  ingestGoogleTrends: (request: TrendsPreviewRequest) => apiRequest('/api/sources/google-trends/ingest', {
    method: 'POST',
    body: JSON.stringify(request),
  }),
  // Analytics functions
  getAnalyticsPerformance: (days?: number) => apiRequest(`/api/analytics/performance${days ? `?days=${days}` : ''}`),
  getAnalyticsEffectiveness: (days?: number) => apiRequest(`/api/analytics/alert-effectiveness${days ? `?days=${days}` : ''}`),
  getAnalyticsBusinessImpact: (days?: number) => apiRequest(`/api/analytics/business-impact${days ? `?days=${days}` : ''}`),
  getAnalyticsLifecycle: (days?: number) => apiRequest(`/api/analytics/trend-lifecycle${days ? `?days=${days}` : ''}`),
  // Strategies functions
  getStrategies: (type?: string) => apiRequest(`/api/strategies${type ? `?strategy_type=${type}` : ''}`),
  getStrategy: (id: string) => apiRequest(`/api/strategies/${id}`),
  deployStrategy: (request: { strategy_id: string; name: string; capital: number; parameters: Record<string, any> }) =>
    apiRequest('/api/strategies/deploy', {
      method: 'POST',
      body: JSON.stringify(request),
    }),
  getDeployedStrategies: () => apiRequest('/api/strategies/deployed/'),
  undeployStrategy: (deploymentId: string) => apiRequest(`/api/strategies/deployed/${deploymentId}`, {
    method: 'DELETE',
  }),
  // User preferences functions
  getUserPreferences: () => apiRequest('/api/user/preferences'),
  updateUserPreferences: (preferences: Record<string, any>) => apiRequest('/api/user/preferences', {
    method: 'PUT',
    body: JSON.stringify(preferences),
  }),
  // Watchlist functions
  getWatchlist: () => apiRequest('/api/watchlist'),
  getFlatWatchlist: () => apiRequest('/api/watchlist/flat'),
  addToWatchlist: (keyword: string, category: string = 'trends') => apiRequest('/api/watchlist/keywords', {
    method: 'POST',
    body: JSON.stringify({ keyword, category }),
  }),
  removeFromWatchlist: (keyword: string, category?: string) => apiRequest('/api/watchlist/keywords', {
    method: 'DELETE',
    body: JSON.stringify({ keyword, category }),
  }),
  // Keyword expansion functions
  getRelatedKeywords: (keyword: string, maxSuggestions: number = 10) => 
    apiRequest(`/api/keyword-expansion/related/${encodeURIComponent(keyword)}?max_suggestions=${maxSuggestions}`),
};

// WebSocket connection management
class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Map<string, ((data: any) => void)[]> = new Map();

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const token = typeof window !== 'undefined' ? localStorage.getItem('vs_token') : null;
    const url = `${BASE.replace('http', 'ws')}/ws/analytics${token ? `?token=${token}` : ''}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('Analytics WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connected', { timestamp: new Date().toISOString() });
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit(data.type, data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('Analytics WebSocket disconnected');
      this.emit('disconnected', { timestamp: new Date().toISOString() });
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('Analytics WebSocket error:', error);
      this.emit('error', error);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Attempting to reconnect WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);
  }

  off(event: string, callback: (data: any) => void) {
    const listeners = this.listeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private emit(event: string, data: any) {
    const listeners = this.listeners.get(event);
    if (listeners) {
      listeners.forEach(callback => callback(data));
    }
  }
}

export const websocketManager = new WebSocketManager();