'use client';

import { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import { Button } from '@/components/ui/button';
import { useConceptDB } from '@/lib/conceptdb-context';
import { useQuery } from '@tanstack/react-query';
import { Loader2, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

// Register the fcose layout
cytoscape.use(fcose);

export function ConceptGraph() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const { client } = useConceptDB();

  const { data: graphData, isLoading } = useQuery({
    queryKey: ['concept-graph'],
    queryFn: async () => {
      if (!client) return null;
      return await client.concepts.getGraph(undefined, 3);
    },
    enabled: !!client,
  });

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Initialize Cytoscape
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...graphData.nodes.map((node: any) => ({
          data: {
            id: node.id,
            label: node.label,
            ...node.metadata,
          },
        })),
        ...graphData.edges.map((edge: any) => ({
          data: {
            id: `${edge.from}-${edge.to}`,
            source: edge.from,
            target: edge.to,
            type: edge.type,
          },
        })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#8B5CF6',
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '12px',
            'color': '#fff',
            'text-outline-width': 2,
            'text-outline-color': '#8B5CF6',
            'width': 40,
            'height': 40,
          },
        },
        {
          selector: 'node:selected',
          style: {
            'background-color': '#7C3AED',
            'border-color': '#5B21B6',
            'border-width': 3,
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#CBD5E1',
            'target-arrow-color': '#CBD5E1',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(type)',
            'font-size': '10px',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
          },
        },
        {
          selector: 'edge[type="is_a"]',
          style: {
            'line-color': '#10B981',
            'target-arrow-color': '#10B981',
          },
        },
        {
          selector: 'edge[type="part_of"]',
          style: {
            'line-color': '#3B82F6',
            'target-arrow-color': '#3B82F6',
          },
        },
        {
          selector: 'edge[type="related_to"]',
          style: {
            'line-color': '#F59E0B',
            'target-arrow-color': '#F59E0B',
            'line-style': 'dashed',
          },
        },
        {
          selector: 'edge[type="opposite_of"]',
          style: {
            'line-color': '#EF4444',
            'target-arrow-color': '#EF4444',
            'line-style': 'dotted',
          },
        },
      ],
      layout: {
        name: 'fcose',
        randomize: true,
        animate: true,
        animationDuration: 1000,
        nodeDimensionsIncludeLabels: true,
        nodeRepulsion: 4500,
        idealEdgeLength: 100,
        edgeElasticity: 0.45,
        nestingFactor: 0.1,
      } as any,
    });

    cyRef.current = cy;

    // Add event listeners
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      setSelectedNode(node.data());
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
      }
    });

    return () => {
      cy.destroy();
    };
  }, [graphData]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.2);
      cyRef.current.center();
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
      cyRef.current.center();
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit();
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[600px] border rounded-lg bg-card">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Concept Relationship Graph</h2>
        <div className="flex space-x-2">
          <Button size="icon" variant="outline" onClick={handleZoomIn}>
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="outline" onClick={handleZoomOut}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="outline" onClick={handleFit}>
            <Maximize2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex space-x-4">
        <div className="flex-1">
          <div
            ref={containerRef}
            className="w-full h-[600px] border rounded-lg bg-card cytoscape-container"
          />
        </div>

        {selectedNode && (
          <div className="w-80 p-4 border rounded-lg bg-card space-y-4">
            <h3 className="font-semibold">Concept Details</h3>
            <div className="space-y-2">
              <div>
                <p className="text-sm text-muted-foreground">Name</p>
                <p className="font-medium">{selectedNode.label}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">ID</p>
                <p className="text-xs font-mono">{selectedNode.id}</p>
              </div>
              {selectedNode.description && (
                <div>
                  <p className="text-sm text-muted-foreground">Description</p>
                  <p className="text-sm">{selectedNode.description}</p>
                </div>
              )}
              {selectedNode.usageCount && (
                <div>
                  <p className="text-sm text-muted-foreground">Usage Count</p>
                  <p className="font-medium">{selectedNode.usageCount}</p>
                </div>
              )}
              {selectedNode.strength && (
                <div>
                  <p className="text-sm text-muted-foreground">Strength</p>
                  <div className="flex items-center space-x-2">
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-concept"
                        style={{ width: `${selectedNode.strength * 100}%` }}
                      />
                    </div>
                    <span className="text-sm">
                      {(selectedNode.strength * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="flex space-x-8 p-4 border rounded-lg bg-muted/50">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-0 border-t-2 border-green-500" />
          <span className="text-sm">is_a</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-0 border-t-2 border-blue-500" />
          <span className="text-sm">part_of</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-0 border-t-2 border-dashed border-yellow-500" />
          <span className="text-sm">related_to</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-0 border-t-2 border-dotted border-red-500" />
          <span className="text-sm">opposite_of</span>
        </div>
      </div>
    </div>
  );
}