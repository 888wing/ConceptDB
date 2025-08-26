/**
 * Custom error classes for ConceptDB SDK
 */

/**
 * Base error class for ConceptDB errors
 */
export class ConceptDBError extends Error {
  public statusCode?: number;
  public details?: any;
  
  constructor(message: string, statusCode?: number, details?: any) {
    super(message);
    this.name = 'ConceptDBError';
    this.statusCode = statusCode;
    this.details = details;
    
    // Maintains proper stack trace for where our error was thrown
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ConceptDBError);
    }
  }
  
  /**
   * Check if error is retryable
   */
  isRetryable(): boolean {
    return this.statusCode ? this.statusCode >= 500 : false;
  }
  
  /**
   * Get formatted error message
   */
  toJSON(): Record<string, any> {
    return {
      name: this.name,
      message: this.message,
      statusCode: this.statusCode,
      details: this.details,
      stack: this.stack
    };
  }
}

/**
 * Network error - connection issues
 */
export class NetworkError extends ConceptDBError {
  constructor(message: string, details?: any) {
    super(message, undefined, details);
    this.name = 'NetworkError';
  }
  
  isRetryable(): boolean {
    return true;
  }
}

/**
 * Validation error - invalid input
 */
export class ValidationError extends ConceptDBError {
  public fields?: Record<string, string[]>;
  
  constructor(message: string, fields?: Record<string, string[]>) {
    super(message, 400, { fields });
    this.name = 'ValidationError';
    this.fields = fields;
  }
  
  isRetryable(): boolean {
    return false;
  }
}

/**
 * Authentication error
 */
export class AuthenticationError extends ConceptDBError {
  constructor(message = 'Authentication failed') {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
  
  isRetryable(): boolean {
    return false;
  }
}

/**
 * Authorization error
 */
export class AuthorizationError extends ConceptDBError {
  constructor(message = 'Insufficient permissions') {
    super(message, 403);
    this.name = 'AuthorizationError';
  }
  
  isRetryable(): boolean {
    return false;
  }
}

/**
 * Not found error
 */
export class NotFoundError extends ConceptDBError {
  public resourceType?: string;
  public resourceId?: string;
  
  constructor(resourceType?: string, resourceId?: string) {
    const message = resourceType && resourceId
      ? `${resourceType} with ID '${resourceId}' not found`
      : 'Resource not found';
    
    super(message, 404, { resourceType, resourceId });
    this.name = 'NotFoundError';
    this.resourceType = resourceType;
    this.resourceId = resourceId;
  }
  
  isRetryable(): boolean {
    return false;
  }
}

/**
 * Conflict error - resource already exists
 */
export class ConflictError extends ConceptDBError {
  constructor(message: string, details?: any) {
    super(message, 409, details);
    this.name = 'ConflictError';
  }
  
  isRetryable(): boolean {
    return false;
  }
}

/**
 * Rate limit error
 */
export class RateLimitError extends ConceptDBError {
  public retryAfter?: number;
  
  constructor(message = 'Rate limit exceeded', retryAfter?: number) {
    super(message, 429, { retryAfter });
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
  
  isRetryable(): boolean {
    return true;
  }
}

/**
 * Timeout error
 */
export class TimeoutError extends ConceptDBError {
  public timeout: number;
  
  constructor(timeout: number) {
    super(`Request timed out after ${timeout}ms`);
    this.name = 'TimeoutError';
    this.timeout = timeout;
  }
  
  isRetryable(): boolean {
    return true;
  }
}

/**
 * Server error - internal server error
 */
export class ServerError extends ConceptDBError {
  constructor(message = 'Internal server error', statusCode = 500, details?: any) {
    super(message, statusCode, details);
    this.name = 'ServerError';
  }
  
  isRetryable(): boolean {
    return true;
  }
}

/**
 * Evolution error - phase transition issues
 */
export class EvolutionError extends ConceptDBError {
  public currentPhase: number;
  public targetPhase?: number;
  public blockers: string[];
  
  constructor(
    message: string,
    currentPhase: number,
    targetPhase?: number,
    blockers: string[] = []
  ) {
    super(message, 422, { currentPhase, targetPhase, blockers });
    this.name = 'EvolutionError';
    this.currentPhase = currentPhase;
    this.targetPhase = targetPhase;
    this.blockers = blockers;
  }
  
  isRetryable(): boolean {
    return false;
  }
}

/**
 * Query error - issues with query execution
 */
export class QueryError extends ConceptDBError {
  public query: string;
  public layer?: string;
  
  constructor(message: string, query: string, layer?: string) {
    super(message, 400, { query, layer });
    this.name = 'QueryError';
    this.query = query;
    this.layer = layer;
  }
  
  isRetryable(): boolean {
    return false;
  }
}

/**
 * Configuration error
 */
export class ConfigurationError extends ConceptDBError {
  public missingFields?: string[];
  
  constructor(message: string, missingFields?: string[]) {
    super(message, undefined, { missingFields });
    this.name = 'ConfigurationError';
    this.missingFields = missingFields;
  }
  
  isRetryable(): boolean {
    return false;
  }
}

/**
 * Error factory for creating appropriate error types from API responses
 */
export class ErrorFactory {
  static fromResponse(response: any): ConceptDBError {
    const status = response.status;
    const data = response.data || {};
    const message = data.detail || data.error || data.message || 'Unknown error';
    
    switch (status) {
      case 400:
        if (data.fields) {
          return new ValidationError(message, data.fields);
        }
        if (data.query) {
          return new QueryError(message, data.query, data.layer);
        }
        return new ValidationError(message);
      
      case 401:
        return new AuthenticationError(message);
      
      case 403:
        return new AuthorizationError(message);
      
      case 404:
        return new NotFoundError(data.resourceType, data.resourceId);
      
      case 409:
        return new ConflictError(message, data);
      
      case 422:
        if (data.currentPhase !== undefined) {
          return new EvolutionError(
            message,
            data.currentPhase,
            data.targetPhase,
            data.blockers
          );
        }
        return new ValidationError(message);
      
      case 429:
        return new RateLimitError(message, data.retryAfter);
      
      case 500:
      case 502:
      case 503:
      case 504:
        return new ServerError(message, status, data);
      
      default:
        return new ConceptDBError(message, status, data);
    }
  }
}