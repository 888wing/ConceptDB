'use client';

import { useQuery } from '@tanstack/react-query';
import { useConceptDB } from '@/lib/conceptdb-context';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Loader2, Database, Brain, Zap, TrendingUp, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

const COLORS = {
  postgres: '#336791',
  concepts: '#8B5CF6',
  hybrid: '#F59E0B',
};

export function MetricsDashboard() {
  const { client, metrics } = useConceptDB();

  const { data: routingStats, isLoading: routingLoading } = useQuery({
    queryKey: ['routing-stats'],
    queryFn: async () => {
      if (!client) return null;
      return await client.evolution.getRoutingStats();
    },
    enabled: !!client,
  });

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: async () => {
      if (!client) return null;
      return await client.health();
    },
    enabled: !!client,
  });

  const { data: optimizations } = useQuery({
    queryKey: ['optimizations'],
    queryFn: async () => {
      if (!client) return null;
      return await client.evolution.getRecommendations();
    },
    enabled: !!client,
  });

  if (routingLoading || healthLoading) {
    return (
      <div className="flex items-center justify-center h-[400px] border rounded-lg bg-card">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const pieData = routingStats ? [
    { name: 'PostgreSQL', value: routingStats.postgresQueries, color: COLORS.postgres },
    { name: 'Concepts', value: routingStats.conceptQueries, color: COLORS.concepts },
    { name: 'Hybrid', value: routingStats.hybridQueries, color: COLORS.hybrid },
  ] : [];

  const barData = routingStats ? [
    { layer: 'PostgreSQL', time: routingStats.avgResponseTime.postgres },
    { layer: 'Concepts', time: routingStats.avgResponseTime.concepts },
    { layer: 'Hybrid', time: routingStats.avgResponseTime.hybrid },
  ] : [];

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 border rounded-lg bg-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Queries</p>
              <p className="text-2xl font-bold">{routingStats?.totalQueries || 0}</p>
            </div>
            <Zap className="h-8 w-8 text-yellow-500" />
          </div>
        </div>

        <div className="p-4 border rounded-lg bg-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Routing Accuracy</p>
              <p className="text-2xl font-bold">
                {((routingStats?.routingAccuracy || 0) * 100).toFixed(1)}%
              </p>
            </div>
            <TrendingUp className="h-8 w-8 text-green-500" />
          </div>
        </div>

        <div className="p-4 border rounded-lg bg-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">System Status</p>
              <p className={cn(
                "text-2xl font-bold capitalize",
                health?.status === 'healthy' ? 'text-green-500' :
                health?.status === 'degraded' ? 'text-yellow-500' : 'text-red-500'
              )}>
                {health?.status || 'Unknown'}
              </p>
            </div>
            {health?.status === 'healthy' ? (
              <Brain className="h-8 w-8 text-green-500" />
            ) : (
              <AlertTriangle className="h-8 w-8 text-yellow-500" />
            )}
          </div>
        </div>

        <div className="p-4 border rounded-lg bg-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Evolution Phase</p>
              <p className="text-2xl font-bold">
                Phase {metrics?.current_phase || 1}
              </p>
              <p className="text-xs text-muted-foreground">
                {metrics?.conceptualization_ratio || 0}% Concepts
              </p>
            </div>
            <Database className="h-8 w-8 text-postgres" />
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="p-6 border rounded-lg bg-card">
          <h3 className="text-lg font-semibold mb-4">Query Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="p-6 border rounded-lg bg-card">
          <h3 className="text-lg font-semibold mb-4">Average Response Time (ms)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="layer" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
              />
              <Bar dataKey="time" fill="#8B5CF6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Health Status */}
      {health && (
        <div className="p-6 border rounded-lg bg-card space-y-4">
          <h3 className="text-lg font-semibold">System Health</h3>
          
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(health.services).map(([service, status]: [string, any]) => (
              <div key={service} className="p-3 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium capitalize">{service}</span>
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    status.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                  )} />
                </div>
                <p className="text-xs text-muted-foreground">
                  Latency: {status.latency}ms
                </p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Avg Query Time</p>
              <p className="font-medium">{health.performance.avgQueryTime}ms</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">P95 Query Time</p>
              <p className="font-medium">{health.performance.p95QueryTime}ms</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Error Rate</p>
              <p className="font-medium">{(health.performance.errorRate * 100).toFixed(2)}%</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Throughput</p>
              <p className="font-medium">{health.performance.throughput} req/s</p>
            </div>
          </div>
        </div>
      )}

      {/* Optimization Recommendations */}
      {optimizations && optimizations.length > 0 && (
        <div className="p-6 border rounded-lg bg-card space-y-4">
          <h3 className="text-lg font-semibold">Optimization Recommendations</h3>
          
          <div className="space-y-3">
            {optimizations.slice(0, 3).map((opt: string, i: number) => (
              <div key={i} className="p-4 border rounded-lg bg-muted/50">
                <p className="text-sm text-muted-foreground">{opt}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}