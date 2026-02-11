'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  BarChart3,
  AlertTriangle,
  RefreshCw,
  Plus,
  Minus
} from 'lucide-react';

interface PortfolioSummary {
  portfolio: {
    id: string;
    name: string;
    cash_balance: number;
    total_value: number;
    unrealized_pnl: number;
    realized_pnl: number;
    currency: string;
    is_paper_trading: boolean;
  };
  positions: Array<{
    symbol: string;
    quantity: number;
    average_cost: number;
    current_price: number | null;
    market_value: number | null;
    unrealized_pnl: number;
    realized_pnl: number;
  }>;
  summary: {
    total_positions: number;
    total_market_value: number;
    total_pnl: number;
  };
}

interface PortfolioComposition {
  cash_balance: number;
  total_value: number;
  positions: Array<{
    symbol: string;
    quantity: number;
    average_cost: number;
    current_price: number | null;
    market_value: number;
    unrealized_pnl: number;
    weight: number;
    pnl_percentage: number;
  }>;
  sector_breakdown: Record<string, number>;
  risk_breakdown: Record<string, number>;
  total_positions: number;
}

interface PortfolioAlerts {
  alerts: Array<{
    type: string;
    severity: 'high' | 'medium' | 'low';
    message: string;
    symbol?: string;
    value: number;
  }>;
  total_alerts: number;
  high_severity: number;
  medium_severity: number;
}

interface PerformanceMetrics {
  total_return: number;
  period_days: number;
  sharpe_ratio: number | null;
  win_rate: number;
  total_trades: number;
}

