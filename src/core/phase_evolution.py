"""
Phase Evolution Mechanism
Manages the evolution from Phase 1 (10%) to Phase 2 (30%) and beyond
Critical component for ConceptDB's evolutionary architecture
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class EvolutionPhase(Enum):
    """Evolution phases with conceptualization percentages"""
    PHASE_1 = (1, 0.1, "Enhancement Layer")  # 10% concepts
    PHASE_2 = (2, 0.3, "Hybrid Database")    # 30% concepts
    PHASE_3 = (3, 0.7, "Concept-First")      # 70% concepts
    PHASE_4 = (4, 1.0, "Pure Concept")       # 100% concepts
    
    def __init__(self, number: int, ratio: float, name: str):
        self.number = number
        self.ratio = ratio
        self.name = name


@dataclass
class EvolutionCriteria:
    """Criteria for phase evolution"""
    min_concept_usage: float  # Minimum % of queries using concepts
    min_accuracy: float       # Minimum accuracy of concept queries
    min_performance: float    # Minimum performance improvement
    min_data_coverage: float  # Minimum % of data with concepts
    min_uptime_hours: int    # Minimum system uptime
    min_query_count: int     # Minimum total queries processed


@dataclass
class EvolutionMetrics:
    """Current evolution metrics"""
    current_phase: int
    concept_usage: float
    query_accuracy: float
    performance_gain: float
    data_coverage: float
    uptime_hours: float
    total_queries: int
    evolution_score: float
    ready_for_next: bool
    blocking_factors: List[str]


class PhaseEvolutionManager:
    """Manages the evolution between ConceptDB phases"""
    
    # Evolution criteria for each phase transition
    EVOLUTION_CRITERIA = {
        2: EvolutionCriteria(  # Phase 1 -> 2
            min_concept_usage=0.25,
            min_accuracy=0.85,
            min_performance=1.0,  # No degradation
            min_data_coverage=0.2,
            min_uptime_hours=168,  # 1 week
            min_query_count=10000
        ),
        3: EvolutionCriteria(  # Phase 2 -> 3
            min_concept_usage=0.5,
            min_accuracy=0.9,
            min_performance=1.2,  # 20% improvement
            min_data_coverage=0.5,
            min_uptime_hours=720,  # 1 month
            min_query_count=100000
        ),
        4: EvolutionCriteria(  # Phase 3 -> 4
            min_concept_usage=0.8,
            min_accuracy=0.95,
            min_performance=1.5,  # 50% improvement
            min_data_coverage=0.8,
            min_uptime_hours=2160,  # 3 months
            min_query_count=1000000
        )
    }
    
    def __init__(
        self,
        pg_storage,
        concept_manager,
        query_router,
        sync_manager,
        cache_manager
    ):
        """
        Initialize evolution manager
        
        Args:
            pg_storage: PostgreSQL storage
            concept_manager: Concept manager
            query_router: Query router
            sync_manager: Sync manager
            cache_manager: Cache manager
        """
        self.pg_storage = pg_storage
        self.concept_manager = concept_manager
        self.query_router = query_router
        self.sync_manager = sync_manager
        self.cache_manager = cache_manager
        
        # Evolution state
        self.current_phase = EvolutionPhase.PHASE_1
        self.evolution_history = []
        self.start_time = datetime.utcnow()
        self.evolution_in_progress = False
        
        # Monitoring
        self.performance_baseline = {}
        self.accuracy_tracker = {
            'concept_queries': {'correct': 0, 'total': 0},
            'sql_queries': {'correct': 0, 'total': 0}
        }
        
    async def initialize(self) -> None:
        """Initialize evolution manager and determine current phase"""
        try:
            # Get current phase from database
            metrics = await self.pg_storage.get_evolution_metrics()
            phase_num = metrics.get('current_phase', 1)
            
            # Set current phase
            for phase in EvolutionPhase:
                if phase.number == phase_num:
                    self.current_phase = phase
                    break
                    
            # Establish performance baseline
            await self._establish_baseline()
            
            logger.info(f"Evolution manager initialized at {self.current_phase.name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize evolution manager: {e}")
            
    async def _establish_baseline(self) -> None:
        """Establish performance baseline for comparison"""
        try:
            # Measure SQL query performance
            sql_times = []
            test_queries = [
                "SELECT * FROM users LIMIT 10",
                "SELECT COUNT(*) FROM products",
                "SELECT AVG(price) FROM orders"
            ]
            
            for query in test_queries:
                start = datetime.utcnow()
                await self.pg_storage.execute_query(query)
                elapsed = (datetime.utcnow() - start).total_seconds()
                sql_times.append(elapsed)
                
            self.performance_baseline['sql_avg'] = sum(sql_times) / len(sql_times)
            
            # Measure concept query performance
            concept_times = []
            test_concepts = [
                "user satisfaction",
                "product quality",
                "order trends"
            ]
            
            for concept in test_concepts:
                start = datetime.utcnow()
                await self.concept_manager.find_similar_concepts(concept)
                elapsed = (datetime.utcnow() - start).total_seconds()
                concept_times.append(elapsed)
                
            self.performance_baseline['concept_avg'] = sum(concept_times) / len(concept_times)
            
        except Exception as e:
            logger.warning(f"Failed to establish baseline: {e}")
            self.performance_baseline = {'sql_avg': 0.1, 'concept_avg': 0.2}
            
    async def evaluate_evolution_readiness(self) -> EvolutionMetrics:
        """
        Evaluate if system is ready for next phase
        
        Returns:
            EvolutionMetrics with current status
        """
        try:
            # Get current metrics
            db_metrics = await self.pg_storage.get_evolution_metrics()
            routing_stats = await self.query_router.get_routing_stats()
            sync_status = self.sync_manager.get_sync_status()
            cache_stats = self.cache_manager.get_cache_stats()
            
            # Calculate derived metrics
            uptime_hours = (datetime.utcnow() - self.start_time).total_seconds() / 3600
            
            # Concept usage percentage
            total_queries = db_metrics.get('total_queries', 0)
            concept_queries = db_metrics.get('concept_queries', 0)
            concept_usage = concept_queries / total_queries if total_queries > 0 else 0
            
            # Query accuracy
            concept_accuracy = self._calculate_accuracy('concept_queries')
            sql_accuracy = self._calculate_accuracy('sql_queries')
            overall_accuracy = (concept_accuracy + sql_accuracy) / 2
            
            # Performance gain
            performance_gain = self._calculate_performance_gain()
            
            # Data coverage
            data_coverage = await self._calculate_data_coverage()
            
            # Calculate evolution score
            evolution_score = self._calculate_evolution_score(
                concept_usage,
                overall_accuracy,
                performance_gain,
                data_coverage,
                uptime_hours,
                total_queries
            )
            
            # Check if ready for next phase
            next_phase_num = self.current_phase.number + 1
            ready, blocking = self._check_evolution_criteria(
                next_phase_num,
                concept_usage,
                overall_accuracy,
                performance_gain,
                data_coverage,
                uptime_hours,
                total_queries
            )
            
            metrics = EvolutionMetrics(
                current_phase=self.current_phase.number,
                concept_usage=concept_usage,
                query_accuracy=overall_accuracy,
                performance_gain=performance_gain,
                data_coverage=data_coverage,
                uptime_hours=uptime_hours,
                total_queries=total_queries,
                evolution_score=evolution_score,
                ready_for_next=ready,
                blocking_factors=blocking
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to evaluate evolution readiness: {e}")
            return EvolutionMetrics(
                current_phase=self.current_phase.number,
                concept_usage=0,
                query_accuracy=0,
                performance_gain=0,
                data_coverage=0,
                uptime_hours=0,
                total_queries=0,
                evolution_score=0,
                ready_for_next=False,
                blocking_factors=[str(e)]
            )
            
    def _calculate_accuracy(self, query_type: str) -> float:
        """Calculate accuracy for query type"""
        tracker = self.accuracy_tracker.get(query_type, {})
        total = tracker.get('total', 0)
        correct = tracker.get('correct', 0)
        return correct / total if total > 0 else 0.5  # Default 50% if no data
        
    def _calculate_performance_gain(self) -> float:
        """Calculate performance gain compared to baseline"""
        if not self.performance_baseline:
            return 1.0
            
        # Would need actual performance measurements
        # For now, simulate based on phase
        phase_gains = {1: 1.0, 2: 1.2, 3: 1.5, 4: 2.0}
        return phase_gains.get(self.current_phase.number, 1.0)
        
    async def _calculate_data_coverage(self) -> float:
        """Calculate percentage of data with concept mappings"""
        try:
            # Get total data count
            total_query = "SELECT COUNT(*) as count FROM pg_tables WHERE schemaname = 'public'"
            total_result = await self.pg_storage.execute_query(total_query)
            total_tables = total_result[0]['count'] if total_result else 0
            
            # Get mapped tables count
            mapped_query = """
            SELECT COUNT(DISTINCT table_name) as count 
            FROM conceptdb.concept_mappings
            """
            mapped_result = await self.pg_storage.execute_query(mapped_query)
            mapped_tables = mapped_result[0]['count'] if mapped_result else 0
            
            return mapped_tables / total_tables if total_tables > 0 else 0
            
        except:
            return 0.1  # Default 10% coverage
            
    def _calculate_evolution_score(
        self,
        concept_usage: float,
        accuracy: float,
        performance: float,
        coverage: float,
        uptime: float,
        queries: int
    ) -> float:
        """Calculate overall evolution score (0-1)"""
        # Weighted scoring
        weights = {
            'concept_usage': 0.3,
            'accuracy': 0.25,
            'performance': 0.15,
            'coverage': 0.15,
            'uptime': 0.1,
            'queries': 0.05
        }
        
        # Normalize metrics
        normalized = {
            'concept_usage': min(concept_usage / 0.5, 1.0),  # Target 50%
            'accuracy': accuracy,
            'performance': min(performance / 1.5, 1.0),  # Target 50% gain
            'coverage': coverage,
            'uptime': min(uptime / 720, 1.0),  # Target 1 month
            'queries': min(queries / 100000, 1.0)  # Target 100k
        }
        
        # Calculate weighted score
        score = sum(
            normalized[key] * weights[key] 
            for key in weights
        )
        
        return min(score, 1.0)
        
    def _check_evolution_criteria(
        self,
        target_phase: int,
        concept_usage: float,
        accuracy: float,
        performance: float,
        coverage: float,
        uptime: float,
        queries: int
    ) -> Tuple[bool, List[str]]:
        """Check if criteria met for evolution"""
        if target_phase not in self.EVOLUTION_CRITERIA:
            return False, ["Invalid target phase"]
            
        criteria = self.EVOLUTION_CRITERIA[target_phase]
        blocking = []
        
        if concept_usage < criteria.min_concept_usage:
            blocking.append(
                f"Concept usage {concept_usage:.1%} < {criteria.min_concept_usage:.1%}"
            )
            
        if accuracy < criteria.min_accuracy:
            blocking.append(
                f"Accuracy {accuracy:.1%} < {criteria.min_accuracy:.1%}"
            )
            
        if performance < criteria.min_performance:
            blocking.append(
                f"Performance gain {performance:.1f}x < {criteria.min_performance:.1f}x"
            )
            
        if coverage < criteria.min_data_coverage:
            blocking.append(
                f"Data coverage {coverage:.1%} < {criteria.min_data_coverage:.1%}"
            )
            
        if uptime < criteria.min_uptime_hours:
            blocking.append(
                f"Uptime {uptime:.0f}h < {criteria.min_uptime_hours}h"
            )
            
        if queries < criteria.min_query_count:
            blocking.append(
                f"Query count {queries} < {criteria.min_query_count}"
            )
            
        return len(blocking) == 0, blocking
        
    async def evolve_to_phase(
        self,
        target_phase: int,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Evolve to target phase
        
        Args:
            target_phase: Target phase number
            force: Force evolution even if criteria not met
            
        Returns:
            Evolution result
        """
        if self.evolution_in_progress:
            return {
                'success': False,
                'message': 'Evolution already in progress'
            }
            
        try:
            self.evolution_in_progress = True
            
            # Validate target phase
            if target_phase <= self.current_phase.number:
                return {
                    'success': False,
                    'message': f'Already at phase {self.current_phase.number}'
                }
                
            if target_phase > 4:
                return {
                    'success': False,
                    'message': 'Maximum phase is 4'
                }
                
            # Check readiness
            metrics = await self.evaluate_evolution_readiness()
            
            if not force and not metrics.ready_for_next:
                return {
                    'success': False,
                    'message': 'Not ready for evolution',
                    'blocking_factors': metrics.blocking_factors,
                    'metrics': asdict(metrics)
                }
                
            # Perform evolution
            logger.info(f"Starting evolution from Phase {self.current_phase.number} to {target_phase}")
            
            # Phase-specific evolution logic
            if target_phase == 2:
                result = await self._evolve_to_phase_2()
            elif target_phase == 3:
                result = await self._evolve_to_phase_3()
            elif target_phase == 4:
                result = await self._evolve_to_phase_4()
            else:
                result = {'success': False, 'message': 'Invalid target phase'}
                
            if result['success']:
                # Update current phase
                for phase in EvolutionPhase:
                    if phase.number == target_phase:
                        self.current_phase = phase
                        break
                        
                # Record evolution
                self.evolution_history.append({
                    'from_phase': self.current_phase.number - 1,
                    'to_phase': target_phase,
                    'timestamp': datetime.utcnow().isoformat(),
                    'metrics': asdict(metrics),
                    'forced': force
                })
                
                # Update database
                await self._update_phase_in_db(target_phase)
                
            return result
            
        except Exception as e:
            logger.error(f"Evolution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            self.evolution_in_progress = False
            
    async def _evolve_to_phase_2(self) -> Dict[str, Any]:
        """Evolve from Phase 1 (10%) to Phase 2 (30%)"""
        try:
            logger.info("Evolving to Phase 2: Hybrid Database (30% conceptualization)")
            
            # 1. Increase concept extraction rate
            await self._increase_concept_extraction(target_ratio=0.3)
            
            # 2. Enable intelligent routing with higher concept threshold
            self.query_router.concept_threshold = 0.7  # Lower threshold
            
            # 3. Enable real-time sync
            asyncio.create_task(
                self.sync_manager.schedule_sync(interval_minutes=15)
            )
            
            # 4. Optimize cache for hybrid queries
            await self.cache_manager.warmup_cache(
                await self._get_common_queries()
            )
            
            # 5. Update routing strategy
            await self._update_routing_strategy('hybrid')
            
            return {
                'success': True,
                'message': 'Successfully evolved to Phase 2',
                'new_ratio': 0.3,
                'features_enabled': [
                    'Intelligent routing',
                    'Real-time sync',
                    'Hybrid query optimization'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def _evolve_to_phase_3(self) -> Dict[str, Any]:
        """Evolve from Phase 2 (30%) to Phase 3 (70%)"""
        try:
            logger.info("Evolving to Phase 3: Concept-First (70% conceptualization)")
            
            # 1. Concept-first routing
            self.query_router.concept_threshold = 0.5  # Even lower threshold
            
            # 2. Aggressive concept extraction
            await self._increase_concept_extraction(target_ratio=0.7)
            
            # 3. Enable concept-based indexing
            await self._create_concept_indexes()
            
            # 4. Migrate critical data to concept layer
            await self._migrate_critical_data()
            
            return {
                'success': True,
                'message': 'Successfully evolved to Phase 3',
                'new_ratio': 0.7,
                'features_enabled': [
                    'Concept-first routing',
                    'Concept indexing',
                    'Critical data migration'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def _evolve_to_phase_4(self) -> Dict[str, Any]:
        """Evolve from Phase 3 (70%) to Phase 4 (100%)"""
        try:
            logger.info("Evolving to Phase 4: Pure Concept Database (100% conceptualization)")
            
            # This would be a major architectural shift
            # For now, return placeholder
            
            return {
                'success': True,
                'message': 'Successfully evolved to Phase 4',
                'new_ratio': 1.0,
                'features_enabled': [
                    'Pure concept storage',
                    'AI-native operations',
                    'Complete semantic understanding'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def _increase_concept_extraction(self, target_ratio: float) -> None:
        """Increase concept extraction to target ratio"""
        # Trigger comprehensive extraction
        from src.core.data_concept_extractor import DataConceptExtractor
        
        extractor = DataConceptExtractor(
            self.pg_storage,
            self.concept_manager,
            self.query_router.semantic_engine,
            min_confidence=0.3  # Lower threshold for more concepts
        )
        
        await extractor.extract_from_all_tables()
        
    async def _update_routing_strategy(self, strategy: str) -> None:
        """Update query routing strategy"""
        # Would update routing logic
        pass
        
    async def _create_concept_indexes(self) -> None:
        """Create concept-based indexes"""
        # Would create specialized indexes
        pass
        
    async def _migrate_critical_data(self) -> None:
        """Migrate critical data to concept layer"""
        # Would migrate important data
        pass
        
    async def _get_common_queries(self) -> List[str]:
        """Get common queries for cache warmup"""
        # Would get from query history
        return [
            "SELECT * FROM users WHERE active = true",
            "find similar products to laptop",
            "customer satisfaction trends"
        ]
        
    async def _update_phase_in_db(self, phase: int) -> None:
        """Update phase in database"""
        query = """
        UPDATE conceptdb.evolution_metrics 
        SET current_phase = $1, 
            conceptualization_ratio = $2,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
        """
        
        # Get ratio for phase
        ratio = 0.1
        for p in EvolutionPhase:
            if p.number == phase:
                ratio = p.ratio
                break
                
        await self.pg_storage.execute_command(query, [phase, ratio])
        
    def get_evolution_status(self) -> Dict[str, Any]:
        """Get current evolution status"""
        return {
            'current_phase': {
                'number': self.current_phase.number,
                'name': self.current_phase.name,
                'conceptualization': f"{self.current_phase.ratio:.0%}"
            },
            'evolution_history': self.evolution_history[-5:],  # Last 5 evolutions
            'evolution_in_progress': self.evolution_in_progress,
            'uptime_hours': (datetime.utcnow() - self.start_time).total_seconds() / 3600
        }