export interface ConceptDBConfig {
  url?: string;
  apiKey?: string;
  timeout?: number;
  phase?: 1 | 2 | 3 | 4;
  autoEvolve?: boolean;
}

export interface QueryResult<T = any> {
  success: boolean;
  data: T;
  routing: {
    type: 'sql' | 'concept' | 'hybrid';
    confidence: number;
  };
  timing: {
    total_ms: number;
    routing_ms: number;
    execution_ms: number;
  };
  metadata?: Record<string, any>;
}

export interface Concept {
  id: string;
  name: string;
  description?: string;
  vector?: number[];
  metadata?: Record<string, any>;
  relations?: Relation[];
  created_at: string;
  updated_at: string;
  evolution_stage?: number;
}

export interface Relation {
  type: 'is_a' | 'part_of' | 'related_to' | 'opposite_of';
  target_id: string;
  strength: number;
  metadata?: Record<string, any>;
}

export interface DataRecord {
  id: string;
  data: Record<string, any>;
  concepts?: string[];
  created_at: string;
  updated_at: string;
}

export interface ImportOptions {
  source: string;
  type?: 'structured' | 'unstructured';
  extractConcepts?: boolean;
  mapping?: Record<string, string>;
  batchSize?: number;
}

export interface EvolutionMetrics {
  current_phase: number;
  conceptualization_ratio: number;
  total_queries: number;
  concept_queries: number;
  sql_queries: number;
  hybrid_queries: number;
  concept_coverage: number;
  evolution_progress: number;
  recommendation?: string;
}

export interface SearchOptions {
  limit?: number;
  threshold?: number;
  includeRelations?: boolean;
  filters?: Record<string, any>;
}

export type QueryType = 'natural' | 'sql' | 'hybrid' | 'auto';

export interface QueryOptions {
  type?: QueryType;
  explain?: boolean;
  timeout?: number;
  cache?: boolean;
}