export default function PortfolioPage() {
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const [composition, setComposition] = useState<PortfolioComposition | null>(null);
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null);
  const [alerts, setAlerts] = useState<PortfolioAlerts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);

      // First get the user's portfolio
      const portfolioResponse = await fetch('/api/trading/portfolios');
      if (!portfolioResponse.ok) throw new Error('Failed to fetch portfolios');
      const portfolios = await portfolioResponse.json();

      if (portfolios.length === 0) {
        setError('No portfolio found. Please create a portfolio first.');
        return;
      }

      const portfolioId = portfolios[0].id;

      // Fetch all portfolio data in parallel
      const [summaryRes, compositionRes, performanceRes, alertsRes] = await Promise.all([
        fetch(`/api/trading/portfolios/${portfolioId}/summary`),
        fetch(`/api/trading/portfolios/${portfolioId}/composition`),
        fetch(`/api/trading/portfolios/${portfolioId}/performance`),
        fetch(`/api/trading/portfolios/${portfolioId}/alerts`)
      ]);

      if (summaryRes.ok) {
        const summaryData = await summaryRes.json();
        setPortfolioSummary(summaryData);
      }

      if (compositionRes.ok) {
        const compositionData = await compositionRes.json();
        setComposition(compositionData);
      }

      if (performanceRes.ok) {
        const performanceData = await performanceRes.json();
        setPerformance(performanceData);
      }

      if (alertsRes.ok) {
        const alertsData = await alertsRes.json();
        setAlerts(alertsData);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load portfolio data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="border border-red-500 rounded-md p-4 flex items-center space-x-2 bg-red-50">
          <AlertTriangle className="h-4 w-4 text-red-500" />
          <span className="text-red-700">{error}</span>
        </div>
      </div>
    );
  }

  if (!portfolioSummary) {
    return (
      <div className="container mx-auto p-6">
        <div className="border border-yellow-500 rounded-md p-4 flex items-center space-x-2 bg-yellow-50">
          <AlertTriangle className="h-4 w-4 text-yellow-500" />
          <span className="text-yellow-700">No portfolio data available.</span>
        </div>
      </div>
    );
  }

  const totalPnl = portfolioSummary.portfolio.unrealized_pnl + portfolioSummary.portfolio.realized_pnl;
  const pnlPercentage = portfolioSummary.portfolio.total_value > 0
    ? (totalPnl / (portfolioSummary.portfolio.total_value - totalPnl)) * 100
    : 0;

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{portfolioSummary.portfolio.name}</h1>
          <p className="text-muted-foreground">
            {portfolioSummary.portfolio.is_paper_trading ? 'Paper Trading' : 'Live Trading'} Portfolio
          </p>
        </div>
        <Button onClick={fetchPortfolioData} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${portfolioSummary.portfolio.total_value.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              {portfolioSummary.portfolio.currency}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cash Balance</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${portfolioSummary.portfolio.cash_balance.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            {totalPnl >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ${totalPnl.toLocaleString()}
            </div>
            <p className={`text-xs ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {pnlPercentage >= 0 ? '+' : ''}{pnlPercentage.toFixed(2)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Positions</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {portfolioSummary.summary.total_positions}
            </div>
            <p className="text-xs text-muted-foreground">
              Active positions
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="positions" className="space-y-4">
        <TabsList>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="composition">Composition</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
        </TabsList>

        <TabsContent value="positions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Current Positions</CardTitle>
              <CardDescription>
                Your active trading positions with real-time P&L
              </CardDescription>
            </CardHeader>
            <CardContent>
              {portfolioSummary.positions.length === 0 ? (
                <p className="text-muted-foreground">No active positions</p>
              ) : (
                <div className="space-y-4">
                  {portfolioSummary.positions.map((position) => (
                    <div key={position.symbol} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div>
                          <h3 className="font-semibold">{position.symbol}</h3>
                          <p className="text-sm text-muted-foreground">
                            {position.quantity} shares @ ${position.average_cost.toFixed(2)}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold">
                          ${position.market_value?.toLocaleString() || 'N/A'}
                        </div>
                        <div className={`text-sm ${position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ${position.unrealized_pnl.toFixed(2)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="composition" className="space-y-4">
          {composition && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Sector Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {Object.entries(composition.sector_breakdown).map(([sector, percentage]) => (
                      <div key={sector} className="flex items-center justify-between mb-2">
                        <span className="text-sm">{sector}</span>
                        <span className="text-sm font-medium">{percentage.toFixed(1)}%</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Risk Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {Object.entries(composition.risk_breakdown).map(([risk, percentage]) => (
                      <div key={risk} className="flex items-center justify-between mb-2">
                        <Badge variant={risk === 'high' ? 'destructive' : risk === 'medium' ? 'default' : 'secondary'}>
                          {risk.toUpperCase()}
                        </Badge>
                        <span className="text-sm font-medium">{(percentage * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Position Weights</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {composition.positions.map((position) => (
                      <div key={position.symbol} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{position.symbol}</span>
                          <span className="text-sm text-muted-foreground">
                            {position.weight.toFixed(1)}%
                          </span>
                        </div>
                        {/* <Progress value={position.weight} className="h-2" /> */}
                        {/* TODO: Uncomment and update the import path above if you have a Progress component */}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          {performance && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle>Total Return</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold ${performance.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {performance.total_return >= 0 ? '+' : ''}{performance.total_return.toFixed(2)}%
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {performance.period_days} days
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Sharpe Ratio</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {performance.sharpe_ratio?.toFixed(2) || 'N/A'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Risk-adjusted returns
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Win Rate</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {performance.win_rate.toFixed(1)}%
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {performance.total_trades} total trades
                  </p>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>
        <TabsContent value="alerts" className="space-y-4">
          {alerts && (
            <>
              {/* Alert Summary */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">Total Alerts</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{alerts.total_alerts}</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">High Severity</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-red-600">{alerts.high_severity}</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">Medium Severity</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-yellow-600">{alerts.medium_severity}</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">Status</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Badge variant={alerts.total_alerts > 0 ? "destructive" : "secondary"}>
                      {alerts.total_alerts > 0 ? "Action Required" : "All Clear"}
                    </Badge>
                  </CardContent>
                </Card>
              </div>

              {/* Alert List */}
              <Card>
                <CardHeader>
                  <CardTitle>Active Alerts</CardTitle>
                  <CardDescription>
                    Portfolio risk warnings and limit violations
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {alerts.alerts.length === 0 ? (
                    <p className="text-muted-foreground">No active alerts</p>
                  ) : (
                    <div className="space-y-4">
                      {alerts.alerts.map((alert, index) => (
                        <div
                          key={index}
                          className={`border rounded-md p-4 flex items-center space-x-2 ${
                            alert.severity === 'high'
                              ? 'border-red-500 bg-red-50'
                              : alert.severity === 'medium'
                              ? 'border-yellow-500 bg-yellow-50'
                              : 'border-blue-500 bg-blue-50'
                          }`}
                        >
                          <AlertTriangle className="h-4 w-4" />
                          <span className="flex-1">
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="font-medium">{alert.message}</div>
                                {alert.symbol && (
                                  <div className="text-sm text-muted-foreground">Symbol: {alert.symbol}</div>
                                )}
                              </div>
                              <Badge
                                variant={
                                  alert.severity === 'high'
                                    ? 'destructive'
                                    : alert.severity === 'medium'
                                    ? 'default'
                                    : 'secondary'
                                }
                              >
                                {alert.severity.toUpperCase()}
                              </Badge>
                            </div>
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}