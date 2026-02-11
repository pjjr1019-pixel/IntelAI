'use client';

import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts';
import { Plus, X, TrendingUp, BarChart3, Activity, Eye, EyeOff } from 'lucide-react';

interface ComparisonDataPoint {
  timestamp: string;
  [key: string]: string | number | undefined; // Dynamic keys for different trend values
}

interface TrendSeries {
  id: string;
  name: string;
  data: ComparisonDataPoint[];
  color: string;
  visible: boolean;
}

interface TrendComparisonProps {
  availableTrends: Array<{
    id: string;
    name: string;
    data: ComparisonDataPoint[];
    category?: string;
  }>;
  title?: string;
  height?: number;
  maxComparisons?: number;
}

const COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#10b981', // green
  '#f59e0b', // yellow
  '#8b5cf6', // purple
  '#06b6d4', // cyan
  '#f97316', // orange
  '#84cc16', // lime
  '#ec4899', // pink
  '#6b7280', // gray
];

export default function TrendComparison({
  availableTrends,
  title = 'Trend Comparison',
  height = 400,
  maxComparisons = 5,
}: TrendComparisonProps) {
  const [selectedTrends, setSelectedTrends] = useState<TrendSeries[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showLegend, setShowLegend] = useState(true);

  // Filter available trends based on search
  const filteredTrends = useMemo(() => {
    return availableTrends.filter(trend =>
      trend.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [availableTrends, searchQuery]);

  // Combine data from all selected trends
  const combinedData = useMemo(() => {
    if (selectedTrends.length === 0) return [];

    // Get all unique timestamps
    const allTimestamps = new Set<string>();
    selectedTrends.forEach(trend => {
      trend.data.forEach(point => allTimestamps.add(point.timestamp));
    });

    // Create combined data points
    return Array.from(allTimestamps)
      .sort()
      .map(timestamp => {
        const point: ComparisonDataPoint = { timestamp };

        selectedTrends.forEach(trend => {
          const trendPoint = trend.data.find(p => p.timestamp === timestamp);
          point[trend.id] = trendPoint ? trendPoint.value : undefined;
        });

        return point;
      });
  }, [selectedTrends]);

  const addTrend = (trendId: string) => {
    if (selectedTrends.length >= maxComparisons) return;

    const trend = availableTrends.find(t => t.id === trendId);
    if (!trend || selectedTrends.some(t => t.id === trendId)) return;

    const color = COLORS[selectedTrends.length % COLORS.length];
    const newTrend: TrendSeries = {
      id: trend.id,
      name: trend.name,
      data: trend.data,
      color,
      visible: true,
    };

    setSelectedTrends(prev => [...prev, newTrend]);
  };

  const removeTrend = (trendId: string) => {
    setSelectedTrends(prev => prev.filter(t => t.id !== trendId));
  };

  const toggleTrendVisibility = (trendId: string) => {
    setSelectedTrends(prev =>
      prev.map(t =>
        t.id === trendId ? { ...t, visible: !t.visible } : t
      )
    );
  };

  const formatTooltipValue = (value: any, name: string) => {
    if (value === null || value === undefined) return ['No data', name];
    return [typeof value === 'number' ? value.toFixed(2) : value, name];
  };

  const formatXAxisTick = (value: string) => {
    const date = new Date(value);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  // Calculate correlation between visible trends
  const correlations = useMemo(() => {
    if (selectedTrends.length < 2) return [];

    const visibleTrends = selectedTrends.filter(t => t.visible);
    if (visibleTrends.length < 2) return [];

    const correlations: Array<{ trend1: string; trend2: string; correlation: number }> = [];

    for (let i = 0; i < visibleTrends.length; i++) {
      for (let j = i + 1; j < visibleTrends.length; j++) {
        const trend1 = visibleTrends[i];
        const trend2 = visibleTrends[j];

        // Calculate correlation coefficient
        const values1: number[] = [];
        const values2: number[] = [];

        combinedData.forEach(point => {
          const val1 = point[trend1.id] as number | null;
          const val2 = point[trend2.id] as number | null;
          if (val1 !== null && val2 !== null) {
            values1.push(val1);
            values2.push(val2);
          }
        });

        if (values1.length > 1) {
          const correlation = calculateCorrelation(values1, values2);
          correlations.push({
            trend1: trend1.name,
            trend2: trend2.name,
            correlation,
          });
        }
      }
    }

    return correlations.sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation));
  }, [selectedTrends, combinedData]);

  return (
    <div className="bg-surface-2/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          {title}
        </h3>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowLegend(!showLegend)}
            className="p-1 hover:bg-surface-1 rounded transition-colors"
            title={showLegend ? 'Hide Legend' : 'Show Legend'}
          >
            {showLegend ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Selected Trends */}
      {selectedTrends.length > 0 && (
        <div className="mb-4">
          <div className="flex flex-wrap gap-2">
            {selectedTrends.map((trend) => (
              <div
                key={trend.id}
                className="flex items-center gap-2 bg-surface-1 rounded-lg px-3 py-1"
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: trend.color }}
                />
                <span className="text-sm font-medium">{trend.name}</span>
                <button
                  onClick={() => toggleTrendVisibility(trend.id)}
                  className={`p-0.5 rounded transition-colors ${
                    trend.visible ? 'hover:bg-green-500/20' : 'hover:bg-gray-500/20'
                  }`}
                  title={trend.visible ? 'Hide' : 'Show'}
                >
                  {trend.visible ? (
                    <Eye className="w-3 h-3 text-green-400" />
                  ) : (
                    <EyeOff className="w-3 h-3 text-gray-400" />
                  )}
                </button>
                <button
                  onClick={() => removeTrend(trend.id)}
                  className="p-0.5 hover:bg-red-500/20 rounded transition-colors"
                  title="Remove"
                >
                  <X className="w-3 h-3 text-red-400" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart Area */}
        <div className="lg:col-span-2">
          {selectedTrends.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Activity className="w-12 h-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No Trends Selected</h3>
              <p className="text-muted-foreground">
                Add trends from the panel on the right to start comparing them.
              </p>
            </div>
          ) : (
            <div style={{ height: `${height}px` }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={combinedData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="timestamp"
                    tick={{ fontSize: 12, fill: '#9ca3af' }}
                    tickFormatter={formatXAxisTick}
                  />
                  <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} />
                  <Tooltip
                    labelFormatter={(value) => new Date(value).toLocaleString()}
                    formatter={formatTooltipValue}
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '8px',
                    }}
                  />
                  {showLegend && (
                    <Legend
                      wrapperStyle={{ paddingTop: '20px' }}
                      iconType="line"
                    />
                  )}

                  {selectedTrends
                    .filter(trend => trend.visible)
                    .map((trend) => (
                      <Line
                        key={trend.id}
                        type="monotone"
                        dataKey={trend.id}
                        stroke={trend.color}
                        strokeWidth={2}
                        dot={{ r: 2, fill: trend.color }}
                        activeDot={{ r: 4, fill: trend.color }}
                        name={trend.name}
                        connectNulls={false}
                      />
                    ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Control Panel */}
        <div className="space-y-4">
          {/* Search and Add Trends */}
          <div>
            <h4 className="font-medium mb-3">Add Trends to Compare</h4>

            {/* Search */}
            <div className="relative mb-3">
              <input
                type="text"
                placeholder="Search trends..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg pl-3 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
            </div>

            {/* Available Trends */}
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {filteredTrends
                .filter(trend => !selectedTrends.some(st => st.id === trend.id))
                .map((trend) => (
                  <div
                    key={trend.id}
                    className="flex items-center justify-between p-2 hover:bg-surface-1 rounded cursor-pointer transition-colors"
                    onClick={() => addTrend(trend.id)}
                  >
                    <div className="flex items-center gap-2">
                      <Plus className="w-4 h-4 text-blue-400" />
                      <span className="text-sm">{trend.name}</span>
                    </div>
                    {trend.category && (
                      <span className="text-xs px-2 py-1 rounded-full bg-surface-2 text-muted-foreground">
                        {trend.category}
                      </span>
                    )}
                  </div>
                ))}
            </div>

            {selectedTrends.length >= maxComparisons && (
              <div className="text-xs text-orange-400 mt-2">
                Maximum of {maxComparisons} trends can be compared at once.
              </div>
            )}
          </div>

          {/* Correlation Analysis */}
          {correlations.length > 0 && (
            <div>
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Correlation Analysis
              </h4>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {correlations.slice(0, 5).map((corr, index) => (
                  <div key={index} className="text-xs bg-surface-1 rounded p-2">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-muted-foreground">
                        {corr.trend1} ↔ {corr.trend2}
                      </span>
                      <span className={`font-medium ${
                        Math.abs(corr.correlation) > 0.7 ? 'text-green-400' :
                        Math.abs(corr.correlation) > 0.5 ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>
                        {corr.correlation > 0 ? '+' : ''}{corr.correlation.toFixed(2)}
                      </span>
                    </div>
                    <div className="w-full bg-surface-2 rounded-full h-1">
                      <div
                        className={`h-1 rounded-full ${
                          corr.correlation > 0 ? 'bg-green-500' : 'bg-red-500'
                        }`}
                        style={{
                          width: `${Math.abs(corr.correlation) * 100}%`,
                          marginLeft: corr.correlation < 0 ? `${(1 - Math.abs(corr.correlation)) * 100}%` : '0',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Statistics */}
          {selectedTrends.length > 0 && (
            <div className="bg-surface-1 rounded-lg p-3">
              <h4 className="font-medium mb-2">Comparison Stats</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Trends:</span>
                  <span className="font-medium">{selectedTrends.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Data Points:</span>
                  <span className="font-medium">{combinedData.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Time Range:</span>
                  <span className="font-medium text-xs">
                    {combinedData.length > 0 ? (
                      `${new Date(combinedData[0].timestamp).toLocaleDateString()} - ${new Date(combinedData[combinedData.length - 1].timestamp).toLocaleDateString()}`
                    ) : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper function to calculate correlation coefficient
function calculateCorrelation(x: number[], y: number[]): number {
  const n = x.length;
  if (n === 0) return 0;

  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
  const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
  const sumY2 = y.reduce((sum, yi) => sum + yi * yi, 0);

  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));

  return denominator === 0 ? 0 : numerator / denominator;
}