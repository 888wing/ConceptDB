'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { QueryInterface } from '@/components/query-interface';
import { ConceptGraph } from '@/components/concept-graph';
import { EvolutionTimeline } from '@/components/evolution-timeline';
import { MetricsDashboard } from '@/components/metrics-dashboard';
import { Header } from '@/components/header';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState('query');

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="query">Query Explorer</TabsTrigger>
            <TabsTrigger value="graph">Concept Graph</TabsTrigger>
            <TabsTrigger value="evolution">Evolution Timeline</TabsTrigger>
            <TabsTrigger value="metrics">Metrics Dashboard</TabsTrigger>
          </TabsList>
          
          <TabsContent value="query" className="space-y-4">
            <QueryInterface />
          </TabsContent>
          
          <TabsContent value="graph" className="space-y-4">
            <ConceptGraph />
          </TabsContent>
          
          <TabsContent value="evolution" className="space-y-4">
            <EvolutionTimeline />
          </TabsContent>
          
          <TabsContent value="metrics" className="space-y-4">
            <MetricsDashboard />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}