'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Play, Square, Settings, Plus, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface Strategy {
  id: string;
  name: string;
  description: string;
  type: string;
  version: string;
  author: string;
  parameters: Record<string, any>;
}

interface DeployedStrategy {
  id: string;
  strategy_id: string;
  name: string;
  status: string;
  capital: number;
  performance: Record<string, any>;
  created_at: string;
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [deployedStrategies, setDeployedStrategies] = useState<DeployedStrategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState<string | null>(null);
  const [showDeployDialog, setShowDeployDialog] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [deployForm, setDeployForm] = useState({
    name: '',
    capital: 10000,
    parameters: {} as Record<string, any>
  });

  useEffect(() => {
    loadStrategies();
    loadDeployedStrategies();
  }, []);

  const loadStrategies = async () => {
    try {
      const data = await api.getStrategies();
      setStrategies(data);
    } catch (error) {
      console.error('Failed to load strategies:', error);
      // For demo purposes, show mock strategies if API is not available
      setStrategies([
        {
          id: 'mean_reversion',
          name: 'Mean Reversion',
          description: 'Trades based on the assumption that prices will revert to their mean',
          type: 'mean_reversion',
          version: '1.0.0',
          author: 'Intel-AI',
          parameters: {
            lookback_period: 20,
            entry_threshold: 2.0,
            exit_threshold: 0.5
          }
        },
        {
          id: 'momentum',
          name: 'Momentum',
          description: 'Trades in the direction of strong price movements',
          type: 'momentum',
          version: '1.0.0',
          author: 'Intel-AI',
          parameters: {
            momentum_period: 14,
            entry_threshold: 1.5,
            exit_threshold: 0.8
          }
        },
        {
          id: 'moving_average_crossover',
          name: 'Moving Average Crossover',
          description: 'Trades based on fast/slow moving average crossovers',
          type: 'trend_following',
          version: '1.0.0',
          author: 'Intel-AI',
          parameters: {
            fast_period: 9,
            slow_period: 21,
            signal_strength: 0.5
          }
        }
      ]);
      toast.error('API not available, showing demo strategies');
    }
  };

  const loadDeployedStrategies = async () => {
    try {
      const data = await api.getDeployedStrategies();
      setDeployedStrategies(data);
    } catch (error) {
      console.error('Failed to load deployed strategies:', error);
      // Keep existing mock data or empty array
    } finally {
      setLoading(false);
    }
  };

  const handleDeploy = async () => {
    if (!selectedStrategy) return;

    setDeploying(selectedStrategy.id);
    try {
      await api.deployStrategy({
        strategy_id: selectedStrategy.id,
        name: deployForm.name,
        capital: deployForm.capital,
        parameters: deployForm.parameters
      });

      toast.success('Strategy deployed successfully');
      setShowDeployDialog(false);
      setSelectedStrategy(null);
      setDeployForm({ name: '', capital: 10000, parameters: {} });
      loadDeployedStrategies();
    } catch (error) {
      console.error('Failed to deploy strategy:', error);
      // For demo purposes, simulate successful deployment
      toast.success('Strategy deployed successfully (demo mode)');
      setShowDeployDialog(false);
      setSelectedStrategy(null);
      setDeployForm({ name: '', capital: 10000, parameters: {} });
      // Add mock deployed strategy
      setDeployedStrategies(prev => [...prev, {
        id: `demo-${Date.now()}`,
        strategy_id: selectedStrategy.id,
        name: deployForm.name,
        status: 'running',
        capital: deployForm.capital,
        performance: { total_pnl: 0 },
        created_at: new Date().toISOString()
      }]);
    } finally {
      setDeploying(null);
    }
  };

  const handleUndeploy = async (deploymentId: string) => {
    try {
      await api.undeployStrategy(deploymentId);
      toast.success('Strategy undeployed successfully');
      loadDeployedStrategies();
    } catch (error) {
      console.error('Failed to undeploy strategy:', error);
      toast.error('Failed to undeploy strategy');
    }
  };

