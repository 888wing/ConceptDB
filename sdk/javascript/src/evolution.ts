import { AxiosInstance } from 'axios';
import { ConceptDBConfig, EvolutionMetrics } from './types';

export class EvolutionTracker {
  private queryStats = {
    sql: 0,
    concept: 0,
    hybrid: 0
  };
  
  constructor(
    private api: AxiosInstance,
    private config: ConceptDBConfig
  ) {}
  
  /**
   * Get current evolution metrics
   */
  async getMetrics(): Promise<EvolutionMetrics> {
    const response = await this.api.get('/metrics/evolution');
    return response.data;
  }
  
  /**
   * Track a query for evolution purposes
   */
  async trackQuery(type: 'sql' | 'concept' | 'hybrid'): Promise<void> {
    this.queryStats[type]++;
    
    // Check if we should trigger evolution
    const total = this.queryStats.sql + this.queryStats.concept + this.queryStats.hybrid;
    if (total % 100 === 0) {
      await this.checkEvolutionReadiness();
    }
  }
  
  /**
   * Check if the system is ready to evolve
   */
  async checkEvolutionReadiness(): Promise<boolean> {
    const metrics = await this.getMetrics();
    
    // Check evolution criteria based on current phase
    switch (metrics.current_phase) {
      case 1:
        // Ready for phase 2 if concept queries > 20%
        return metrics.concept_queries / metrics.total_queries > 0.2;
      case 2:
        // Ready for phase 3 if concept queries > 50%
        return metrics.concept_queries / metrics.total_queries > 0.5;
      case 3:
        // Ready for phase 4 if concept queries > 80%
        return metrics.concept_queries / metrics.total_queries > 0.8;
      default:
        return false;
    }
  }
  
  /**
   * Trigger evolution to the next phase
   */
  async evolve(targetPhase?: number): Promise<any> {
    const response = await this.api.post('/evolve', {
      target_phase: targetPhase || this.config.phase! + 1
    });
    
    if (response.data.success) {
      this.config.phase = response.data.new_phase;
    }
    
    return response.data;
  }
  
  /**
   * Get evolution timeline
   */
  async getTimeline(): Promise<any> {
    const response = await this.api.get('/metrics/evolution/timeline');
    return response.data;
  }
  
  /**
   * Get routing statistics
   */
  async getRoutingStats(): Promise<any> {
    const response = await this.api.get('/metrics/routing');
    return response.data;
  }
  
  /**
   * Get concept coverage metrics
   */
  async getConceptCoverage(): Promise<any> {
    const response = await this.api.get('/metrics/coverage');
    return response.data;
  }
  
  /**
   * Simulate evolution to see impact
   */
  async simulate(targetPhase: number): Promise<any> {
    const response = await this.api.post('/evolve/simulate', {
      target_phase: targetPhase
    });
    return response.data;
  }
  
  /**
   * Get evolution recommendations
   */
  async getRecommendations(): Promise<string[]> {
    const metrics = await this.getMetrics();
    const recommendations: string[] = [];
    
    // Base recommendations on current metrics
    if (metrics.conceptualization_ratio < 0.1) {
      recommendations.push('Import more data to build concept relationships');
      recommendations.push('Enable auto-concept extraction on imports');
    } else if (metrics.conceptualization_ratio < 0.3) {
      recommendations.push('Consider evolving to Phase 2 for hybrid storage');
      recommendations.push('Increase concept extraction rate');
    } else if (metrics.conceptualization_ratio < 0.7) {
      recommendations.push('Ready for Phase 3 - concept-first architecture');
      recommendations.push('Optimize concept relationship graphs');
    } else {
      recommendations.push('System ready for full conceptualization');
      recommendations.push('Consider Phase 4 pure concept database');
    }
    
    // Add performance-based recommendations
    const routingStats = await this.getRoutingStats();
    if (routingStats.avg_response_time > 500) {
      recommendations.push('Consider adding indexes to improve query performance');
    }
    
    if (routingStats.concept_hit_rate < 0.5) {
      recommendations.push('Improve concept coverage by extracting more concepts');
    }
    
    return recommendations;
  }
  
  /**
   * Reset evolution metrics (for testing)
   */
  async reset(): Promise<any> {
    const response = await this.api.post('/metrics/reset');
    this.queryStats = { sql: 0, concept: 0, hybrid: 0 };
    return response.data;
  }
}