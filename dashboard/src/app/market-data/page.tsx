'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, BarChart3, Activity, RefreshCw, DollarSign, Bitcoin, PieChart } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar, Cell } from 'recharts';
import { api } from '@/lib/api';
import { RefreshButton } from '@/components/Loading';

// Mock market data - in a real app, this would come from APIs
const mockStockData = [
  { symbol: 'AAPL', name: 'Apple Inc.', price: 182.52, change: 2.34, changePercent: 1.30, volume: '45.2M' },
  { symbol: 'MSFT', name: 'Microsoft Corp.', price: 415.26, change: -1.23, changePercent: -0.30, volume: '18.7M' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 141.80, change: 3.45, changePercent: 2.49, volume: '22.1M' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 155.89, change: -0.67, changePercent: -0.43, volume: '31.5M' },
  { symbol: 'TSLA', name: 'Tesla Inc.', price: 248.42, change: 5.67, changePercent: 2.34, volume: '89.3M' },
];

const mockCryptoData = [
  { symbol: 'BTC', name: 'Bitcoin', price: 43250.00, change: 1250.50, changePercent: 2.98, marketCap: '845B' },
  { symbol: 'ETH', name: 'Ethereum', price: 2650.75, change: -45.25, changePercent: -1.68, marketCap: '318B' },
  { symbol: 'BNB', name: 'Binance Coin', price: 315.20, change: 8.90, changePercent: 2.91, marketCap: '47B' },
  { symbol: 'ADA', name: 'Cardano', price: 0.52, change: 0.02, changePercent: 4.00, marketCap: '18B' },
  { symbol: 'SOL', name: 'Solana', price: 98.45, change: -2.15, changePercent: -2.14, marketCap: '43B' },
];

// Mock chart data
const mockChartData = [
  { time: '09:00', price: 182.00, volume: 1200000 },
  { time: '10:00', price: 183.50, volume: 1500000 },
  { time: '11:00', price: 181.80, volume: 980000 },
  { time: '12:00', price: 184.20, volume: 2100000 },
  { time: '13:00', price: 185.10, volume: 1750000 },
  { time: '14:00', price: 183.90, volume: 1320000 },
  { time: '15:00', price: 182.52, volume: 1890000 },
];

const mockCryptoChartData = [
  { time: '00:00', price: 42500, volume: 25000000 },
  { time: '04:00', price: 42800, volume: 18000000 },
  { time: '08:00', price: 43100, volume: 32000000 },
  { time: '12:00', price: 42900, volume: 28000000 },
  { time: '16:00', price: 43200, volume: 35000000 },
  { time: '20:00', price: 43250, volume: 29000000 },
];