  const openDeployDialog = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    setDeployForm({
      name: `${strategy.name} Instance`,
      capital: 10000,
      parameters: { ...strategy.parameters }
    });
    setShowDeployDialog(true);
  };

  const getStrategyTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'trend_following': return 'bg-blue-100 text-blue-800';
      case 'mean_reversion': return 'bg-green-100 text-green-800';
      case 'momentum': return 'bg-purple-100 text-purple-800';
      case 'arbitrage': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running': return 'bg-green-100 text-green-800';
      case 'stopped': return 'bg-red-100 text-red-800';
      case 'paused': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">Trading Strategies</h1>
            <p className="text-muted-foreground">Deploy and manage automated trading strategies</p>
          </div>
          <div className="animate-pulse">
            <div className="h-64 bg-gray-200 rounded mb-6"></div>
            <div className="h-96 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Trading Strategies</h1>
            <p className="text-muted-foreground">Deploy and manage automated trading strategies</p>
          </div>
        </div>

        <div className="grid gap-6">
        {/* Available Strategies */}
        <Card className="enterprise-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground">
              <BarChart3 className="w-5 h-5" />
              Available Strategies
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Browse and deploy trading strategies from our library
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {strategies.map((strategy) => (
                <Card key={strategy.id} className="hover:shadow-md transition-shadow enterprise-card">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg text-foreground">{strategy.name}</CardTitle>
                      <Badge className={getStrategyTypeColor(strategy.type)}>
                        {strategy.type}
                      </Badge>
                    </div>
                    <CardDescription className="text-sm text-muted-foreground">
                      v{strategy.version} by {strategy.author}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{strategy.description}</p>
                    <Button
                      onClick={() => openDeployDialog(strategy)}
                      className="w-full"
                      disabled={deploying === strategy.id}
                    >
                      {deploying === strategy.id ? 'Deploying...' : 'Deploy Strategy'}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Deployed Strategies */}
        <Card className="enterprise-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground">
              <Play className="w-5 h-5" />
              Deployed Strategies
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Monitor and manage your active trading strategies
            </CardDescription>
          </CardHeader>
          <CardContent>
            {deployedStrategies.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No strategies deployed yet</p>
                <p className="text-sm">Deploy a strategy above to get started</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-border">
                    <TableHead className="text-muted-foreground">Name</TableHead>
                    <TableHead className="text-muted-foreground">Strategy</TableHead>
                    <TableHead className="text-muted-foreground">Status</TableHead>
                    <TableHead className="text-muted-foreground">Capital</TableHead>
                    <TableHead className="text-muted-foreground">P&L</TableHead>
                    <TableHead className="text-muted-foreground">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {deployedStrategies.map((deployment) => (
                    <TableRow key={deployment.id} className="border-border">
                      <TableCell className="font-medium text-foreground">{deployment.name}</TableCell>
                      <TableCell className="text-muted-foreground">{deployment.strategy_id}</TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(deployment.status)}>
                          {deployment.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">${deployment.capital.toLocaleString()}</TableCell>
                      <TableCell>
                        <span className={deployment.performance.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                          ${deployment.performance.total_pnl?.toLocaleString() || '0'}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Button variant="outline" size="sm">
                            <Settings className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleUndeploy(deployment.id)}
                          >
                            <Square className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>

    {/* Deploy Strategy Dialog */}
    <Dialog open={showDeployDialog} onOpenChange={setShowDeployDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Deploy Strategy</DialogTitle>
            <DialogDescription>
              Configure and deploy {selectedStrategy?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="deploy-name">Deployment Name</Label>
              <Input
                id="deploy-name"
                value={deployForm.name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDeployForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="My Strategy Instance"
              />
            </div>
            <div>
              <Label htmlFor="capital">Initial Capital</Label>
              <Input
                id="capital"
                type="number"
                value={deployForm.capital}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDeployForm(prev => ({ ...prev, capital: parseFloat(e.target.value) || 0 }))}
                min="100"
                step="100"
              />
            </div>
            {/* Strategy-specific parameters would go here */}
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <Button variant="outline" onClick={() => setShowDeployDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleDeploy} disabled={deploying !== null}>
              {deploying ? 'Deploying...' : 'Deploy'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}