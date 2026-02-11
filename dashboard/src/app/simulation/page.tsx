"use client";
import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Play, Square, Trash2, Plus, TrendingUp, TrendingDown } from 'lucide-react';
import { toast } from 'sonner';

interface SimulationSession {
  id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
  initial_balance: number;
  current_balance: number;
  total_return: number;
  total_trades: number;
}

interface SimulationOrder {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  order_type: string;
  price: number | null;
  status: string;
  executed_at: string | null;
  execution_price: number | null;
}

interface SimulationPosition {
  id: string;
  symbol: string;
  quantity: number;
  average_cost: number;
  current_price: number | null;
  market_value: number | null;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
}

interface SimulationMetrics {
  total_return: number;
  total_return_percent: number;
  sharpe_ratio: number | null;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  avg_trade_return: number;
  largest_win: number;
  largest_loss: number;
}

export default function SimulationPage() {
  const [sessions, setSessions] = useState<SimulationSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<SimulationSession | null>(null);
  const [orders, setOrders] = useState<SimulationOrder[]>([]);
  const [positions, setPositions] = useState<SimulationPosition[]>([]);
  const [metrics, setMetrics] = useState<SimulationMetrics | null>(null);
  const [loading, setLoading] = useState(false);

  // New session form
  const [newSession, setNewSession] = useState({
    name: '',
    description: '',
    initial_balance: 100000,
  });

  // New order form
  const [newOrder, setNewOrder] = useState({
    symbol: '',
    side: 'buy' as 'buy' | 'sell',
    quantity: 1,
    order_type: 'market' as 'market' | 'limit',
    price: '',
  });

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const response = await fetch('/api/trading/simulations');
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      toast.error('Failed to load simulations');
    }
  };

  const createSession = async () => {
    if (!newSession.name.trim()) {
      toast.error('Please enter a simulation name');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/trading/simulations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSession),
      });

      if (response.ok) {
        toast.success('Simulation created successfully');
        setNewSession({ name: '', description: '', initial_balance: 100000 });
        loadSessions();
      } else {
        toast.error('Failed to create simulation');
      }
    } catch (error) {
      toast.error('Failed to create simulation');
    } finally {
      setLoading(false);
    }
  };

  const startSession = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/trading/simulations/${sessionId}/start`, {
        method: 'POST',
      });

      if (response.ok) {
        toast.success('Simulation started');
        loadSessions();
        if (selectedSession?.id === sessionId) {
          loadSessionDetails(sessionId);
        }
      } else {
        toast.error('Failed to start simulation');
      }
    } catch (error) {
      toast.error('Failed to start simulation');
    }
  };

  const stopSession = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/trading/simulations/${sessionId}/stop`, {
        method: 'POST',
      });

      if (response.ok) {
        toast.success('Simulation stopped');
        loadSessions();
        if (selectedSession?.id === sessionId) {
          loadSessionDetails(sessionId);
        }
      } else {
        toast.error('Failed to stop simulation');
      }
    } catch (error) {
      toast.error('Failed to stop simulation');
    }
  };

  const deleteSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this simulation?')) return;

    try {
      const response = await fetch(`/api/trading/simulations/${sessionId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast.success('Simulation deleted');
        loadSessions();
        if (selectedSession?.id === sessionId) {
          setSelectedSession(null);
        }
      } else {
        toast.error('Failed to delete simulation');
      }
    } catch (error) {
      toast.error('Failed to delete simulation');
    }
  };

  const loadSessionDetails = async (sessionId: string) => {
    try {
      // Load session info
      const sessionResponse = await fetch(`/api/trading/simulations/${sessionId}`);
      if (sessionResponse.ok) {
        const sessionData = await sessionResponse.json();
        setSelectedSession(sessionData);
      }

      // Load orders
      const ordersResponse = await fetch(`/api/trading/simulations/${sessionId}/orders`);
      if (ordersResponse.ok) {
        const ordersData = await ordersResponse.json();
        setOrders(ordersData);
      }

      // Load positions
      const positionsResponse = await fetch(`/api/trading/simulations/${sessionId}/positions`);
      if (positionsResponse.ok) {
        const positionsData = await positionsResponse.json();
        setPositions(positionsData);
      }

      // Load metrics
      const metricsResponse = await fetch(`/api/trading/simulations/${sessionId}/metrics`);
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData);
      }
    } catch (error) {
      toast.error('Failed to load session details');
    }
  };

  const placeOrder = async () => {
    if (!selectedSession || selectedSession.status !== 'running') {
      toast.error('Simulation must be running to place orders');
      return;
    }

    if (!newOrder.symbol.trim()) {
      toast.error('Please enter a symbol');
      return;
    }

    if (newOrder.quantity <= 0) {
      toast.error('Quantity must be positive');
      return;
    }

    setLoading(true);
    try {
      const orderData = {
        ...newOrder,
        price: newOrder.order_type === 'limit' ? parseFloat(newOrder.price) : null,
      };

      const response = await fetch(`/api/trading/simulations/${selectedSession.id}/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData),
      });

      if (response.ok) {
        toast.success('Order placed successfully');
        setNewOrder({
          symbol: '',
          side: 'buy',
          quantity: 1,
          order_type: 'market',
          price: '',
        });
        loadSessionDetails(selectedSession.id);
      } else {
        toast.error('Failed to place order');
      }
    } catch (error) {
      toast.error('Failed to place order');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      pending: 'secondary',
      running: 'default',
      completed: 'outline',
      failed: 'destructive',
    } as const;

    return <Badge variant={variants[status as keyof typeof variants] || 'secondary'}>{status}</Badge>;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Paper Trading Simulation</h1>
          <p className="text-muted-foreground">Test trading strategies risk-free with realistic market conditions</p>
        </div>

        <Dialog>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              New Simulation
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Simulation</DialogTitle>
              <DialogDescription>
                Set up a new paper trading simulation with custom parameters.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">Simulation Name</Label>
                <Input
                  id="name"
                  value={newSession.name}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewSession(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="My Trading Strategy Test"
                />
              </div>
              <div>
                <Label htmlFor="description">Description (Optional)</Label>
                <Input
                  id="description"
                  value={newSession.description}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewSession(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Testing momentum strategy with tech stocks"
                />
              </div>
              <div>
                <Label htmlFor="balance">Initial Balance ($)</Label>
                <Input
                  id="balance"
                  type="number"
                  value={newSession.initial_balance}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewSession(prev => ({ ...prev, initial_balance: parseInt(e.target.value) || 100000 }))}
                />
              </div>
              <Button onClick={createSession} disabled={loading} className="w-full">
                {loading ? 'Creating...' : 'Create Simulation'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sessions List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Simulations</CardTitle>
            <CardDescription>Your paper trading sessions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                    selectedSession?.id === session.id ? 'border-primary bg-primary/5' : 'hover:bg-muted'
                  }`}
                  onClick={() => loadSessionDetails(session.id)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium">{session.name}</h4>
                      <p className="text-sm text-muted-foreground">{session.description}</p>
                    </div>
                    {getStatusBadge(session.status)}
                  </div>
                  <div className="mt-2 text-sm">
                    <div>Balance: ${session.current_balance.toLocaleString()}</div>
                    <div>Trades: {session.total_trades}</div>
                    <div className={session.total_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                      Return: {session.total_return.toFixed(2)}%
                    </div>
                  </div>
                </div>
              ))}
              {sessions.length === 0 && (
                <p className="text-center text-muted-foreground py-8">
                  No simulations yet. Create your first one!
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Session Details */}
        <Card className="lg:col-span-2">
          {selectedSession ? (
            <>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{selectedSession.name}</CardTitle>
                    <CardDescription>{selectedSession.description}</CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(selectedSession.status)}
                    {selectedSession.status === 'pending' && (
                      <Button size="sm" onClick={() => startSession(selectedSession.id)}>
                        <Play className="w-4 h-4 mr-1" />
                        Start
                      </Button>
                    )}
                    {selectedSession.status === 'running' && (
                      <Button size="sm" variant="outline" onClick={() => stopSession(selectedSession.id)}>
                        <Square className="w-4 h-4 mr-1" />
                        Stop
                      </Button>
                    )}
                    <Button size="sm" variant="destructive" onClick={() => deleteSession(selectedSession.id)}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="overview" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="orders">Orders</TabsTrigger>
                    <TabsTrigger value="positions">Positions</TabsTrigger>
                    <TabsTrigger value="trade">Trade</TabsTrigger>
                  </TabsList>

                  <TabsContent value="overview" className="space-y-4">
                    {metrics && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <Card>
                          <CardContent className="p-4">
                            <div className="text-2xl font-bold">
                              ${selectedSession.current_balance.toLocaleString()}
                            </div>
                            <p className="text-sm text-muted-foreground">Current Balance</p>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardContent className="p-4">
                            <div className={`text-2xl font-bold ${metrics.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {metrics.total_return.toFixed(2)}%
                            </div>
                            <p className="text-sm text-muted-foreground">Total Return</p>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardContent className="p-4">
                            <div className="text-2xl font-bold">{metrics.total_trades}</div>
                            <p className="text-sm text-muted-foreground">Total Trades</p>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardContent className="p-4">
                            <div className="text-2xl font-bold">{metrics.win_rate.toFixed(1)}%</div>
                            <p className="text-sm text-muted-foreground">Win Rate</p>
                          </CardContent>
                        </Card>
                      </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">Performance Metrics</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                          {metrics && (
                            <>
                              <div className="flex justify-between">
                                <span>Sharpe Ratio:</span>
                                <span>{metrics.sharpe_ratio?.toFixed(2) || 'N/A'}</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Max Drawdown:</span>
                                <span className="text-red-600">{metrics.max_drawdown.toFixed(2)}%</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Avg Trade Return:</span>
                                <span className={metrics.avg_trade_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                                  {metrics.avg_trade_return.toFixed(2)}%
                                </span>
                              </div>
                            </>
                          )}
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">Best/Worst Trades</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                          {metrics && (
                            <>
                              <div className="flex justify-between">
                                <span>Largest Win:</span>
                                <span className="text-green-600">${metrics.largest_win.toFixed(2)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Largest Loss:</span>
                                <span className="text-red-600">${metrics.largest_loss.toFixed(2)}</span>
                              </div>
                            </>
                          )}
                        </CardContent>
                      </Card>
                    </div>
                  </TabsContent>

                  <TabsContent value="orders">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Side</TableHead>
                          <TableHead>Quantity</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Price</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Time</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {orders.map((order) => (
                          <TableRow key={order.id}>
                            <TableCell className="font-medium">{order.symbol}</TableCell>
                            <TableCell>
                              <Badge variant={order.side === 'buy' ? 'default' : 'secondary'}>
                                {order.side.toUpperCase()}
                              </Badge>
                            </TableCell>
                            <TableCell>{order.quantity}</TableCell>
                            <TableCell>{order.order_type}</TableCell>
                            <TableCell>${order.execution_price?.toFixed(2) || 'N/A'}</TableCell>
                            <TableCell>{getStatusBadge(order.status)}</TableCell>
                            <TableCell>{order.executed_at ? new Date(order.executed_at).toLocaleString() : 'N/A'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TabsContent>

                  <TabsContent value="positions">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Quantity</TableHead>
                          <TableHead>Avg Cost</TableHead>
                          <TableHead>Current Price</TableHead>
                          <TableHead>Market Value</TableHead>
                          <TableHead>P&L</TableHead>
                          <TableHead>P&L %</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {positions.map((position) => (
                          <TableRow key={position.id}>
                            <TableCell className="font-medium">{position.symbol}</TableCell>
                            <TableCell>{position.quantity}</TableCell>
                            <TableCell>${position.average_cost.toFixed(2)}</TableCell>
                            <TableCell>${position.current_price?.toFixed(2) || 'N/A'}</TableCell>
                            <TableCell>${position.market_value?.toFixed(2) || 'N/A'}</TableCell>
                            <TableCell className={position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                              ${position.unrealized_pnl.toFixed(2)}
                            </TableCell>
                            <TableCell className={position.unrealized_pnl_percent >= 0 ? 'text-green-600' : 'text-red-600'}>
                              {position.unrealized_pnl_percent.toFixed(2)}%
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TabsContent>

                  <TabsContent value="trade" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle>Place Order</CardTitle>
                        <CardDescription>Enter order details for paper trading</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label htmlFor="symbol">Symbol</Label>
                            <Input
                              id="symbol"
                              value={newOrder.symbol}
                               onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewOrder(prev => ({ ...prev, symbol: e.target.value.toUpperCase() }))}
                              placeholder="AAPL"
                            />
                          </div>
                          <div>
                            <Label htmlFor="side">Side</Label>
                            <Select value={newOrder.side} onValueChange={(value: string) => setNewOrder(prev => ({ ...prev, side: value as 'buy' | 'sell' }))}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="buy">Buy</SelectItem>
                                <SelectItem value="sell">Sell</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label htmlFor="quantity">Quantity</Label>
                            <Input
                              id="quantity"
                              type="number"
                              value={newOrder.quantity}
                               onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewOrder(prev => ({ ...prev, quantity: parseInt(e.target.value) || 1 }))}
                              min="1"
                            />
                          </div>
                          <div>
                            <Label htmlFor="order_type">Order Type</Label>
                             <Select value={newOrder.order_type} onValueChange={(value: string) => setNewOrder(prev => ({ ...prev, order_type: value as 'market' | 'limit' }))}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="market">Market</SelectItem>
                                <SelectItem value="limit">Limit</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        {newOrder.order_type === 'limit' && (
                          <div>
                            <Label htmlFor="price">Limit Price</Label>
                            <Input
                              id="price"
                              type="number"
                              step="0.01"
                              value={newOrder.price}
                               onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewOrder(prev => ({ ...prev, price: e.target.value }))}
                              placeholder="150.00"
                            />
                          </div>
                        )}

                        <Button onClick={placeOrder} disabled={loading} className="w-full">
                          {loading ? 'Placing Order...' : 'Place Order'}
                        </Button>
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </>
          ) : (
            <CardContent>
              <p className="text-center text-muted-foreground py-8">
                Select a simulation to view details
              </p>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  );
}