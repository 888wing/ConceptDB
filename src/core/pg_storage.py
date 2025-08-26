"""
PostgreSQL Storage Layer
Handles 90% of data operations in Phase 1
"""

import asyncio
from typing import Dict, List, Any, Optional
import asyncpg
from asyncpg import Pool
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PostgreSQLStorage:
    """PostgreSQL storage backend for ConceptDB Phase 1"""
    
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.pool: Optional[Pool] = None
        
    async def connect(self) -> None:
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("PostgreSQL connection pool created")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
            
    async def disconnect(self) -> None:
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")
            
    async def execute_query(self, query: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results"""
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as connection:
            try:
                # Execute query
                if params:
                    rows = await connection.fetch(query, *params)
                else:
                    rows = await connection.fetch(query)
                
                # Convert to list of dicts
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise
                
    async def execute_command(self, command: str, params: Optional[List] = None) -> str:
        """Execute a SQL command (INSERT, UPDATE, DELETE)"""
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as connection:
            try:
                if params:
                    result = await connection.execute(command, *params)
                else:
                    result = await connection.execute(command)
                return result
            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                raise
                
    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a table"""
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
        """
        return await self.execute_query(query, [table_name])
        
    async def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """Analyze query complexity for routing decision"""
        # Use EXPLAIN to analyze query
        explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE FALSE) {query}"
        
        try:
            async with self.pool.acquire() as connection:
                result = await connection.fetch(explain_query)
                plan = result[0]['QUERY PLAN'][0]
                
                # Extract complexity metrics
                return {
                    'total_cost': plan.get('Total Cost', 0),
                    'plan_rows': plan.get('Plan Rows', 0),
                    'plan_width': plan.get('Plan Width', 0),
                    'node_type': plan.get('Node Type', 'Unknown'),
                    'complexity_score': self._calculate_complexity_score(plan)
                }
        except Exception as e:
            logger.warning(f"Could not analyze query complexity: {e}")
            return {'complexity_score': 0.5}
            
    def _calculate_complexity_score(self, plan: Dict) -> float:
        """Calculate a complexity score from query plan"""
        # Simple heuristic based on query plan
        total_cost = plan.get('Total Cost', 0)
        
        # Normalize cost to 0-1 range
        if total_cost < 100:
            return 0.1
        elif total_cost < 1000:
            return 0.3
        elif total_cost < 10000:
            return 0.5
        elif total_cost < 100000:
            return 0.7
        else:
            return 0.9
            
    async def track_query_routing(
        self,
        query_text: str,
        query_type: str,
        routing_decision: str,
        confidence_score: float,
        execution_time_ms: int,
        result_count: int
    ) -> None:
        """Track query routing decision in database"""
        command = """
        SELECT conceptdb.track_query($1, $2, $3, $4, $5, $6)
        """
        await self.execute_command(
            command,
            [query_text, query_type, routing_decision, confidence_score, execution_time_ms, result_count]
        )
        
    async def get_evolution_metrics(self) -> Dict[str, Any]:
        """Get current evolution metrics"""
        query = """
        SELECT 
            current_phase,
            conceptualization_ratio,
            total_queries,
            sql_queries,
            concept_queries,
            hybrid_queries,
            CASE 
                WHEN total_queries > 0 
                THEN ROUND(concept_queries::numeric / total_queries * 100, 2)
                ELSE 0
            END as concept_percentage,
            updated_at
        FROM conceptdb.evolution_metrics
        WHERE id = 1
        """
        result = await self.execute_query(query)
        return result[0] if result else {
            'current_phase': 1,
            'conceptualization_ratio': 0.1,
            'total_queries': 0,
            'sql_queries': 0,
            'concept_queries': 0,
            'hybrid_queries': 0,
            'concept_percentage': 0
        }
        
    async def update_concept_mapping(
        self,
        table_name: str,
        column_name: str,
        concept_id: str,
        confidence: float
    ) -> None:
        """Update concept mapping for a table column"""
        command = """
        INSERT INTO conceptdb.concept_mappings 
        (table_name, column_name, concept_id, confidence)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (table_name, column_name, concept_id) 
        DO UPDATE SET confidence = $4, updated_at = CURRENT_TIMESTAMP
        """
        await self.execute_command(command, [table_name, column_name, concept_id, confidence])
        
    async def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from a table for concept extraction"""
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        return await self.execute_query(query)
        
    async def health_check(self) -> bool:
        """Check PostgreSQL connection health"""
        try:
            result = await self.execute_query("SELECT 1")
            return len(result) == 1
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False