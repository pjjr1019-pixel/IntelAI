'use client';

import { useState, useRef, useCallback } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  Brush,
  ReferenceLine,
  ComposedChart,
} from 'recharts';
import { ZoomIn, ZoomOut, RotateCcw, Download, BarChart3, TrendingUp, Activity } from 'lucide-react';

interface DataPoint {
  timestamp: string;
  value: number;
  velocity?: number;
  peak?: boolean;
  valley?: boolean;
}

interface InteractiveTrendChartProps {
  data: DataPoint[];
  title?: string;
  height?: number;
  showVelocity?: boolean;
  showPeaksValleys?: boolean;
  chartType?: 'line' | 'area' | 'bar' | 'composed';
  color?: string;
  onExport?: (format: 'png' | 'svg' | 'csv') => void;
}

export default function InteractiveTrendChart({
  data,
  title = 'Trend Chart',
  height = 400,
  showVelocity = false,
  showPeaksValleys = true,
  chartType = 'line',
  color = '#3b82f6',
  onExport,
}: InteractiveTrendChartProps) {
  const [zoomDomain, setZoomDomain] = useState<{ start: number; end: number } | null>(null);
  const [brushDomain, setBrushDomain] = useState<{ startIndex: number; endIndex: number } | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  const handleZoomIn = useCallback(() => {
    if (!data.length) return;

    const currentDomain = zoomDomain || { start: 0, end: data.length - 1 };
    const range = currentDomain.end - currentDomain.start;
    const center = (currentDomain.start + currentDomain.end) / 2;
    const newRange = Math.max(5, range * 0.8); // Zoom in by 20%

    setZoomDomain({
      start: Math.max(0, Math.floor(center - newRange / 2)),
      end: Math.min(data.length - 1, Math.floor(center + newRange / 2)),
    });
  }, [data.length, zoomDomain]);

  const handleZoomOut = useCallback(() => {
    if (!data.length) return;

    const currentDomain = zoomDomain || { start: 0, end: data.length - 1 };
    const range = currentDomain.end - currentDomain.start;
    const center = (currentDomain.start + currentDomain.end) / 2;
    const newRange = Math.min(data.length - 1, range / 0.8); // Zoom out by 20%

    setZoomDomain({
      start: Math.max(0, Math.floor(center - newRange / 2)),
      end: Math.min(data.length - 1, Math.floor(center + newRange / 2)),
    });
  }, [data.length, zoomDomain]);

  const handleResetZoom = useCallback(() => {
    setZoomDomain(null);
    setBrushDomain(null);
  }, []);

  const handleBrushChange = useCallback((domain: any) => {
    if (domain && typeof domain.startIndex === 'number' && typeof domain.endIndex === 'number') {
      setBrushDomain({ startIndex: domain.startIndex, endIndex: domain.endIndex });
    }
  }, []);

  const displayData = brushDomain
    ? data.slice(brushDomain.startIndex, brushDomain.endIndex + 1)
    : zoomDomain
    ? data.slice(zoomDomain.start, zoomDomain.end + 1)
    : data;

  const formatTooltipValue = (value: number, name: string) => {
    if (name === 'value') return [`${value.toFixed(2)}`, 'Interest Score'];
    if (name === 'velocity') return [`${value.toFixed(3)}`, 'Velocity'];
    return [value, name];
  };

  const formatXAxisTick = (value: string) => {
    const date = new Date(value);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: zoomDomain ? '2-digit' : undefined,
    });
  };

  const renderChart = () => {
    const commonProps = {
      data: displayData,
      margin: { top: 20, right: 30, left: 20, bottom: 20 },
    };

    const tooltipProps = {
      labelFormatter: (value: string) => new Date(value).toLocaleString(),
      formatter: formatTooltipValue,
      contentStyle: {
        backgroundColor: '#1f2937',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '8px',
      },
    };

    switch (chartType) {
      case 'area':
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="timestamp"
              tick={{ fontSize: 12, fill: '#9ca3af' }}
              tickFormatter={formatXAxisTick}
            />
            <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} />
            <Tooltip {...tooltipProps} />
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              fill={`${color}20`}
              strokeWidth={2}
            />
            {showPeaksValleys && displayData.map((point, index) => {
              if (point.peak) {
                return (
                  <ReferenceLine
                    key={`peak-${index}`}
                    x={point.timestamp}
                    stroke="#ef4444"
                    strokeWidth={2}
                    label={{ value: "PEAK", position: "top", fill: "#ef4444" }}
                  />
                );
              }
              if (point.valley) {
                return (
                  <ReferenceLine
                    key={`valley-${index}`}
                    x={point.timestamp}
                    stroke="#10b981"
                    strokeWidth={2}
                    label={{ value: "VALLEY", position: "bottom", fill: "#10b981" }}
                  />
                );
              }
              return null;
            })}
          </AreaChart>
        );

      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="timestamp"
              tick={{ fontSize: 12, fill: '#9ca3af' }}
              tickFormatter={formatXAxisTick}
            />
            <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} />
            <Tooltip {...tooltipProps} />
            <Bar dataKey="value" fill={color} />
          </BarChart>
        );

      case 'composed':
        return (
          <ComposedChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="timestamp"
              tick={{ fontSize: 12, fill: '#9ca3af' }}
              tickFormatter={formatXAxisTick}
            />
            <YAxis yAxisId="left" tick={{ fontSize: 12, fill: '#9ca3af' }} />
            {showVelocity && <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12, fill: '#9ca3af' }} />}
            <Tooltip {...tooltipProps} />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="value"
              stroke={color}
              fill={`${color}20`}
              strokeWidth={2}
            />
            {showVelocity && (
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="velocity"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
              />
            )}
          </ComposedChart>
        );

      default: // line
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="timestamp"
              tick={{ fontSize: 12, fill: '#9ca3af' }}
              tickFormatter={formatXAxisTick}
            />
            <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} />
            <Tooltip {...tooltipProps} />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={{ r: 3, fill: color }}
              activeDot={{ r: 5, fill: color }}
            />
            {showPeaksValleys && displayData.map((point, index) => {
              if (point.peak) {
                return (
                  <ReferenceLine
                    key={`peak-${index}`}
                    x={point.timestamp}
                    stroke="#ef4444"
                    strokeWidth={2}
                    label={{ value: "PEAK", position: "top", fill: "#ef4444" }}
                  />
                );
              }
              if (point.valley) {
                return (
                  <ReferenceLine
                    key={`valley-${index}`}
                    x={point.timestamp}
                    stroke="#10b981"
                    strokeWidth={2}
                    label={{ value: "VALLEY", position: "bottom", fill: "#10b981" }}
                  />
                );
              }
              return null;
            })}
          </LineChart>
        );
    }
  };

  return (
    <div className="enterprise-card enterprise-fade-in overflow-hidden" ref={chartRef}>
      <div className="border-b border-border p-6 bg-gradient-to-r from-primary/5 to-accent/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              {chartType === 'bar' && <BarChart3 className="w-5 h-5 text-primary" />}
              {chartType === 'area' && <Activity className="w-5 h-5 text-primary" />}
              {(chartType === 'line' || chartType === 'composed') && <TrendingUp className="w-5 h-5 text-primary" />}
            </div>
            <div>
              <h3 className="text-lg font-bold text-foreground">{title}</h3>
              <p className="text-sm text-muted-foreground">Interactive trend analysis</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Chart Type Selector */}
            <select
              value={chartType}
              onChange={(e) => {/* TODO: Implement chart type change */}}
              className="enterprise-card px-3 py-2 text-sm font-medium min-w-[100px]"
            >
              <option value="line">Line</option>
              <option value="area">Area</option>
              <option value="bar">Bar</option>
              <option value="composed">Composed</option>
            </select>

            {/* Zoom Controls */}
            <div className="flex items-center gap-1 p-1 bg-card border border-border rounded-lg">
              <button
                onClick={handleZoomIn}
                className="p-2 rounded-md hover:bg-primary/10 transition-colors duration-200"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={handleZoomOut}
                className="p-2 rounded-md hover:bg-primary/10 transition-colors duration-200"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={handleResetZoom}
                className="p-2 rounded-md hover:bg-primary/10 transition-colors duration-200"
                title="Reset Zoom"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>

            {/* Export Options */}
            {onExport && (
              <button
                onClick={() => onExport('png')}
                className="p-2 rounded-lg bg-primary/10 border border-primary/20 hover:bg-primary/20 transition-colors duration-200"
                title="Export as PNG"
              >
                <Download className="w-4 h-4 text-primary" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div style={{ height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          {renderChart()}
        </ResponsiveContainer>
      </div>

      {/* Brush for time range selection */}
      {data.length > 20 && (
        <div className="mt-6 p-4 bg-card/50 rounded-lg border border-border">
          <div className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            Time Range Selector
          </div>
          <ResponsiveContainer width="100%" height={60}>
            <AreaChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <Area
                type="monotone"
                dataKey="value"
                stroke={color}
                fill={`${color}10`}
                strokeWidth={1}
              />
              <Brush
                dataKey="timestamp"
                height={30}
                stroke={color}
                onChange={handleBrushChange}
                tickFormatter={formatXAxisTick}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Chart Statistics */}
      <div className="mt-6 grid grid-cols-4 gap-4 p-4 bg-card/50 rounded-lg border border-border">
        <div className="text-center p-3 rounded-lg bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20">
          <div className="text-lg font-bold text-green-400">
            {Math.max(...displayData.map(d => d.value)).toFixed(1)}
          </div>
          <div className="text-xs font-medium text-muted-foreground">Peak Value</div>
        </div>
        <div className="text-center p-3 rounded-lg bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20">
          <div className="text-lg font-bold text-blue-400">
            {(displayData.reduce((sum, d) => sum + d.value, 0) / displayData.length).toFixed(1)}
          </div>
          <div className="text-xs font-medium text-muted-foreground">Average</div>
        </div>
        <div className="text-center p-3 rounded-lg bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20">
          <div className="text-lg font-bold text-purple-400">
            {displayData.length}
          </div>
          <div className="text-xs font-medium text-muted-foreground">Data Points</div>
        </div>
        <div className="text-center p-3 rounded-lg bg-gradient-to-br from-orange-500/10 to-orange-600/10 border border-orange-500/20">
          <div className="text-lg font-bold text-orange-400">
            {((Math.max(...displayData.map(d => d.value)) - Math.min(...displayData.map(d => d.value))) / Math.min(...displayData.map(d => d.value)) * 100).toFixed(1)}%
          </div>
          <div className="text-xs font-medium text-muted-foreground">Range</div>
        </div>
      </div>
    </div>
  );
}