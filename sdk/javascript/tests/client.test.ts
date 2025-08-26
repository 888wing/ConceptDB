/**
 * Tests for ConceptDB client
 */

import { ConceptDB } from '../src/client';
import { ConceptDBError, NetworkError, ValidationError } from '../src/errors';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('ConceptDB Client', () => {
  let client: ConceptDB;
  
  beforeEach(() => {
    mockedAxios.create.mockReturnValue({
      post: jest.fn(),
      get: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() }
      }
    } as any);
    
    client = new ConceptDB({
      url: 'http://localhost:8000',
      apiKey: 'test-key'
    });
  });
  
  afterEach(() => {
    jest.clearAllMocks();
  });
  
  describe('constructor', () => {
    it('should initialize with default config', () => {
      const client = new ConceptDB({ url: 'http://localhost:8000' });
      expect(client).toBeDefined();
      expect(client.concepts).toBeDefined();
      expect(client.query).toBeDefined();
      expect(client.evolution).toBeDefined();
    });
    
    it('should create axios instance with correct config', () => {
      new ConceptDB({
        url: 'http://localhost:8000',
        apiKey: 'test-key',
        timeout: 5000
      });
      
      expect(mockedAxios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8000',
        timeout: 5000,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-key'
        }
      });
    });
  });
  
  describe('execute', () => {
    it('should execute a query successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          query: 'test query',
          routingDecision: 'postgres',
          results: [{ id: 1, name: 'test' }],
          resultCount: 1,
          confidenceScore: 0.9,
          responseTimeMs: 50,
          explanation: 'Routed to PostgreSQL'
        }
      };
      
      (client as any).client.post = jest.fn().mockResolvedValue(mockResponse);
      
      const result = await client.execute('test query', { limit: 10 });
      
      expect(result).toEqual(mockResponse.data);
      expect((client as any).client.post).toHaveBeenCalledWith('/api/v1/query', {
        query: 'test query',
        prefer_layer: undefined,
        limit: 10
      });
    });
    
    it('should handle query errors', async () => {
      (client as any).client.post = jest.fn().mockRejectedValue({
        response: {
          status: 400,
          data: { detail: 'Invalid query syntax' }
        }
      });
      
      await expect(client.execute('invalid')).rejects.toThrow(ValidationError);
    });
  });
  
  describe('createData', () => {
    it('should create data record', async () => {
      const mockResponse = {
        data: {
          id: 'record-123',
          success: true
        }
      };
      
      (client as any).client.post = jest.fn().mockResolvedValue(mockResponse);
      
      const result = await client.createData({
        type: 'customer',
        content: { name: 'John' }
      }, true);
      
      expect(result).toEqual({ id: 'record-123', success: true });
      expect((client as any).client.post).toHaveBeenCalledWith('/api/v1/data', {
        type: 'customer',
        content: { name: 'John' },
        extract_concepts: true
      });
    });
  });
  
  describe('getData', () => {
    it('should get data record by ID', async () => {
      const mockRecord = {
        id: 'record-123',
        type: 'customer',
        content: { name: 'John' }
      };
      
      (client as any).client.get = jest.fn().mockResolvedValue({
        data: { success: true, data: mockRecord }
      });
      
      const result = await client.getData('record-123');
      
      expect(result).toEqual(mockRecord);
      expect((client as any).client.get).toHaveBeenCalledWith('/api/v1/data/record-123');
    });
    
    it('should return null for non-existent record', async () => {
      (client as any).client.get = jest.fn().mockRejectedValue({
        response: { status: 404 }
      });
      
      const result = await client.getData('non-existent');
      
      expect(result).toBeNull();
    });
  });
  
  describe('updateData', () => {
    it('should update data record', async () => {
      (client as any).client.put = jest.fn().mockResolvedValue({
        data: { success: true }
      });
      
      const result = await client.updateData('record-123', {
        content: { name: 'Jane' }
      });
      
      expect(result).toBe(true);
      expect((client as any).client.put).toHaveBeenCalledWith(
        '/api/v1/data/record-123',
        { content: { name: 'Jane' } }
      );
    });
  });
  
  describe('extractConcepts', () => {
    it('should extract concepts from records', async () => {
      const mockResponse = {
        data: {
          processed_records: 10,
          concepts_extracted: 25,
          failed: 0
        }
      };
      
      (client as any).client.post = jest.fn().mockResolvedValue(mockResponse);
      
      const result = await client.extractConcepts(['id1', 'id2'], 50);
      
      expect(result).toEqual({
        processed: 10,
        extracted: 25,
        failed: 0
      });
      expect((client as any).client.post).toHaveBeenCalledWith('/api/v1/concepts/extract', {
        record_ids: ['id1', 'id2'],
        limit: 50
      });
    });
  });
  
  describe('getMetrics', () => {
    it('should get evolution metrics', async () => {
      const mockMetrics = {
        phase: 1,
        conceptualizationRatio: 10,
        totalQueries: 1000,
        conceptQueries: 100,
        postgresQueries: 900,
        hybridQueries: 0,
        avgConceptConfidence: 0.75,
        recommendation: 'Continue with Phase 1'
      };
      
      (client as any).client.get = jest.fn().mockResolvedValue({
        data: mockMetrics
      });
      
      const result = await client.getMetrics();
      
      expect(result).toEqual(mockMetrics);
      expect((client as any).client.get).toHaveBeenCalledWith('/api/v1/metrics/evolution');
    });
  });
  
  describe('health', () => {
    it('should check API health', async () => {
      (client as any).client.get = jest.fn().mockResolvedValue({
        data: {
          status: 'healthy',
          version: '1.0.0'
        }
      });
      
      const result = await client.health();
      
      expect(result).toEqual({
        status: 'healthy',
        version: '1.0.0',
        phase: 1
      });
      expect((client as any).client.get).toHaveBeenCalledWith('/health');
    });
  });
  
  describe('explainQuery', () => {
    it('should explain query routing', async () => {
      const mockExplanation = {
        query: 'test query',
        routing: 'concepts',
        confidence: 0.85,
        reasoning: 'Natural language detected'
      };
      
      (client as any).client.get = jest.fn().mockResolvedValue({
        data: { explanation: mockExplanation }
      });
      
      const result = await client.explainQuery('test query');
      
      expect(result).toEqual(mockExplanation);
      expect((client as any).client.get).toHaveBeenCalledWith('/api/v1/query/explain', {
        params: { query: 'test query' }
      });
    });
  });
  
  describe('error handling', () => {
    it('should handle network errors', async () => {
      (client as any).client.post = jest.fn().mockRejectedValue({
        request: {},
        message: 'Network Error'
      });
      
      await expect(client.execute('test')).rejects.toThrow(NetworkError);
    });
    
    it('should handle validation errors', async () => {
      (client as any).client.post = jest.fn().mockRejectedValue({
        response: {
          status: 400,
          data: { detail: 'Validation failed' }
        }
      });
      
      await expect(client.execute('test')).rejects.toThrow(ValidationError);
    });
    
    it('should handle generic errors', async () => {
      (client as any).client.post = jest.fn().mockRejectedValue({
        response: {
          status: 500,
          data: { error: 'Internal server error' }
        }
      });
      
      await expect(client.execute('test')).rejects.toThrow(ConceptDBError);
    });
  });
});