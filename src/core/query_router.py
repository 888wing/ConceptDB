"""
Query Router
Intelligently routes queries between PostgreSQL (90%) and Concept Layer (10%)
"""

import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import logging
from enum import Enum

from src.core.pg_storage import PostgreSQLStorage
from src.core.vector_store import QdrantStore
from src.core.semantic_engine import SemanticEngine

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries based on intent"""
    SQL = "sql"
    NATURAL_LANGUAGE = "natural_language"
    HYBRID = "hybrid"
    

class RouteDecision(Enum):
    """Routing decisions for queries"""
    POSTGRES = "postgres"
    CONCEPTS = "concepts"
    BOTH = "both"


class QueryRouter:
    """Routes queries intelligently between PostgreSQL and Concept Layer"""
    
    def __init__(
        self,
        pg_storage: PostgreSQLStorage,
        vector_store: QdrantStore,
        semantic_engine: SemanticEngine,
        concept_threshold: float = 0.8
    ):
        self.pg_storage = pg_storage
        self.vector_store = vector_store
        self.semantic_engine = semantic_engine
        self.concept_threshold = concept_threshold
        
        # Keywords indicating semantic/natural language queries
        self.semantic_keywords = [
            'similar', 'like', 'related', 'might', 'could', 
            'probably', 'seems', 'about', 'around', 'near',
            'suggest', 'recommend', 'find me', 'show me'
        ]
        
        # SQL keywords indicating structured queries
        self.sql_keywords = [
            'select', 'from', 'where', 'insert', 'update',
            'delete', 'join', 'group by', 'order by', 'having'
        ]
        
    async def route_query(self, query: str) -> Dict[str, Any]:
        """
        Main routing logic - determines where to send the query
        
        Returns:
            Dict containing:
            - route: Where the query was routed (postgres/concepts/both)
            - results: Query results
            - confidence: Confidence in routing decision
            - explanation: Why this routing was chosen
        """
        try:
            # Analyze query to determine type and confidence
            query_type, confidence = await self._analyze_query(query)
            
            # Determine routing based on type and confidence
            route_decision = self._determine_route(query_type, confidence)
            
            # Execute query based on routing decision
            results = await self._execute_routed_query(
                query, 
                route_decision,
                query_type
            )
            
            # Track routing decision for evolution metrics
            await self._track_routing(
                query, 
                query_type,
                route_decision, 
                confidence,
                len(results)
            )
            
            return {
                'route': route_decision.value,
                'query_type': query_type.value,
                'results': results,
                'confidence': confidence,
                'explanation': self._get_routing_explanation(
                    query_type, 
                    confidence,
                    route_decision
                )
            }
            
        except Exception as e:
            logger.error(f"Query routing failed: {e}")
            # Fallback to PostgreSQL for safety
            return await self._fallback_to_postgres(query, str(e))
            
    async def _analyze_query(self, query: str) -> Tuple[QueryType, float]:
        """
        Analyze query to determine its type and confidence score
        """
        query_lower = query.lower()
        
        # Check for SQL keywords
        sql_score = sum(1 for keyword in self.sql_keywords 
                       if keyword in query_lower)
        
        # Check for semantic keywords
        semantic_score = sum(1 for keyword in self.semantic_keywords 
                           if keyword in query_lower)
        
        # Check query structure
        has_sql_structure = bool(re.match(
            r'^\s*(select|insert|update|delete|with)\s+', 
            query_lower
        ))
        
        # Calculate confidence scores
        if has_sql_structure or sql_score >= 2:
            return QueryType.SQL, 0.95
        elif semantic_score >= 2:
            confidence = min(0.5 + (semantic_score * 0.15), 0.95)
            return QueryType.NATURAL_LANGUAGE, confidence
        elif sql_score > 0 and semantic_score > 0:
            confidence = 0.6
            return QueryType.HYBRID, confidence
        else:
            # Default: try to understand intent through complexity
            complexity = await self._analyze_complexity(query)
            if complexity > 0.5:
                return QueryType.NATURAL_LANGUAGE, complexity
            else:
                return QueryType.SQL, 0.7
                
    async def _analyze_complexity(self, query: str) -> float:
        """
        Analyze query complexity to help determine routing
        """
        try:
            # Use PostgreSQL's EXPLAIN to estimate complexity
            complexity_metrics = await self.pg_storage.analyze_query_complexity(
                f"SELECT * FROM customers WHERE name ILIKE '%{query}%'"
            )
            return complexity_metrics.get('complexity_score', 0.5)
        except:
            # If analysis fails, return moderate complexity
            return 0.5
            
    def _determine_route(
        self, 
        query_type: QueryType, 
        confidence: float
    ) -> RouteDecision:
        """
        Determine where to route the query based on type and confidence
        """
        if query_type == QueryType.SQL:
            # Pure SQL goes to PostgreSQL
            return RouteDecision.POSTGRES
        elif query_type == QueryType.NATURAL_LANGUAGE:
            # Natural language with high confidence goes to concepts
            if confidence >= self.concept_threshold:
                return RouteDecision.CONCEPTS
            else:
                # Low confidence: try both
                return RouteDecision.BOTH
        else:  # HYBRID
            # Hybrid queries should check both layers
            return RouteDecision.BOTH
            
    async def _execute_routed_query(
        self,
        query: str,
        route: RouteDecision,
        query_type: QueryType
    ) -> List[Dict[str, Any]]:
        """
        Execute query based on routing decision
        """
        results = []
        
        if route == RouteDecision.POSTGRES:
            # Execute in PostgreSQL only
            results = await self._execute_postgres_query(query, query_type)
            
        elif route == RouteDecision.CONCEPTS:
            # Execute in Concept Layer only
            results = await self._execute_concept_query(query)
            
        else:  # BOTH
            # Execute in both and merge results
            postgres_task = self._execute_postgres_query(query, query_type)
            concept_task = self._execute_concept_query(query)
            
            postgres_results, concept_results = await asyncio.gather(
                postgres_task, 
                concept_task,
                return_exceptions=True
            )
            
            # Handle exceptions and merge results
            if not isinstance(postgres_results, Exception):
                results.extend(postgres_results)
            if not isinstance(concept_results, Exception):
                results.extend(concept_results)
                
            # Remove duplicates while preserving order
            seen = set()
            unique_results = []
            for item in results:
                item_id = item.get('id', str(item))
                if item_id not in seen:
                    seen.add(item_id)
                    unique_results.append(item)
            results = unique_results
            
        return results
        
    async def _execute_postgres_query(
        self,
        query: str,
        query_type: QueryType
    ) -> List[Dict[str, Any]]:
        """
        Execute query in PostgreSQL
        """
        try:
            if query_type == QueryType.SQL:
                # Direct SQL execution
                return await self.pg_storage.execute_query(query)
            else:
                # Convert natural language to SQL (simple approach for Phase 1)
                sql_query = self._convert_to_sql(query)
                if sql_query:
                    return await self.pg_storage.execute_query(sql_query)
                else:
                    return []
        except Exception as e:
            logger.error(f"PostgreSQL query failed: {e}")
            return []
            
    async def _execute_concept_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute query in Concept Layer using vector search
        """
        try:
            # Convert query to vector
            query_vector = await self.semantic_engine.text_to_vector(query)
            
            # Search for similar concepts
            concept_results = await self.vector_store.search(
                vector=query_vector,
                limit=10
            )
            
            # Convert concept results to standard format
            results = []
            for concept in concept_results:
                results.append({
                    'id': concept.get('id'),
                    'type': 'concept',
                    'score': concept.get('score'),
                    'data': concept.get('payload', {}),
                    'source': 'concept_layer'
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Concept query failed: {e}")
            return []
            
    def _convert_to_sql(self, natural_query: str) -> Optional[str]:
        """
        Simple natural language to SQL conversion for Phase 1
        This will be enhanced with LLM in later phases
        """
        query_lower = natural_query.lower()
        
        # Simple pattern matching for common queries
        patterns = [
            (r'find all (\w+)', r'SELECT * FROM \1'),
            (r'find (\w+) where (\w+) (?:is|equals?) (.+)', 
             r"SELECT * FROM \1 WHERE \2 = '\3'"),
            (r'show me (\w+)', r'SELECT * FROM \1 LIMIT 10'),
            (r'count (\w+)', r'SELECT COUNT(*) FROM \1'),
            (r'(\w+) with (\w+) greater than (\d+)', 
             r'SELECT * FROM \1 WHERE \2 > \3'),
        ]
        
        for pattern, replacement in patterns:
            match = re.search(pattern, query_lower)
            if match:
                return re.sub(pattern, replacement, query_lower)
                
        return None
        
    async def _track_routing(
        self,
        query: str,
        query_type: QueryType,
        route: RouteDecision,
        confidence: float,
        result_count: int
    ) -> None:
        """
        Track routing decision for evolution metrics
        """
        try:
            # Calculate execution time (simple approximation for Phase 1)
            execution_time_ms = int(confidence * 100)
            
            await self.pg_storage.track_query_routing(
                query_text=query,
                query_type=query_type.value,
                routing_decision=route.value,
                confidence_score=confidence,
                execution_time_ms=execution_time_ms,
                result_count=result_count
            )
        except Exception as e:
            logger.warning(f"Failed to track routing: {e}")
            
    def _get_routing_explanation(
        self,
        query_type: QueryType,
        confidence: float,
        route: RouteDecision
    ) -> str:
        """
        Generate human-readable explanation for routing decision
        """
        if route == RouteDecision.POSTGRES:
            if query_type == QueryType.SQL:
                return "Direct SQL query routed to PostgreSQL"
            else:
                return f"Low confidence ({confidence:.2f}) semantic query, using PostgreSQL"
                
        elif route == RouteDecision.CONCEPTS:
            return f"High confidence ({confidence:.2f}) semantic query routed to Concept Layer"
            
        else:  # BOTH
            if query_type == QueryType.HYBRID:
                return "Hybrid query checking both PostgreSQL and Concept Layer"
            else:
                return f"Medium confidence ({confidence:.2f}) query, checking both layers"
                
    async def _fallback_to_postgres(
        self, 
        query: str, 
        error: str
    ) -> Dict[str, Any]:
        """
        Fallback to PostgreSQL when routing fails
        """
        try:
            results = await self.pg_storage.execute_query(query)
            return {
                'route': 'postgres_fallback',
                'query_type': 'unknown',
                'results': results,
                'confidence': 0.0,
                'explanation': f'Routing failed ({error}), used PostgreSQL fallback'
            }
        except:
            return {
                'route': 'failed',
                'query_type': 'unknown',
                'results': [],
                'confidence': 0.0,
                'explanation': f'Query failed: {error}'
            }
            
    async def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about query routing for monitoring evolution
        """
        metrics = await self.pg_storage.get_evolution_metrics()
        
        return {
            'current_phase': metrics.get('current_phase', 1),
            'conceptualization_ratio': metrics.get('conceptualization_ratio', 0.1),
            'total_queries': metrics.get('total_queries', 0),
            'postgres_queries': metrics.get('sql_queries', 0),
            'concept_queries': metrics.get('concept_queries', 0),
            'hybrid_queries': metrics.get('hybrid_queries', 0),
            'concept_percentage': metrics.get('concept_percentage', 0),
            'evolution_ready': metrics.get('concept_percentage', 0) >= 25
        }