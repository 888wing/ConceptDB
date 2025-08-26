"""
Evolution Tracker
Monitors and manages database evolution from SQL to conceptual operations
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from enum import Enum

from .pg_storage import PostgreSQLStorage

logger = logging.getLogger(__name__)


class EvolutionPhase(Enum):
    """Evolution phases of the database"""
    PHASE_1 = 1  # 10% conceptualization
    PHASE_2 = 2  # 30% conceptualization  
    PHASE_3 = 3  # 70% conceptualization
    PHASE_4 = 4  # 100% conceptualization


class EvolutionTracker:
    """Tracks and manages the evolution of database from SQL to concepts"""
    
    def __init__(self, pg_storage: PostgreSQLStorage):
        self.pg_storage = pg_storage
        self.current_phase = EvolutionPhase.PHASE_1
        self.target_ratios = {
            EvolutionPhase.PHASE_1: 0.10,
            EvolutionPhase.PHASE_2: 0.30,
            EvolutionPhase.PHASE_3: 0.70,
            EvolutionPhase.PHASE_4: 1.00
        }
        
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current evolution metrics"""
        try:
            # Get metrics from PostgreSQL
            metrics = await self.pg_storage.get_evolution_metrics()
            
            # Calculate additional metrics
            total_queries = metrics.get('total_queries', 0)
            concept_queries = metrics.get('concept_queries', 0)
            sql_queries = metrics.get('sql_queries', 0)
            
            if total_queries > 0:
                actual_ratio = concept_queries / total_queries
                sql_ratio = sql_queries / total_queries
            else:
                actual_ratio = 0.0
                sql_ratio = 1.0
                
            # Determine readiness for next phase
            target_ratio = self.target_ratios[self.current_phase]
            phase_progress = (actual_ratio / target_ratio) * 100 if target_ratio > 0 else 0
            
            return {
                'current_phase': self.current_phase.value,
                'phase_name': self._get_phase_name(self.current_phase),
                'target_conceptualization': target_ratio,
                'actual_conceptualization': actual_ratio,
                'sql_ratio': sql_ratio,
                'phase_progress': min(phase_progress, 100),
                'total_queries': total_queries,
                'concept_queries': concept_queries,
                'sql_queries': sql_queries,
                'evolution_ready': phase_progress >= 80,
                'next_phase': self._get_next_phase(),
                'metrics_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get evolution metrics: {e}")
            return self._default_metrics()
            
    async def track_query(
        self,
        query_type: str,
        route: str,
        confidence: float,
        execution_time: float
    ) -> None:
        """Track a query for evolution metrics"""
        try:
            query = """
                INSERT INTO query_logs 
                (query_type, route, confidence, execution_time, timestamp)
                VALUES ($1, $2, $3, $4, $5)
            """
            
            await self.pg_storage.execute_query(
                query,
                [query_type, route, confidence, execution_time, datetime.utcnow()]
            )
            
            # Update aggregated metrics
            await self._update_aggregated_metrics(route)
            
        except Exception as e:
            logger.error(f"Failed to track query: {e}")
            
    async def get_evolution_timeline(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get evolution progress over time"""
        try:
            query = """
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN route = 'concepts' THEN 1 ELSE 0 END) as concept_queries,
                    SUM(CASE WHEN route = 'postgres' THEN 1 ELSE 0 END) as sql_queries,
                    AVG(confidence) as avg_confidence,
                    AVG(execution_time) as avg_execution_time
                FROM query_logs
                WHERE timestamp >= $1
                GROUP BY DATE(timestamp)
                ORDER BY date
            """
            
            start_date = datetime.utcnow() - timedelta(days=days)
            results = await self.pg_storage.execute_query(query, [start_date])
            
            timeline = []
            for row in results:
                total = row['total_queries']
                concept = row['concept_queries']
                
                timeline.append({
                    'date': row['date'].isoformat() if row['date'] else None,
                    'total_queries': total,
                    'concept_queries': concept,
                    'sql_queries': row['sql_queries'],
                    'conceptualization_ratio': concept / total if total > 0 else 0,
                    'avg_confidence': float(row['avg_confidence']) if row['avg_confidence'] else 0,
                    'avg_execution_time': float(row['avg_execution_time']) if row['avg_execution_time'] else 0
                })
                
            return timeline
            
        except Exception as e:
            logger.error(f"Failed to get evolution timeline: {e}")
            return []
            
    async def check_evolution_readiness(self) -> Dict[str, Any]:
        """Check if system is ready to evolve to next phase"""
        try:
            metrics = await self.get_current_metrics()
            
            # Criteria for evolution
            criteria = {
                'conceptualization_target_met': metrics['phase_progress'] >= 80,
                'minimum_queries': metrics['total_queries'] >= 1000,
                'confidence_threshold': await self._check_confidence_threshold(),
                'performance_acceptable': await self._check_performance(),
                'error_rate_low': await self._check_error_rate()
            }
            
            all_criteria_met = all(criteria.values())
            
            return {
                'ready': all_criteria_met,
                'criteria': criteria,
                'current_phase': metrics['current_phase'],
                'next_phase': metrics['next_phase'],
                'recommendation': self._get_evolution_recommendation(criteria, metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to check evolution readiness: {e}")
            return {
                'ready': False,
                'error': str(e)
            }
            
    async def trigger_evolution(self) -> Dict[str, Any]:
        """Trigger evolution to next phase"""
        try:
            readiness = await self.check_evolution_readiness()
            
            if not readiness['ready']:
                return {
                    'success': False,
                    'message': 'System not ready for evolution',
                    'details': readiness
                }
                
            # Get next phase
            next_phase = self._get_next_phase_enum()
            if not next_phase:
                return {
                    'success': False,
                    'message': 'Already at maximum evolution phase'
                }
                
            # Update phase
            old_phase = self.current_phase
            self.current_phase = next_phase
            
            # Log evolution event
            await self._log_evolution_event(old_phase, next_phase)
            
            # Update system configuration
            await self._update_system_configuration(next_phase)
            
            return {
                'success': True,
                'message': f'Successfully evolved from {old_phase.name} to {next_phase.name}',
                'old_phase': old_phase.value,
                'new_phase': next_phase.value,
                'new_target_ratio': self.target_ratios[next_phase]
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger evolution: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def get_routing_statistics(self) -> Dict[str, Any]:
        """Get detailed routing statistics"""
        try:
            query = """
                SELECT 
                    route,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence,
                    AVG(execution_time) as avg_time,
                    MIN(execution_time) as min_time,
                    MAX(execution_time) as max_time,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY execution_time) as median_time,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time) as p95_time
                FROM query_logs
                WHERE timestamp >= $1
                GROUP BY route
            """
            
            # Last 24 hours
            start_date = datetime.utcnow() - timedelta(days=1)
            results = await self.pg_storage.execute_query(query, [start_date])
            
            stats = {}
            for row in results:
                stats[row['route']] = {
                    'count': row['count'],
                    'avg_confidence': float(row['avg_confidence']) if row['avg_confidence'] else 0,
                    'performance': {
                        'avg_time': float(row['avg_time']) if row['avg_time'] else 0,
                        'min_time': float(row['min_time']) if row['min_time'] else 0,
                        'max_time': float(row['max_time']) if row['max_time'] else 0,
                        'median_time': float(row['median_time']) if row['median_time'] else 0,
                        'p95_time': float(row['p95_time']) if row['p95_time'] else 0
                    }
                }
                
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get routing statistics: {e}")
            return {}
            
    async def get_concept_adoption_metrics(self) -> Dict[str, Any]:
        """Get metrics on concept adoption and usage"""
        try:
            # Get concept usage stats
            query = """
                SELECT 
                    COUNT(DISTINCT id) as total_concepts,
                    AVG(usage_count) as avg_usage,
                    MAX(usage_count) as max_usage,
                    AVG(confidence_score) as avg_confidence
                FROM concepts
            """
            
            concept_stats = await self.pg_storage.execute_query(query)
            
            # Get relationship stats
            rel_query = """
                SELECT 
                    relationship_type,
                    COUNT(*) as count,
                    AVG(strength) as avg_strength
                FROM concept_relationships
                GROUP BY relationship_type
            """
            
            rel_stats = await self.pg_storage.execute_query(rel_query)
            
            return {
                'total_concepts': concept_stats[0]['total_concepts'] if concept_stats else 0,
                'avg_concept_usage': float(concept_stats[0]['avg_usage']) if concept_stats else 0,
                'max_concept_usage': concept_stats[0]['max_usage'] if concept_stats else 0,
                'avg_concept_confidence': float(concept_stats[0]['avg_confidence']) if concept_stats else 0,
                'relationships': {
                    row['relationship_type']: {
                        'count': row['count'],
                        'avg_strength': float(row['avg_strength'])
                    }
                    for row in rel_stats
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get concept adoption metrics: {e}")
            return {}
            
    # Private helper methods
    
    def _get_phase_name(self, phase: EvolutionPhase) -> str:
        """Get human-readable phase name"""
        names = {
            EvolutionPhase.PHASE_1: "Enhancement Layer (10%)",
            EvolutionPhase.PHASE_2: "Hybrid Database (30%)",
            EvolutionPhase.PHASE_3: "Concept-First (70%)",
            EvolutionPhase.PHASE_4: "Pure Concept Database (100%)"
        }
        return names.get(phase, "Unknown")
        
    def _get_next_phase(self) -> Optional[int]:
        """Get next phase number"""
        if self.current_phase == EvolutionPhase.PHASE_4:
            return None
        return self.current_phase.value + 1
        
    def _get_next_phase_enum(self) -> Optional[EvolutionPhase]:
        """Get next phase enum"""
        next_value = self._get_next_phase()
        if next_value:
            return EvolutionPhase(next_value)
        return None
        
    def _default_metrics(self) -> Dict[str, Any]:
        """Return default metrics when database is not available"""
        return {
            'current_phase': 1,
            'phase_name': self._get_phase_name(EvolutionPhase.PHASE_1),
            'target_conceptualization': 0.10,
            'actual_conceptualization': 0.0,
            'sql_ratio': 1.0,
            'phase_progress': 0.0,
            'total_queries': 0,
            'concept_queries': 0,
            'sql_queries': 0,
            'evolution_ready': False,
            'next_phase': 2,
            'metrics_timestamp': datetime.utcnow().isoformat()
        }
        
    async def _update_aggregated_metrics(self, route: str) -> None:
        """Update aggregated metrics table"""
        try:
            query = """
                INSERT INTO evolution_metrics 
                (phase, conceptualization_ratio, total_queries, sql_queries, concept_queries, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (phase) DO UPDATE
                SET total_queries = evolution_metrics.total_queries + 1,
                    sql_queries = evolution_metrics.sql_queries + CASE WHEN $7 = 'postgres' THEN 1 ELSE 0 END,
                    concept_queries = evolution_metrics.concept_queries + CASE WHEN $7 = 'concepts' THEN 1 ELSE 0 END,
                    conceptualization_ratio = 
                        CAST(evolution_metrics.concept_queries + CASE WHEN $7 = 'concepts' THEN 1 ELSE 0 END AS FLOAT) / 
                        CAST(evolution_metrics.total_queries + 1 AS FLOAT),
                    timestamp = $6
            """
            
            metrics = await self.get_current_metrics()
            
            await self.pg_storage.execute_query(
                query,
                [
                    self.current_phase.value,
                    metrics['actual_conceptualization'],
                    metrics['total_queries'] + 1,
                    metrics['sql_queries'] + (1 if route == 'postgres' else 0),
                    metrics['concept_queries'] + (1 if route == 'concepts' else 0),
                    datetime.utcnow(),
                    route
                ]
            )
        except Exception as e:
            logger.error(f"Failed to update aggregated metrics: {e}")
            
    async def _check_confidence_threshold(self) -> bool:
        """Check if average confidence meets threshold"""
        try:
            query = """
                SELECT AVG(confidence) as avg_confidence
                FROM query_logs
                WHERE route = 'concepts'
                AND timestamp >= $1
            """
            
            start_date = datetime.utcnow() - timedelta(days=7)
            result = await self.pg_storage.execute_query(query, [start_date])
            
            if result and result[0]['avg_confidence']:
                return float(result[0]['avg_confidence']) >= 0.7
            return False
            
        except Exception as e:
            logger.error(f"Failed to check confidence threshold: {e}")
            return False
            
    async def _check_performance(self) -> bool:
        """Check if performance meets requirements"""
        try:
            query = """
                SELECT 
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time) as p95_time
                FROM query_logs
                WHERE timestamp >= $1
            """
            
            start_date = datetime.utcnow() - timedelta(days=1)
            result = await self.pg_storage.execute_query(query, [start_date])
            
            if result and result[0]['p95_time']:
                # P95 should be under 500ms
                return float(result[0]['p95_time']) < 0.5
            return True
            
        except Exception as e:
            logger.error(f"Failed to check performance: {e}")
            return False
            
    async def _check_error_rate(self) -> bool:
        """Check if error rate is acceptable"""
        try:
            # For now, return True as we don't track errors yet
            # In production, this would check error logs
            return True
            
        except Exception as e:
            logger.error(f"Failed to check error rate: {e}")
            return False
            
    def _get_evolution_recommendation(
        self,
        criteria: Dict[str, bool],
        metrics: Dict[str, Any]
    ) -> str:
        """Get recommendation for evolution"""
        if all(criteria.values()):
            return f"System ready to evolve to Phase {metrics['next_phase']}"
            
        issues = []
        if not criteria.get('conceptualization_target_met'):
            issues.append(f"Increase concept usage (current: {metrics['actual_conceptualization']:.1%})")
        if not criteria.get('minimum_queries'):
            issues.append(f"Need more queries (current: {metrics['total_queries']})")
        if not criteria.get('confidence_threshold'):
            issues.append("Improve query confidence scores")
        if not criteria.get('performance_acceptable'):
            issues.append("Optimize query performance")
        if not criteria.get('error_rate_low'):
            issues.append("Reduce error rate")
            
        return f"Address issues: {', '.join(issues)}"
        
    async def _log_evolution_event(
        self,
        old_phase: EvolutionPhase,
        new_phase: EvolutionPhase
    ) -> None:
        """Log evolution event"""
        try:
            query = """
                INSERT INTO evolution_events 
                (old_phase, new_phase, timestamp, metadata)
                VALUES ($1, $2, $3, $4)
            """
            
            metadata = {
                'old_phase_name': self._get_phase_name(old_phase),
                'new_phase_name': self._get_phase_name(new_phase),
                'old_target': self.target_ratios[old_phase],
                'new_target': self.target_ratios[new_phase]
            }
            
            await self.pg_storage.execute_query(
                query,
                [old_phase.value, new_phase.value, datetime.utcnow(), json.dumps(metadata)]
            )
            
        except Exception as e:
            logger.error(f"Failed to log evolution event: {e}")
            
    async def _update_system_configuration(self, phase: EvolutionPhase) -> None:
        """Update system configuration for new phase"""
        try:
            # Update configuration in database
            query = """
                INSERT INTO system_config (key, value, updated_at)
                VALUES ('evolution_phase', $1, $2)
                ON CONFLICT (key) DO UPDATE
                SET value = $1, updated_at = $2
            """
            
            await self.pg_storage.execute_query(
                query,
                [phase.value, datetime.utcnow()]
            )
            
            logger.info(f"System configuration updated to Phase {phase.value}")
            
        except Exception as e:
            logger.error(f"Failed to update system configuration: {e}")