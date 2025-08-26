'use client';

import { useQuery } from '@tanstack/react-query';
import { useConceptDB } from '@/lib/conceptdb-context';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Loader2, TrendingUp, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { format } from 'date-fns';

export function EvolutionTimeline() {
  const { client } = useConceptDB();

  const { data: timeline, isLoading } = useQuery({
    queryKey: ['evolution-timeline'],
    queryFn: async () => {
      if (!client) return null;
      return await client.evolution.getTimeline();
    },
    enabled: !!client,
  });

  const { data: readiness } = useQuery({
    queryKey: ['phase-readiness'],
    queryFn: async () => {
      if (!client) return null;
      return await client.evolution.checkEvolutionReadiness();
    },
    enabled: !!client,
  });

  const handleEvolve = async () => {
    if (!client) return;
    
    try {
      // For now, just evolve to the next phase (phase 2)
      const result = await client.evolution.evolve(2);
      console.log('Evolution result:', result);
    } catch (error) {
      console.error('Evolution failed:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[400px] border rounded-lg bg-card">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const chartData = timeline?.map((item: any) => ({
    date: format(new Date(item.date), 'MMM dd'),
    conceptualization: item.conceptualizationRatio,
    queries: item.queryCount,
    confidence: item.avgConfidence * 100,
  })) || [];

  return (
    <div className="space-y-6">
      {readiness && (
        <div className="p-6 border rounded-lg bg-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Phase Evolution Status</h3>
              <p className="text-sm text-muted-foreground">
                Current Phase 1 → Phase 2
              </p>
            </div>
            <Button
              onClick={handleEvolve}
              disabled={!readiness}
              className="flex items-center space-x-2"
            >
              <TrendingUp className="h-4 w-4" />
              <span>Evolve to Phase 2</span>
            </Button>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Readiness</span>
              <span className="font-medium">{readiness ? '100%' : '0%'}</span>
            </div>
            <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-concept to-concept-light transition-all"
                style={{ width: readiness ? '100%' : '0%' }}
              />
            </div>
          </div>

          {false && /* readiness.blockers.length > 0 && */ (
            <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
              <div className="flex items-start space-x-2">
                <AlertCircle className="h-4 w-4 text-destructive mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-medium text-destructive">Blockers</p>
                  <ul className="text-sm space-y-1">
                    {[].map((blocker: any, i: number) => (
                      <li key={i}>• {blocker}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {false && /* readiness.recommendations.length > 0 && */ (
            <div className="p-4 rounded-lg bg-muted/50">
              <p className="text-sm font-medium mb-2">Recommendations</p>
              <ul className="text-sm space-y-1 text-muted-foreground">
                {[].map((rec: any, i: number) => (
                  <li key={i}>• {rec}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="text-sm text-muted-foreground">
            Estimated time to next phase: Coming soon
          </div>
        </div>
      )}

      <div className="p-6 border rounded-lg bg-card space-y-4">
        <h3 className="text-lg font-semibold">Evolution Timeline</h3>
        
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="date"
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="conceptualization"
              stroke="#8B5CF6"
              strokeWidth={2}
              name="Conceptualization %"
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="confidence"
              stroke="#10B981"
              strokeWidth={2}
              name="Avg Confidence %"
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="queries"
              stroke="#F59E0B"
              strokeWidth={2}
              name="Query Count"
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
              yAxisId="right"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}