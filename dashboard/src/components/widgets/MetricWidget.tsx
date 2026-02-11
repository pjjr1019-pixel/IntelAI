'use client';

import React from 'react';
import { Activity, TrendingUp, TrendingDown, AlertTriangle, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { DashboardWidget } from '../DashboardLayoutProvider';

interface MetricWidgetProps {
  widget: DashboardWidget;
  data?: {
    value: number;
    label: string;
    icon?: string;
    color?: string;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: number;
  };
}

const iconMap = {
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
};

export function MetricWidget({ widget, data }: MetricWidgetProps) {
  const IconComponent = data?.icon ? iconMap[data.icon as keyof typeof iconMap] : Activity;
  const colorClass = data?.color ? `text-${data.color}` : 'text-primary';

  const getTrendIcon = () => {
    if (!data?.trend) return null;
    const TrendIcon = data.trend === 'up' ? ArrowUpRight : data.trend === 'down' ? ArrowDownRight : null;
    if (!TrendIcon) return null;
    return <TrendIcon className={`w-4 h-4 ${data.trend === 'up' ? 'text-green-500' : 'text-red-500'}`} />;
  };

  const getTrendColor = () => {
    if (!data?.trend) return '';
    return data.trend === 'up' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="p-6 h-full enterprise-fade-in">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-xl bg-primary/10 ${colorClass}`}>
            <IconComponent className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              {data?.label || widget.title}
            </p>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold text-foreground">
                {data?.value?.toLocaleString() || '0'}
              </p>
              {data?.trendValue && (
                <div className={`flex items-center gap-1 text-sm font-medium ${getTrendColor()}`}>
                  {getTrendIcon()}
                  <span>{Math.abs(data.trendValue)}%</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Progress bar for visual appeal */}
      <div className="mt-4">
        <div className="w-full bg-muted rounded-full h-2">
          <div
            className="bg-primary h-2 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${Math.min(100, (data?.value || 0) / 100 * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}