import { AxiosInstance } from 'axios';
import { QueryResult, QueryOptions } from './types';

export class QueryBuilder {
  private conditions: string[] = [];
  private selectFields: string[] = [];
  private fromTable: string = '';
  private joins: string[] = [];
  private orderByFields: string[] = [];
  private limitValue?: number;
  private offsetValue?: number;
  private queryType: 'sql' | 'natural' = 'sql';
  
  constructor(private api: AxiosInstance) {}
  
  /**
   * Select fields for the query
   */
  select(...fields: string[]): QueryBuilder {
    this.selectFields = fields;
    return this;
  }
  
  /**
   * Specify the table to query from
   */
  from(table: string): QueryBuilder {
    this.fromTable = table;
    return this;
  }
  
  /**
   * Add a WHERE condition
   */
  where(condition: string, value?: any): QueryBuilder {
    if (value !== undefined) {
      // Handle parameterized queries
      this.conditions.push(`${condition} = '${value}'`);
    } else {
      this.conditions.push(condition);
    }
    return this;
  }
  
  /**
   * Add an AND condition
   */
  and(condition: string, value?: any): QueryBuilder {
    return this.where(condition, value);
  }
  
  /**
   * Add an OR condition
   */
  or(condition: string, value?: any): QueryBuilder {
    if (this.conditions.length > 0) {
      const lastCondition = this.conditions.pop();
      this.conditions.push(`(${lastCondition} OR ${condition}${value !== undefined ? ` = '${value}'` : ''})`);
    } else {
      this.where(condition, value);
    }
    return this;
  }
  
  /**
   * Add a JOIN clause
   */
  join(table: string, condition: string): QueryBuilder {
    this.joins.push(`JOIN ${table} ON ${condition}`);
    return this;
  }
  
  /**
   * Add a LEFT JOIN clause
   */
  leftJoin(table: string, condition: string): QueryBuilder {
    this.joins.push(`LEFT JOIN ${table} ON ${condition}`);
    return this;
  }
  
  /**
   * Order results by field
   */
  orderBy(field: string, direction: 'ASC' | 'DESC' = 'ASC'): QueryBuilder {
    this.orderByFields.push(`${field} ${direction}`);
    return this;
  }
  
  /**
   * Limit the number of results
   */
  limit(value: number): QueryBuilder {
    this.limitValue = value;
    return this;
  }
  
  /**
   * Set the offset for pagination
   */
  offset(value: number): QueryBuilder {
    this.offsetValue = value;
    return this;
  }
  
  /**
   * Search for similar concepts (switches to natural language mode)
   */
  similar(concept: string, threshold: number = 0.7): QueryBuilder {
    this.queryType = 'natural';
    this.conditions.push(`similar to "${concept}" with threshold ${threshold}`);
    return this;
  }
  
  /**
   * Find related concepts (natural language mode)
   */
  related(concept: string): QueryBuilder {
    this.queryType = 'natural';
    this.conditions.push(`related to "${concept}"`);
    return this;
  }
  
  /**
   * Build the query string
   */
  build(): string {
    if (this.queryType === 'natural') {
      // Build natural language query
      let query = '';
      if (this.selectFields.length > 0) {
        query += `find ${this.selectFields.join(', ')} `;
      } else {
        query += 'find ';
      }
      
      if (this.fromTable) {
        query += `from ${this.fromTable} `;
      }
      
      if (this.conditions.length > 0) {
        query += `where ${this.conditions.join(' and ')} `;
      }
      
      if (this.orderByFields.length > 0) {
        query += `ordered by ${this.orderByFields.join(', ')} `;
      }
      
      if (this.limitValue) {
        query += `limit ${this.limitValue} `;
      }
      
      return query.trim();
    } else {
      // Build SQL query
      let query = 'SELECT ';
      
      if (this.selectFields.length > 0) {
        query += this.selectFields.join(', ');
      } else {
        query += '*';
      }
      
      if (this.fromTable) {
        query += ` FROM ${this.fromTable}`;
      }
      
      if (this.joins.length > 0) {
        query += ' ' + this.joins.join(' ');
      }
      
      if (this.conditions.length > 0) {
        query += ` WHERE ${this.conditions.join(' AND ')}`;
      }
      
      if (this.orderByFields.length > 0) {
        query += ` ORDER BY ${this.orderByFields.join(', ')}`;
      }
      
      if (this.limitValue) {
        query += ` LIMIT ${this.limitValue}`;
      }
      
      if (this.offsetValue) {
        query += ` OFFSET ${this.offsetValue}`;
      }
      
      return query;
    }
  }
  
  /**
   * Execute the built query
   */
  async execute<T = any>(options?: QueryOptions): Promise<QueryResult<T>> {
    const query = this.build();
    const response = await this.api.post('/query', {
      query,
      ...options
    });
    
    // Reset builder after execution
    this.reset();
    
    return response.data;
  }
  
  /**
   * Reset the query builder
   */
  reset(): void {
    this.conditions = [];
    this.selectFields = [];
    this.fromTable = '';
    this.joins = [];
    this.orderByFields = [];
    this.limitValue = undefined;
    this.offsetValue = undefined;
    this.queryType = 'sql';
  }
  
  /**
   * Create a raw query
   */
  static raw(query: string): QueryBuilder {
    const builder = new QueryBuilder(null as any);
    builder.conditions = [query];
    return builder;
  }
}