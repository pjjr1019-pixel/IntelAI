'use client';

import React, { lazy, Suspense } from 'react';
import { TrendingUp } from 'lucide-react';
import { DashboardWidget } from '../DashboardLayoutProvider';

// Lazy load the Google Trends panel
const GoogleTrendsPanel = lazy(() => import('../GoogleTrendsPanel'));

interface ChartWidgetProps {
  widget: DashboardWidget;
}

export function ChartWidget({ widget }: ChartWidgetProps) {
  // For now, we'll only support Google Trends chart
  // In the future, this could be extended to support different chart types
  if (widget.id === 'google-trends' || widget.type === 'chart') {
    return (
      <Suspense fallback={
        <div className="p-8 h-full flex items-center justify-center enterprise-fade-in">
          <div className="text-center space-y-3">
            <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto"></div>
            <p className="text-muted-foreground font-medium">Loading analytics...</p>
          </div>
        </div>
      }>
        <GoogleTrendsPanel />
      </Suspense>
    );
  }

  return (
    <div className="p-8 h-full flex items-center justify-center enterprise-fade-in">
      <div className="text-center space-y-3">
        <div className="p-4 rounded-full bg-muted mx-auto w-fit">
          <TrendingUp className="w-8 h-8 text-muted-foreground" />
        </div>
        <div>
          <p className="font-semibold text-foreground">{widget.title}</p>
          <p className="text-sm text-muted-foreground">Chart type not implemented yet</p>
        </div>
      </div>
    </div>
  );
}