'use client';

import { useState } from 'react';
import { TrendingUp, RefreshCw } from 'lucide-react';
import GoogleTrendsPanel from '@/components/GoogleTrendsPanel';
import { RefreshButton } from '@/components/Loading';

export default function TrendsPage() {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = () => {
    setRefreshing(true);
    // The GoogleTrendsPanel component handles its own refresh logic
    setTimeout(() => setRefreshing(false), 1000);
  };

  return (
    <div className="space-y-8" id="main-content">
      {/* Professional Header */}
      <div className="flex items-center justify-between pb-6 border-b border-border">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold text-foreground tracking-tight flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-primary" />
            Google Trends Analysis
          </h1>
          <p className="text-muted-foreground">
            Monitor real-time search trends and analyze keyword performance across different regions
          </p>
        </div>
        <div className="flex items-center gap-3">
          <RefreshButton
            onClick={handleRefresh}
            loading={refreshing}
            size="sm"
            className="enterprise-card"
          />
        </div>
      </div>

      {/* Google Trends Panel */}
      <div className="space-y-6">
        <GoogleTrendsPanel />
      </div>
    </div>
  );
}