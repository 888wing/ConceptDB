"""Basic integration tests without ML dependencies"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_postgresql_connection():
    """Test basic PostgreSQL connection"""
    from src.core.pg_storage import PostgreSQLStorage, PGConfig, DataRecord
    
    print("🔍 Testing PostgreSQL connection...")
    
    config = PGConfig(
        host="localhost",
        port=5433,
        database="conceptdb",
        user="concept_user",
        password="concept_pass"
    )
    
    storage = PostgreSQLStorage(config)
    
    # Test connection
    success = await storage.initialize()
    assert success, "Failed to initialize PostgreSQL"
    print("✅ PostgreSQL connection successful")
    
    # Test creating a record
    record = DataRecord(
        type="test_record",
        content={"test": "data", "value": 123},
        metadata={"source": "test"}
    )
    
    record_id = await storage.create_record(record)
    assert record_id is not None, "Failed to create record"
    print(f"✅ Created record: {record_id}")
    
    # Test retrieving the record
    retrieved = await storage.get_record(record_id)
    assert retrieved is not None, "Failed to retrieve record"
    assert retrieved.type == "test_record", "Record type mismatch"
    assert retrieved.content["test"] == "data", "Content mismatch"
    print(f"✅ Retrieved record successfully")
    
    # Test searching records
    results = await storage.search_records(type="test_record")
    assert len(results) > 0, "Search returned no results"
    print(f"✅ Search found {len(results)} records")
    
    # Test evolution metrics
    metrics = await storage.get_evolution_metrics()
    assert metrics is not None, "Failed to get evolution metrics"
    assert metrics.get('phase') == 1, "Wrong phase"
    assert 0.0 <= metrics.get('conceptualization_ratio', 0.1) <= 1.0, "Invalid ratio"
    print(f"✅ Evolution metrics: Phase {metrics.get('phase')}, Ratio: {metrics.get('conceptualization_ratio', 0.1):.0%}")
    
    # Clean up
    deleted = await storage.delete_record(record_id)
    assert deleted, "Failed to delete record"
    print(f"✅ Deleted test record")
    
    await storage.close()
    print("✅ All PostgreSQL tests passed!")
    return True

async def test_query_router_basic():
    """Test query router without semantic engine"""
    from src.core.pg_storage import PostgreSQLStorage, PGConfig
    from src.core.query_router import QueryRouter, QueryType, RoutingDecision
    
    print("\n🔍 Testing Query Router...")
    
    # Initialize PostgreSQL storage
    config = PGConfig(
        host="localhost",
        port=5433,
        database="conceptdb",
        user="concept_user",
        password="concept_pass"
    )
    
    pg_storage = PostgreSQLStorage(config)
    await pg_storage.initialize()
    
    # Create query router (will use None for concept_storage and semantic_engine)
    query_router = QueryRouter(pg_storage, None, None)
    
    # Test SQL query detection
    sql_query = "SELECT * FROM users WHERE age > 25"
    analysis = query_router.analyze_query(sql_query)
    assert analysis.query_type == QueryType.SQL, "Failed to detect SQL query"
    assert analysis.has_sql_keywords is True, "Failed to detect SQL keywords"
    assert analysis.suggested_routing == RoutingDecision.POSTGRES, "Wrong routing decision"
    print(f"✅ SQL query detected: {analysis.query_type.value}")
    
    # Test natural language query detection
    nl_query = "find similar concepts to customer satisfaction"
    analysis = query_router.analyze_query(nl_query)
    assert analysis.query_type == QueryType.NATURAL_LANGUAGE, "Failed to detect NL query"
    assert analysis.has_semantic_intent is True, "Failed to detect semantic intent"
    assert analysis.suggested_routing == RoutingDecision.CONCEPTS, "Wrong routing decision"
    print(f"✅ NL query detected: {analysis.query_type.value}")
    
    # Test hybrid query detection
    hybrid_query = "SELECT * FROM products WHERE description is similar to 'smart device'"
    analysis = query_router.analyze_query(hybrid_query)
    assert analysis.query_type == QueryType.HYBRID, "Failed to detect hybrid query"
    assert analysis.has_sql_keywords is True, "Failed to detect SQL in hybrid"
    assert analysis.has_semantic_intent is True, "Failed to detect semantic in hybrid"
    print(f"✅ Hybrid query detected: {analysis.query_type.value}")
    
    # Test routing explanation
    explanation = await query_router.explain_routing(sql_query)
    assert explanation['routing_decision'] == 'postgres', "Wrong routing in explanation"
    assert 'reasoning' in explanation, "Missing reasoning in explanation"
    assert explanation['phase_info']['current_phase'] == 1, "Wrong phase"
    assert explanation['phase_info']['conceptualization_ratio'] == 0.1, "Wrong ratio"
    print(f"✅ Routing explanation generated")
    
    await pg_storage.close()
    print("✅ All Query Router tests passed!")
    return True

async def main():
    """Run all basic tests"""
    print("🚀 Running Basic Integration Tests")
    print("=" * 50)
    
    try:
        # Test PostgreSQL
        await test_postgresql_connection()
        
        # Test Query Router
        await test_query_router_basic()
        
        print("\n" + "=" * 50)
        print("🎉 All basic tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)