export default function MarketDataPage() {
  const [refreshing, setRefreshing] = useState(false);
  const [selectedTimeframe, setSelectedTimeframe] = useState<'1D' | '1W' | '1M' | '3M'>('1D');
  const [selectedAsset, setSelectedAsset] = useState<'stocks' | 'crypto'>('stocks');

  const handleRefresh = () => {
    setRefreshing(true);
    // In a real app, this would refresh market data
    setTimeout(() => setRefreshing(false), 1000);
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: price < 1 ? 4 : 2,
    }).format(price);
  };

  const formatVolume = (volume: string | number) => {
    if (typeof volume === 'string') return volume;
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(1)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  return (
    <div className="space-y-8" id="main-content">
      {/* Professional Header */}
      <div className="flex items-center justify-between pb-6 border-b border-border">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold text-foreground tracking-tight flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-primary" />
            Market Data
          </h1>
          <p className="text-muted-foreground">
            Real-time market data, charts, and analysis for stocks and cryptocurrencies
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

      {/* Market Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="enterprise-card p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-green-100 dark:bg-green-900/20">
              <TrendingUp className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">S&P 500</p>
              <p className="text-lg font-semibold text-green-600 dark:text-green-400">4,847.35</p>
              <p className="text-xs text-green-600 dark:text-green-400">+0.85%</p>
            </div>
          </div>
        </div>

        <div className="enterprise-card p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-blue-100 dark:bg-blue-900/20">
              <Bitcoin className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Bitcoin</p>
              <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">$43,250</p>
              <p className="text-xs text-green-600 dark:text-green-400">+2.98%</p>
            </div>
          </div>
        </div>

        <div className="enterprise-card p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-purple-100 dark:bg-purple-900/20">
              <Activity className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">VIX</p>
              <p className="text-lg font-semibold text-purple-600 dark:text-purple-400">14.23</p>
              <p className="text-xs text-red-600 dark:text-red-400">-1.24%</p>
            </div>
          </div>
        </div>

        <div className="enterprise-card p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-orange-100 dark:bg-orange-900/20">
              <DollarSign className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Market Cap</p>
              <p className="text-lg font-semibold text-orange-600 dark:text-orange-400">$45.2T</p>
              <p className="text-xs text-green-600 dark:text-green-400">+1.15%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Asset Type Selector */}
      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setSelectedAsset('stocks')}
          className={`px-6 py-3 rounded-lg font-medium transition-colors ${
            selectedAsset === 'stocks'
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          📈 Stocks
        </button>
        <button
          onClick={() => setSelectedAsset('crypto')}
          className={`px-6 py-3 rounded-lg font-medium transition-colors ${
            selectedAsset === 'crypto'
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          ₿ Crypto
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <div className="lg:col-span-2">
          <div className="enterprise-card p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">
                {selectedAsset === 'stocks' ? 'AAPL' : 'BTC'} Price Chart
              </h3>
              <div className="flex gap-2">
                {(['1D', '1W', '1M', '3M'] as const).map((timeframe) => (
                  <button
                    key={timeframe}
                    onClick={() => setSelectedTimeframe(timeframe)}
                    className={`px-3 py-1 text-sm rounded ${
                      selectedTimeframe === timeframe
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                  >
                    {timeframe}
                  </button>
                ))}
              </div>
            </div>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={selectedAsset === 'stocks' ? mockChartData : mockCryptoChartData}>
                  <defs>
                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis dataKey="time" />
                  <YAxis domain={['dataMin - 5', 'dataMax + 5']} />
                  <Tooltip
                    formatter={(value: any) => [formatPrice(value), 'Price']}
                    labelFormatter={(label) => `Time: ${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="price"
                    stroke="#3b82f6"
                    fillOpacity={1}
                    fill="url(#priceGradient)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Top Assets Table */}
        <div className="lg:col-span-1">
          <div className="enterprise-card p-6">
            <h3 className="text-lg font-semibold mb-4">
              Top {selectedAsset === 'stocks' ? 'Stocks' : 'Cryptocurrencies'}
            </h3>
            <div className="space-y-3">
              {(selectedAsset === 'stocks' ? mockStockData : mockCryptoData).map((asset) => (
                <div key={asset.symbol} className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted/80 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-semibold">
                      {asset.symbol.slice(0, 2)}
                    </div>
                    <div>
                      <p className="font-medium text-sm">{asset.symbol}</p>
                      <p className="text-xs text-muted-foreground truncate max-w-20">{asset.name}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-sm">{formatPrice(asset.price)}</p>
                    <p className={`text-xs flex items-center gap-1 ${
                      asset.changePercent >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {asset.changePercent >= 0 ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      {asset.changePercent >= 0 ? '+' : ''}{asset.changePercent.toFixed(2)}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Volume Chart */}
      <div className="enterprise-card p-6">
        <h3 className="text-lg font-semibold mb-6">Trading Volume</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={selectedAsset === 'stocks' ? mockChartData : mockCryptoChartData}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip
                formatter={(value: any) => [formatVolume(value), 'Volume']}
                labelFormatter={(label) => `Time: ${label}`}
              />
              <Bar dataKey="volume" fill="#3b82f6" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Market Sentiment Indicator */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="enterprise-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <PieChart className="w-5 h-5 text-green-600" />
            <h4 className="font-semibold">Market Sentiment</h4>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Bullish</span>
              <span className="text-sm font-medium">68%</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-green-600 h-2 rounded-full" style={{ width: '68%' }}></div>
            </div>
          </div>
        </div>

        <div className="enterprise-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="w-5 h-5 text-blue-600" />
            <h4 className="font-semibold">Volatility Index</h4>
          </div>
          <div className="text-2xl font-bold text-blue-600">14.23</div>
          <p className="text-sm text-muted-foreground">Low volatility</p>
        </div>

        <div className="enterprise-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <BarChart3 className="w-5 h-5 text-purple-600" />
            <h4 className="font-semibold">Market Breadth</h4>
          </div>
          <div className="text-2xl font-bold text-purple-600">+1.2%</div>
          <p className="text-sm text-muted-foreground">Stocks up vs down</p>
        </div>
      </div>
    </div>
  );
}