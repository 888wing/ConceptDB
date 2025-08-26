/**
 * Unit tests for CLI query command
 */

import { queryCommand } from '../commands/query';
import axios from 'axios';
import { jest } from '@jest/globals';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('Query Command', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock console methods
    console.log = jest.fn();
    console.error = jest.fn();
  });

  test('should execute SQL query successfully', async () => {
    const mockResponse = {
      data: {
        success: true,
        data: {
          route: 'postgres',
          query_type: 'sql',
          results: [
            { id: 1, name: 'Customer 1' },
            { id: 2, name: 'Customer 2' }
          ],
          confidence: 0.95
        }
      }
    };

    mockedAxios.post.mockResolvedValue(mockResponse);

    await queryCommand.parseAsync(['node', 'query', 'SELECT * FROM customers']);

    expect(mockedAxios.post).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/query',
      { query: 'SELECT * FROM customers', limit: 10 }
    );
    expect(console.log).toHaveBeenCalledWith(expect.stringContaining('Route: postgres'));
    expect(console.log).toHaveBeenCalledWith(expect.stringContaining('2 results'));
  });

  test('should execute natural language query successfully', async () => {
    const mockResponse = {
      data: {
        success: true,
        data: {
          route: 'concepts',
          query_type: 'natural_language',
          results: [
            { id: 'c1', type: 'concept', score: 0.9, data: { name: 'Similar Product' } }
          ],
          confidence: 0.85
        }
      }
    };

    mockedAxios.post.mockResolvedValue(mockResponse);

    await queryCommand.parseAsync(['node', 'query', 'find similar products']);

    expect(mockedAxios.post).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/query',
      { query: 'find similar products', limit: 10 }
    );
    expect(console.log).toHaveBeenCalledWith(expect.stringContaining('Route: concepts'));
  });

  test('should handle query with custom limit', async () => {
    const mockResponse = {
      data: {
        success: true,
        data: {
          route: 'postgres',
          query_type: 'sql',
          results: []
        }
      }
    };

    mockedAxios.post.mockResolvedValue(mockResponse);

    await queryCommand.parseAsync(['node', 'query', 'SELECT * FROM products', '--limit', '5']);

    expect(mockedAxios.post).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/query',
      { query: 'SELECT * FROM products', limit: 5 }
    );
  });

  test('should handle API errors gracefully', async () => {
    mockedAxios.post.mockRejectedValue(new Error('Connection refused'));

    await queryCommand.parseAsync(['node', 'query', 'SELECT * FROM users']);

    expect(console.error).toHaveBeenCalledWith(expect.stringContaining('Query failed'));
    expect(console.error).toHaveBeenCalledWith(expect.stringContaining('Connection refused'));
  });

  test('should display results in table format', async () => {
    const mockResponse = {
      data: {
        success: true,
        data: {
          route: 'postgres',
          results: [
            { id: 1, name: 'Product A', price: 99.99 },
            { id: 2, name: 'Product B', price: 149.99 }
          ]
        }
      }
    };

    mockedAxios.post.mockResolvedValue(mockResponse);

    await queryCommand.parseAsync(['node', 'query', 'SELECT * FROM products', '--format', 'table']);

    expect(console.log).toHaveBeenCalledWith(expect.stringContaining('Product A'));
    expect(console.log).toHaveBeenCalledWith(expect.stringContaining('99.99'));
  });
});