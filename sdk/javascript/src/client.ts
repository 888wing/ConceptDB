import axios, { AxiosInstance } from 'axios';
import { 
  ConceptDBConfig, 
  QueryResult, 
  QueryOptions, 
  DataRecord,
  ImportOptions,
  EvolutionMetrics 
} from './types';
import { QueryBuilder } from './query-builder';
import { ConceptManager } from './concepts';
import { EvolutionTracker } from './evolution';

export class ConceptDB {
  private api: AxiosInstance;
  private config: ConceptDBConfig;
  
  public query: QueryBuilder;
  public concepts: ConceptManager;
  public evolution: EvolutionTracker;
  
  constructor(config: ConceptDBConfig = {}) {
    this.config = {
      url: config.url || process.env.CONCEPTDB_URL || 'http://localhost:8000',
      apiKey: config.apiKey || process.env.CONCEPTDB_API_KEY,
      timeout: config.timeout || 30000,
      phase: config.phase || 1,
      autoEvolve: config.autoEvolve || false
    };
    
    this.api = axios.create({
      baseURL: `${this.config.url}/api/v1`,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` })
      }
    });
    
    // Initialize modules
    this.query = new QueryBuilder(this.api);
    this.concepts = new ConceptManager(this.api);
    this.evolution = new EvolutionTracker(this.api, this.config);
  }
  
  /**
   * Execute a query (natural language or SQL)
   * @param query The query string
   * @param options Query options
   * @returns Query result with routing information
   */
  async execute<T = any>(query: string, options?: QueryOptions): Promise<QueryResult<T>> {
    const response = await this.api.post('/query', {
      query,
      ...options
    });
    
    const result = response.data as QueryResult<T>;
    
    // Track evolution if auto-evolve is enabled
    if (this.config.autoEvolve) {
      await this.evolution.trackQuery(result.routing.type);
    }
    
    return result;
  }
  
  /**
   * Insert data records
   * @param records Array of records to insert
   * @returns Inserted records with IDs
   */
  async insert(records: Partial<DataRecord>[]): Promise<DataRecord[]> {
    const response = await this.api.post('/data', { records });
    return response.data.records;
  }
  
  /**
   * Update a data record
   * @param id Record ID
   * @param data Data to update
   * @returns Updated record
   */
  async update(id: string, data: Partial<DataRecord>): Promise<DataRecord> {
    const response = await this.api.put(`/data/${id}`, data);
    return response.data;
  }
  
  /**
   * Delete a data record
   * @param id Record ID
   * @returns Success status
   */
  async delete(id: string): Promise<boolean> {
    const response = await this.api.delete(`/data/${id}`);
    return response.data.success;
  }
  
  /**
   * Import data from various sources
   * @param options Import options
   * @returns Import result
   */
  async importData(options: ImportOptions): Promise<any> {
    const response = await this.api.post('/data/import', options);
    return response.data;
  }
  
  /**
   * Get current evolution metrics
   * @returns Evolution metrics
   */
  async getMetrics(): Promise<EvolutionMetrics> {
    const response = await this.api.get('/metrics/evolution');
    return response.data;
  }
  
  /**
   * Check database health
   * @returns Health status
   */
  async health(): Promise<any> {
    const response = await this.api.get('/health');
    return response.data;
  }
  
  /**
   * Create a transaction for batch operations
   * @returns Transaction object
   */
  async transaction(): Promise<Transaction> {
    return new Transaction(this.api);
  }
  
  /**
   * Set API key for authentication
   * @param apiKey API key
   */
  setApiKey(apiKey: string): void {
    this.config.apiKey = apiKey;
    this.api.defaults.headers.common['Authorization'] = `Bearer ${apiKey}`;
  }
  
  /**
   * Get current configuration
   * @returns Current configuration
   */
  getConfig(): ConceptDBConfig {
    return { ...this.config };
  }
}

/**
 * Transaction class for batch operations
 */
class Transaction {
  private operations: any[] = [];
  
  constructor(private api: AxiosInstance) {}
  
  insert(records: Partial<DataRecord>[]): Transaction {
    this.operations.push({ type: 'insert', data: records });
    return this;
  }
  
  update(id: string, data: Partial<DataRecord>): Transaction {
    this.operations.push({ type: 'update', id, data });
    return this;
  }
  
  delete(id: string): Transaction {
    this.operations.push({ type: 'delete', id });
    return this;
  }
  
  async commit(): Promise<any> {
    const response = await this.api.post('/transaction', {
      operations: this.operations
    });
    return response.data;
  }
  
  rollback(): void {
    this.operations = [];
  }
}