import axios, { AxiosInstance } from 'axios';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

export interface QueryResult {
  success: boolean;
  data: any;
  routing: {
    type: 'sql' | 'concept' | 'hybrid';
    confidence: number;
  };
  timing: {
    total_ms: number;
    routing_ms: number;
    execution_ms: number;
  };
}

export interface QueryExplanation {
  analysis: {
    type: string;
    routing: string;
    confidence: number;
  };
  reasoning: string[];
  suggestions?: string[];
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  postgres?: boolean;
  postgres_details?: string;
  qdrant?: boolean;
  qdrant_details?: string;
  sqlite?: boolean;
  sqlite_details?: string;
  message?: string;
}

export interface EvolutionMetrics {
  current_phase: number;
  conceptualization_ratio: number;
  total_queries?: number;
  concept_queries?: number;
  sql_queries?: number;
  concept_coverage?: number;
  evolution_progress?: number;
}

export class ConceptDBClient {
  private api: AxiosInstance;
  private host: string;
  private port: string;
  
  constructor(config?: { host?: string; port?: string }) {
    this.host = config?.host || process.env.CONCEPTDB_HOST || 'localhost';
    this.port = config?.port || process.env.CONCEPTDB_PORT || '8000';
    
    this.api = axios.create({
      baseURL: `http://${this.host}:${this.port}/api/v1`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
  
  // Query operations
  async query(query: string): Promise<QueryResult> {
    const response = await this.api.post('/query', { query });
    return response.data;
  }
  
  async explainQuery(query: string): Promise<QueryExplanation> {
    const response = await this.api.post('/query/explain', { query });
    return response.data;
  }
  
  // Health and status
  async getHealth(): Promise<HealthStatus> {
    try {
      const response = await this.api.get('/health');
      return response.data;
    } catch (error) {
      return {
        status: 'unhealthy',
        message: 'Cannot connect to ConceptDB API'
      };
    }
  }
  
  async getEvolutionMetrics(): Promise<EvolutionMetrics> {
    const response = await this.api.get('/metrics/evolution');
    return response.data;
  }
  
  async getRoutingStats(): Promise<any> {
    const response = await this.api.get('/metrics/routing');
    return response.data;
  }
  
  // Concept operations
  async createConcept(concept: {
    name: string;
    description?: string;
    metadata?: any;
  }): Promise<any> {
    const response = await this.api.post('/concepts', concept);
    return response.data;
  }
  
  async extractConcepts(data: {
    text?: string;
    records?: any[];
    mapping?: any;
    auto_detect?: boolean;
    source?: string;
  }): Promise<any> {
    const response = await this.api.post('/concepts/extract', data);
    return response.data;
  }
  
  async searchConcepts(query: string, limit: number = 10): Promise<any> {
    const response = await this.api.post('/concepts/search', {
      query,
      limit
    });
    return response.data;
  }
  
  async getRecentConcepts(limit: number = 10): Promise<any> {
    const response = await this.api.get(`/concepts/recent?limit=${limit}`);
    return response.data;
  }
  
  async getConceptGraph(conceptId?: string): Promise<any> {
    const url = conceptId ? `/concepts/${conceptId}/graph` : '/concepts/graph';
    const response = await this.api.get(url);
    return response.data;
  }
  
  // Data import operations
  async importData(data: {
    records?: any[];
    content?: string;
    source: string;
    type: 'structured' | 'unstructured';
  }): Promise<any> {
    const response = await this.api.post('/data/import', data);
    return response.data;
  }
  
  // Evolution operations
  async triggerEvolution(options?: {
    target_phase?: number;
    force?: boolean;
  }): Promise<any> {
    const response = await this.api.post('/evolve', options || {});
    return response.data;
  }
  
  // Utility methods
  async ping(): Promise<boolean> {
    try {
      const health = await this.getHealth();
      return health.status === 'healthy' || health.status === 'degraded';
    } catch {
      return false;
    }
  }
  
  setAuth(token: string): void {
    this.api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
}