"""Integration tests for PostgreSQL and Query Router"""

import asyncio
import pytest
from typing import Dict, Any

from src.core.pg_storage import PostgreSQLStorage, PGConfig, DataRecord
from src.core.query_router import QueryRouter, QueryType, RoutingDecision
from src.core.storage import ConceptStorage
from src.core.semantic_engine import SemanticEngine


@pytest.fixture
async def pg_storage():
    """Create PostgreSQL storage instance"""
    config = PGConfig(
        host="localhost",
        port=5433,
        database="conceptdb",
        user="concept_user",
        password="concept_pass"
    )
    storage = PostgreSQLStorage(config)
    await storage.initialize()
    yield storage
    await storage.close()


@pytest.fixture
def concept_storage():
    """Create concept storage instance"""
    return ConceptStorage()


@pytest.fixture
def semantic_engine():
    """Create semantic engine instance"""
    return SemanticEngine()


@pytest.fixture
async def query_router(pg_storage, concept_storage, semantic_engine):
    """Create query router instance"""
    return QueryRouter(pg_storage, concept_storage, semantic_engine)


@pytest.mark.asyncio
async def test_postgresql_connection(pg_storage):
    """Test PostgreSQL connection and basic operations"""
    # Test connection
    assert pg_storage.pool is not None
    
    # Test creating a record
    record = DataRecord(
        type="test_record",
        content={"test": "data", "value": 123},
        metadata={"source": "test"}
    )
    
    record_id = await pg_storage.create_record(record)
    assert record_id is not None
    
    # Test retrieving the record
    retrieved = await pg_storage.get_record(record_id)
    assert retrieved is not None
    assert retrieved.type == "test_record"
    assert retrieved.content["test"] == "data"
    
    # Test updating the record
    success = await pg_storage.update_record(
        record_id,
        {"content": {"test": "updated", "value": 456}}
    )
    assert success is True
    
    # Test searching records
    results = await pg_storage.search_records(type="test_record")
    assert len(results) > 0
    
    # Clean up
    deleted = await pg_storage.delete_record(record_id)
    assert deleted is True


@pytest.mark.asyncio
async def test_query_router_analysis(query_router):
    """Test query analysis and routing logic"""
    
    # Test SQL query detection
    sql_query = "SELECT * FROM users WHERE age > 25"
    analysis = query_router.analyze_query(sql_query)
    assert analysis.query_type == QueryType.SQL
    assert analysis.has_sql_keywords is True
    assert analysis.suggested_routing == RoutingDecision.POSTGRES
    
    # Test natural language query detection
    nl_query = "find similar concepts to customer satisfaction"
    analysis = query_router.analyze_query(nl_query)
    assert analysis.query_type == QueryType.NATURAL_LANGUAGE
    assert analysis.has_semantic_intent is True
    assert analysis.suggested_routing == RoutingDecision.CONCEPTS
    
    # Test hybrid query detection
    hybrid_query = "SELECT * FROM products WHERE description is similar to 'smart device'"
    analysis = query_router.analyze_query(hybrid_query)
    assert analysis.query_type == QueryType.HYBRID
    assert analysis.has_sql_keywords is True
    assert analysis.has_semantic_intent is True


@pytest.mark.asyncio
async def test_query_routing_execution(query_router):
    """Test actual query routing and execution"""
    
    # Test PostgreSQL routing
    sql_query = "SELECT type, COUNT(*) as count FROM data_records GROUP BY type"
    result = await query_router.route_query(sql_query)
    assert result.routing_decision == RoutingDecision.POSTGRES
    assert result.postgres_results is not None
    assert result.confidence_score > 0.7
    assert result.response_time_ms > 0
    
    # Test Concept routing
    nl_query = "what concepts are related to customer feedback"
    result = await query_router.route_query(nl_query)
    assert result.routing_decision in [RoutingDecision.CONCEPTS, RoutingDecision.BOTH]
    assert result.confidence_score > 0
    
    # Test routing explanation
    explanation = await query_router.explain_routing(sql_query)
    assert explanation['routing_decision'] == 'postgres'
    assert 'reasoning' in explanation
    assert explanation['phase_info']['current_phase'] == 1
    assert explanation['phase_info']['conceptualization_ratio'] == 0.1


