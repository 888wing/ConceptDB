import { AxiosInstance } from 'axios';
import { Concept, Relation, SearchOptions } from './types';

export class ConceptManager {
  constructor(private api: AxiosInstance) {}
  
  /**
   * Create a new concept
   */
  async create(concept: Partial<Concept>): Promise<Concept> {
    const response = await this.api.post('/concepts', concept);
    return response.data;
  }
  
  /**
   * Get a concept by ID
   */
  async get(id: string): Promise<Concept> {
    const response = await this.api.get(`/concepts/${id}`);
    return response.data;
  }
  
  /**
   * Update a concept
   */
  async update(id: string, updates: Partial<Concept>): Promise<Concept> {
    const response = await this.api.put(`/concepts/${id}`, updates);
    return response.data;
  }
  
  /**
   * Delete a concept
   */
  async delete(id: string): Promise<boolean> {
    const response = await this.api.delete(`/concepts/${id}`);
    return response.data.success;
  }
  
  /**
   * Search for similar concepts
   */
  async search(query: string, options: SearchOptions = {}): Promise<Concept[]> {
    const response = await this.api.post('/concepts/search', {
      query,
      ...options
    });
    return response.data.concepts;
  }
  
  /**
   * Extract concepts from text
   */
  async extract(text: string, options: any = {}): Promise<Concept[]> {
    const response = await this.api.post('/concepts/extract', {
      text,
      ...options
    });
    return response.data.concepts;
  }
  
  /**
   * Get concept relationships
   */
  async getRelations(id: string): Promise<Relation[]> {
    const response = await this.api.get(`/concepts/${id}/relations`);
    return response.data.relations;
  }
  
  /**
   * Add a relationship between concepts
   */
  async addRelation(
    sourceId: string, 
    targetId: string, 
    type: Relation['type'], 
    strength: number = 1.0
  ): Promise<Relation> {
    const response = await this.api.post(`/concepts/${sourceId}/relations`, {
      target_id: targetId,
      type,
      strength
    });
    return response.data;
  }
  
  /**
   * Remove a relationship
   */
  async removeRelation(sourceId: string, targetId: string): Promise<boolean> {
    const response = await this.api.delete(`/concepts/${sourceId}/relations/${targetId}`);
    return response.data.success;
  }
  
  /**
   * Get concept graph visualization data
   */
  async getGraph(rootId?: string, depth: number = 2): Promise<any> {
    const url = rootId ? `/concepts/${rootId}/graph` : '/concepts/graph';
    const response = await this.api.get(url, { params: { depth } });
    return response.data;
  }
  
  /**
   * Merge two concepts
   */
  async merge(sourceId: string, targetId: string): Promise<Concept> {
    const response = await this.api.post(`/concepts/${targetId}/merge`, {
      source_id: sourceId
    });
    return response.data;
  }
  
  /**
   * Get concept evolution history
   */
  async getEvolution(id: string): Promise<any> {
    const response = await this.api.get(`/concepts/${id}/evolution`);
    return response.data;
  }
  
  /**
   * Batch create concepts
   */
  async createBatch(concepts: Partial<Concept>[]): Promise<Concept[]> {
    const response = await this.api.post('/concepts/batch', { concepts });
    return response.data.concepts;
  }
  
  /**
   * Get trending concepts
   */
  async getTrending(limit: number = 10): Promise<Concept[]> {
    const response = await this.api.get('/concepts/trending', { params: { limit } });
    return response.data.concepts;
  }
}