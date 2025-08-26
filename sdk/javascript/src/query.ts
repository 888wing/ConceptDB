/**
 * Query builder module for ConceptDB SDK
 */

import { AxiosInstance } from 'axios';
import { QueryOptions, QueryResult } from './types';
import { ConceptDBError } from './errors';

export class QueryBuilder {
  private client: AxiosInstance;
  private queryStr: string = '';
  private options: QueryOptions = {};
  
  constructor(client: AxiosInstance) {
    this.client = client;
  }
  
  /**
   * Start a new query
   */
  query(query: string): QueryBuilder {
    this.queryStr = query;
    this.options = {};
    return this;
  }
  
  /**
   * Set the preferred layer for query routing
   */
  preferLayer(layer: 'auto' | 'postgres' | 'concepts'): QueryBuilder {
    this.options.preferLayer = layer;
    return this;
  }
  
  /**
   * Set result limit
   */
  limit(count: number): QueryBuilder {
    this.options.limit = count;
    return this;
  }
  
  /**
   * Set result offset for pagination
   */
  offset(count: number): QueryBuilder {
    this.options.offset = count;
    return this;
  }
  
  /**
   * Include metadata in results
   */
  includeMetadata(include = true): QueryBuilder {
    this.options.includeMetadata = include;
    return this;
  }
  
  /**
   * Execute the query
   */
  async execute(): Promise<QueryResult> {
    if (!this.queryStr) {
      throw new ConceptDBError('Query string is required');
    }
    
    try {
      const response = await this.client.post('/api/v1/query', {
        query: this.queryStr,
        prefer_layer: this.options.preferLayer,
        limit: this.options.limit,
        offset: this.options.offset,
        include_metadata: this.options.includeMetadata
      });
      
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }
  
  /**
   * Execute a SQL query directly on PostgreSQL layer
   */
  async sql(query: string, params?: any[]): Promise<QueryResult> {
    try {
      const response = await this.client.post('/api/v1/query/sql', {
        query,
        params,
        prefer_layer: 'postgres'
      });
      
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }
  
  /**
   * Execute a natural language query on concept layer
   */
  async natural(query: string, options: QueryOptions = {}): Promise<QueryResult> {
    try {
      const response = await this.client.post('/api/v1/query/natural', {
        query,
        prefer_layer: 'concepts',
        ...options
      });
      
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }
  
  /**
   * Execute a hybrid query across both layers
   */
  async hybrid(query: string, options: QueryOptions = {}): Promise<QueryResult> {
    try {
      const response = await this.client.post('/api/v1/query/hybrid', {
        query,
        prefer_layer: 'auto',
        ...options
      });
      
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }
  
  /**
   * Get explanation for how a query would be routed
   */
  async explain(query?: string): Promise<{
    query: string;
    routing: 'postgres' | 'concepts' | 'both';
    confidence: number;
    reasoning: string;
    optimizations: string[];
  }> {
    const q = query || this.queryStr;
    if (!q) {
      throw new ConceptDBError('Query string is required for explanation');
    }
    
    try {
      const response = await this.client.get('/api/v1/query/explain', {
        params: { query: q }
      });
      
      return response.data.explanation;
    } catch (error) {
      throw this.handleError(error);
    }
  }
  
  /**
   * Stream results for large queries
   */
  async *stream(): AsyncGenerator<any, void, unknown> {
    if (!this.queryStr) {
      throw new ConceptDBError('Query string is required');
    }
    
    try {
      const response = await this.client.post('/api/v1/query/stream', {
        query: this.queryStr,
        ...this.options
      }, {
        responseType: 'stream'
      });
      
      // Process stream
      const stream = response.data;
      let buffer = '';
      
      for await (const chunk of stream) {
        buffer += chunk.toString();
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.trim()) {
            try {
              const data = JSON.parse(line);
              yield data;
            } catch (e) {
              // Skip malformed lines
            }
          }
        }
      }
      
      // Process remaining buffer
      if (buffer.trim()) {
        try {
          const data = JSON.parse(buffer);
          yield data;
        } catch (e) {
          // Skip malformed data
        }
      }
    } catch (error) {
      throw this.handleError(error);
    }
  }
  
  /**
   * Build and validate query without executing
   */
  build(): { query: string; options: QueryOptions } {
    if (!this.queryStr) {
      throw new ConceptDBError('Query string is required');
    }
    
    return {
      query: this.queryStr,
      options: this.options
    };
  }
  
  /**
   * Clear the query builder
   */
  clear(): QueryBuilder {
    this.queryStr = '';
    this.options = {};
    return this;
  }
  
  /**
   * Chain multiple queries
   */
  static chain(...queries: Array<{ query: string; options?: QueryOptions }>): QueryChain {
    return new QueryChain(queries);
  }
  
  /**
   * Handle errors
   */
  private handleError(error: any): Error {
    if (error.response) {
      const message = error.response.data?.detail || error.response.data?.error || error.message;
      return new ConceptDBError(message, error.response.status);
    }
    return error;
  }
}

/**
 * Query chain for executing multiple queries in sequence
 */
export class QueryChain {
  private queries: Array<{ query: string; options?: QueryOptions }>;
  private results: QueryResult[] = [];
  
  constructor(queries: Array<{ query: string; options?: QueryOptions }>) {
    this.queries = queries;
  }
  
  /**
   * Add a query to the chain
   */
  add(query: string, options?: QueryOptions): QueryChain {
    this.queries.push({ query, options });
    return this;
  }
  
  /**
   * Execute all queries in sequence
   */
  async execute(client: AxiosInstance): Promise<QueryResult[]> {
    this.results = [];
    
    for (const { query, options } of this.queries) {
      try {
        const response = await client.post('/api/v1/query', {
          query,
          ...options
        });
        this.results.push(response.data);
      } catch (error: any) {
        throw new ConceptDBError(
          `Query chain failed at: ${query}. Error: ${error.message}`
        );
      }
    }
    
    return this.results;
  }
  
  /**
   * Execute queries in parallel
   */
  async executeParallel(client: AxiosInstance): Promise<QueryResult[]> {
    const promises = this.queries.map(({ query, options }) =>
      client.post('/api/v1/query', {
        query,
        ...options
      })
    );
    
    try {
      const responses = await Promise.all(promises);
      this.results = responses.map(r => r.data);
      return this.results;
    } catch (error: any) {
      throw new ConceptDBError(`Parallel query execution failed: ${error.message}`);
    }
  }
  
  /**
   * Get results from last execution
   */
  getResults(): QueryResult[] {
    return this.results;
  }
}