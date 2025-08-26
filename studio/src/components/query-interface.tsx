'use client';

import { useState } from 'react';
import { Search, Loader2, Database, Brain, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useConceptDB } from '@/lib/conceptdb-context';
import { useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

export function QueryInterface() {
  const [query, setQuery] = useState('');
  const [preferLayer, setPreferLayer] = useState<'auto' | 'postgres' | 'concepts'>('auto');
  const { client } = useConceptDB();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['query', query, preferLayer],
    queryFn: async () => {
      if (!client || !query) return null;
      return await client.execute(query, { 
        type: preferLayer === 'postgres' ? 'sql' : preferLayer === 'concepts' ? 'natural' : 'auto' 
      });
    },
    enabled: false,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      toast.error('Please enter a query');
      return;
    }
    refetch();
  };

  const getLayerIcon = (layer: string) => {
    switch (layer) {
      case 'postgres':
        return <Database className="h-4 w-4 text-postgres" />;
      case 'concepts':
        return <Brain className="h-4 w-4 text-concept" />;
      default:
        return <Zap className="h-4 w-4 text-yellow-500" />;
    }
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter SQL or natural language query..."
            className="w-full min-h-[120px] p-4 pr-12 rounded-lg border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <Button
            type="submit"
            size="icon"
            disabled={isLoading || !client}
            className="absolute bottom-4 right-4"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
          </Button>
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="text-sm text-muted-foreground">Prefer Layer:</span>
          <div className="flex space-x-2">
            {(['auto', 'postgres', 'concepts'] as const).map((layer) => (
              <Button
                key={layer}
                type="button"
                variant={preferLayer === layer ? 'default' : 'outline'}
                size="sm"
                onClick={() => setPreferLayer(layer)}
                className="capitalize"
              >
                {layer}
              </Button>
            ))}
          </div>
        </div>
      </form>

      {error && (
        <div className="p-4 rounded-lg border border-destructive bg-destructive/10">
          <p className="text-sm text-destructive">
            {(error as Error).message}
          </p>
        </div>
      )}

      {data && (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                {getLayerIcon(data.routing?.type || 'hybrid')}
                <span className="text-sm font-medium capitalize">
                  {data.routing?.type || 'hybrid'}
                </span>
              </div>
              <div className="text-sm text-muted-foreground">
                {data.data?.length || 0} results • {data.timing?.total_ms || 0}ms
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-muted-foreground">Confidence:</span>
              <div className="flex items-center space-x-1">
                <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full transition-all',
                      (data.routing?.confidence || 0) > 0.8
                        ? 'bg-green-500'
                        : (data.routing?.confidence || 0) > 0.5
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    )}
                    style={{ width: `${(data.routing?.confidence || 0) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium">
                  {((data.routing?.confidence || 0) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>

          {data.routing?.confidence && (
            <div className="p-4 rounded-lg border bg-muted/50">
              <p className="text-sm text-muted-foreground">
                Query routed via {data.routing.type} layer with {Math.round(data.routing.confidence * 100)}% confidence
              </p>
            </div>
          )}

          <div className="rounded-lg border bg-card overflow-hidden">
            <div className="p-4 border-b bg-muted/50">
              <h3 className="text-sm font-medium">Query Results</h3>
            </div>
            <div className="p-4 max-h-[400px] overflow-auto">
              <pre className="text-sm">
                {JSON.stringify(data.data, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}