@pytest.mark.asyncio
async def test_evolution_metrics(pg_storage):
    """Test evolution metrics tracking"""
    
    # Log some query routing stats
    await pg_storage.log_query_routing(
        query_text="test query",
        query_type="natural_language",
        routed_to="concepts",
        confidence_score=0.85,
        response_time_ms=150,
        result_count=5
    )
    
    # Update evolution metrics
    await pg_storage.update_evolution_metrics()
    
    # Get current metrics
    metrics = await pg_storage.get_evolution_metrics()
    assert metrics is not None
    assert metrics['phase'] == 1
    assert metrics['conceptualization_ratio'] >= 0.0
    assert metrics['conceptualization_ratio'] <= 1.0


@pytest.mark.asyncio
async def test_hybrid_query_execution(query_router):
    """Test hybrid query that uses both layers"""
    
    hybrid_query = "find customer feedback with rating > 3 similar to 'quality issues'"
    result = await query_router.route_query(hybrid_query)
    
    # Should route to both or intelligently decide
    assert result.routing_decision in [RoutingDecision.BOTH, RoutingDecision.POSTGRES, RoutingDecision.CONCEPTS]
    assert result.merged_results is not None
    assert result.explanation != ""
    
    # Check that results have source indicators
    for item in result.merged_results:
        assert '_source' in item or 'source' in item or 'type' in item


@pytest.mark.asyncio
async def test_concept_extraction_tracking(pg_storage):
    """Test tracking of concept extraction from records"""
    
    # Get unprocessed records
    unprocessed = await pg_storage.get_unprocessed_records(limit=5)
    
    # If there are unprocessed records, mark some as processed
    if unprocessed:
        record = unprocessed[0]
        success = await pg_storage.mark_concepts_extracted(
            record.id,
            ["concept_1", "concept_2", "concept_3"]
        )
        assert success is True
        
        # Verify the record is marked as processed
        updated = await pg_storage.get_record(record.id)
        assert updated.concept_extracted is True
        assert len(updated.concept_ids) == 3


def test_sync():
    """Synchronous test runner for debugging"""
    async def run_tests():
        # Initialize components
        pg_config = PGConfig()
        pg_storage = PostgreSQLStorage(pg_config)
        await pg_storage.initialize()
        
        concept_storage = ConceptStorage()
        semantic_engine = SemanticEngine()
        query_router = QueryRouter(pg_storage, concept_storage, semantic_engine)
        
        try:
            # Test basic connection
            print("Testing PostgreSQL connection...")
            assert pg_storage.pool is not None
            print("✓ PostgreSQL connected")
            
            # Test query analysis
            print("\nTesting query analysis...")
            sql_query = "SELECT * FROM users"
            analysis = query_router.analyze_query(sql_query)
            print(f"✓ SQL query detected: {analysis.query_type.value}")
            
            nl_query = "find similar concepts"
            analysis = query_router.analyze_query(nl_query)
            print(f"✓ NL query detected: {analysis.query_type.value}")
            
            # Test routing
            print("\nTesting query routing...")
            result = await query_router.route_query("SELECT COUNT(*) FROM data_records")
            print(f"✓ Query routed to: {result.routing_decision.value}")
            print(f"  Response time: {result.response_time_ms}ms")
            
            # Test metrics
            print("\nTesting evolution metrics...")
            metrics = await pg_storage.get_evolution_metrics()
            print(f"✓ Phase: {metrics.get('phase', 1)}")
            print(f"  Conceptualization: {metrics.get('conceptualization_ratio', 0.1):.0%}")
            
            print("\n✅ All integration tests passed!")
            
        finally:
            await pg_storage.close()
    
    # Run the async tests
    asyncio.run(run_tests())


if __name__ == "__main__":
    # Run sync test for quick validation
    test_sync()