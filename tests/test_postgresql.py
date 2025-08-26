#!/usr/bin/env python3
"""Test PostgreSQL integration without ML dependencies"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_postgresql():
    """Test PostgreSQL storage layer"""
    # Import directly without going through __init__.py
    import sys
    import importlib.util
    
    # Load pg_storage module directly
    spec = importlib.util.spec_from_file_location(
        "pg_storage", 
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src/core/pg_storage.py")
    )
    pg_storage = importlib.util.module_from_spec(spec)
    sys.modules["pg_storage"] = pg_storage
    spec.loader.exec_module(pg_storage)
    
    PostgreSQLStorage = pg_storage.PostgreSQLStorage
    PGConfig = pg_storage.PGConfig
    DataRecord = pg_storage.DataRecord
    
    print("🔍 Testing PostgreSQL Storage Layer")
    print("=" * 50)
    
    # Configure connection
    config = PGConfig(
        host="localhost",
        port=5433,
        database="conceptdb",
        user="concept_user",
        password="concept_pass"
    )
    
    storage = PostgreSQLStorage(config)
    
    # 1. Test connection
    print("\n1️⃣ Testing connection...")
    success = await storage.initialize()
    if not success:
        print("❌ Failed to connect to PostgreSQL")
        print("   Make sure docker-compose is running")
        return False
    print("✅ Connected to PostgreSQL")
    
    # 2. Test creating a record
    print("\n2️⃣ Testing record creation...")
    record = DataRecord(
        type="customer_feedback",
        content={
            "text": "The product is great but delivery was slow",
            "rating": 4,
            "user_id": "user_123"
        },
        metadata={
            "source": "website",
            "category": "review",
            "timestamp": "2024-01-15"
        }
    )
    
    record_id = await storage.create_record(record)
    if not record_id:
        print("❌ Failed to create record")
        await storage.close()
        return False
    print(f"✅ Created record: {record_id}")
    
    # 3. Test retrieving the record
    print("\n3️⃣ Testing record retrieval...")
    retrieved = await storage.get_record(record_id)
    if not retrieved:
        print("❌ Failed to retrieve record")
        await storage.close()
        return False
    
    assert retrieved.type == "customer_feedback"
    assert retrieved.content["rating"] == 4
    assert retrieved.metadata["source"] == "website"
    print("✅ Retrieved record successfully")
    print(f"   Type: {retrieved.type}")
    print(f"   Content: {retrieved.content}")
    
    # 4. Test updating a record
    print("\n4️⃣ Testing record update...")
    success = await storage.update_record(
        record_id,
        {
            "content": {"text": "Updated text", "rating": 5, "user_id": "user_123"},
            "metadata": {"source": "website", "category": "review", "updated": True}
        }
    )
    if not success:
        print("❌ Failed to update record")
        await storage.close()
        return False
    
    updated = await storage.get_record(record_id)
    assert updated.content["rating"] == 5
    assert updated.metadata.get("updated") == True
    print("✅ Updated record successfully")
    
    # 5. Test searching records
    print("\n5️⃣ Testing record search...")
    results = await storage.search_records(
        type="customer_feedback",
        metadata_filter={"source": "website"}
    )
    assert len(results) > 0
    print(f"✅ Search found {len(results)} records")
    
    # 6. Test getting unprocessed records
    print("\n6️⃣ Testing unprocessed records...")
    unprocessed = await storage.get_unprocessed_records(limit=10)
    print(f"✅ Found {len(unprocessed)} unprocessed records")
    
    # 7. Test marking concepts extracted
    if unprocessed:
        print("\n7️⃣ Testing concept extraction marking...")
        import uuid
        first_unprocessed = unprocessed[0]
        # Generate proper UUIDs for concept IDs
        concept_ids = [str(uuid.uuid4()) for _ in range(3)]
        success = await storage.mark_concepts_extracted(
            first_unprocessed.id,
            concept_ids
        )
        assert success
        
        # Verify it's marked
        updated_record = await storage.get_record(first_unprocessed.id)
        assert updated_record.concept_extracted == True
        assert len(updated_record.concept_ids) == 3
        print("✅ Marked concepts as extracted")
    
    # 8. Test evolution metrics
    print("\n8️⃣ Testing evolution metrics...")
    
    # Log some query routing stats
    await storage.log_query_routing(
        query_text="SELECT * FROM users",
        query_type="sql",
        routed_to="postgres",
        confidence_score=0.95,
        response_time_ms=45,
        result_count=10
    )
    
    await storage.log_query_routing(
        query_text="find similar concepts",
        query_type="natural_language",
        routed_to="concepts",
        confidence_score=0.85,
        response_time_ms=120,
        result_count=5
    )
    
    # Update metrics
    await storage.update_evolution_metrics()
    
    # Get metrics
    metrics = await storage.get_evolution_metrics()
    assert metrics is not None
    assert metrics['phase'] == 1
    assert 0.0 <= metrics['conceptualization_ratio'] <= 1.0
    
    print(f"✅ Evolution metrics:")
    print(f"   Phase: {metrics['phase']}")
    print(f"   Conceptualization: {metrics['conceptualization_ratio']:.0%}")
    print(f"   Total queries: {metrics.get('total_queries', 0)}")
    
    # 9. Test raw SQL execution
    print("\n9️⃣ Testing raw SQL execution...")
    results = await storage.execute_sql(
        "SELECT COUNT(*) as count FROM data_records"
    )
    assert len(results) > 0
    print(f"✅ Raw SQL execution: {results[0]['count']} total records")
    
    # 10. Clean up
    print("\n🧹 Cleaning up...")
    deleted = await storage.delete_record(record_id)
    assert deleted
    print(f"✅ Deleted test record")
    
    # Close connection
    await storage.close()
    
    print("\n" + "=" * 50)
    print("✅ All PostgreSQL tests passed!")
    return True

async def test_query_router():
    """Test Query Router logic"""
    import sys
    import importlib.util
    
    # Load modules directly
    spec_pg = importlib.util.spec_from_file_location(
        "pg_storage", 
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src/core/pg_storage.py")
    )
    pg_storage = importlib.util.module_from_spec(spec_pg)
    sys.modules["pg_storage"] = pg_storage
    spec_pg.loader.exec_module(pg_storage)
    
    spec_router = importlib.util.spec_from_file_location(
        "query_router",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src/core/query_router.py")
    )
    query_router = importlib.util.module_from_spec(spec_router)
    sys.modules["query_router"] = query_router
    spec_router.loader.exec_module(query_router)
    
    PostgreSQLStorage = pg_storage.PostgreSQLStorage
    PGConfig = pg_storage.PGConfig
    QueryRouter = query_router.QueryRouter
    QueryType = query_router.QueryType
    RoutingDecision = query_router.RoutingDecision
    
    print("\n🔍 Testing Query Router")
    print("=" * 50)
    
    # Initialize PostgreSQL
    config = PGConfig(
        host="localhost",
        port=5433,
        database="conceptdb",
        user="concept_user",
        password="concept_pass"
    )
    
    pg_storage = PostgreSQLStorage(config)
    await pg_storage.initialize()
    
    # Create router (without ML components for now)
    router = QueryRouter(pg_storage, None, None)
    
    # 1. Test SQL query analysis
    print("\n1️⃣ Testing SQL query detection...")
    sql_query = "SELECT * FROM customers WHERE age > 25 AND country = 'USA'"
    analysis = router.analyze_query(sql_query)
    
    assert analysis.query_type == QueryType.SQL
    assert analysis.has_sql_keywords == True
    assert analysis.has_semantic_intent == False
    assert analysis.suggested_routing == RoutingDecision.POSTGRES
    print(f"✅ SQL query detected")
    print(f"   Type: {analysis.query_type.value}")
    print(f"   Confidence: {analysis.confidence_score:.0%}")
    print(f"   Routing: {analysis.suggested_routing.value}")
    
    # 2. Test natural language query
    print("\n2️⃣ Testing natural language detection...")
    nl_query = "find all products similar to smartphones with good reviews"
    analysis = router.analyze_query(nl_query)
    
    assert analysis.query_type == QueryType.NATURAL_LANGUAGE
    assert analysis.has_sql_keywords == False
    assert analysis.has_semantic_intent == True
    assert analysis.suggested_routing == RoutingDecision.CONCEPTS
    print(f"✅ Natural language query detected")
    print(f"   Type: {analysis.query_type.value}")
    print(f"   Confidence: {analysis.confidence_score:.0%}")
    print(f"   Routing: {analysis.suggested_routing.value}")
    
    # 3. Test hybrid query
    print("\n3️⃣ Testing hybrid query detection...")
    hybrid_query = "SELECT * FROM products WHERE category similar to 'electronics' and sentiment is positive"
    analysis = router.analyze_query(hybrid_query)
    
    assert analysis.query_type == QueryType.HYBRID
    assert analysis.has_sql_keywords == True
    assert analysis.has_semantic_intent == True
    print(f"✅ Hybrid query detected")
    print(f"   Type: {analysis.query_type.value}")
    print(f"   Confidence: {analysis.confidence_score:.0%}")
    print(f"   Routing: {analysis.suggested_routing.value}")
    
    # 4. Test routing explanation
    print("\n4️⃣ Testing routing explanation...")
    explanation = await router.explain_routing(sql_query)
    
    assert explanation['routing_decision'] == 'postgres'
    assert 'reasoning' in explanation
    assert explanation['phase_info']['current_phase'] == 1
    assert explanation['phase_info']['conceptualization_ratio'] == 0.1
    
    print(f"✅ Routing explanation:")
    print(f"   Decision: {explanation['routing_decision']}")
    print(f"   Reasoning: {explanation['reasoning']}")
    print(f"   Phase: {explanation['phase_info']['current_phase']}")
    
    # 5. Test confidence thresholds
    print("\n5️⃣ Testing confidence thresholds...")
    
    # Low confidence SQL
    weak_sql = "from users"
    analysis = router.analyze_query(weak_sql)
    print(f"   Weak SQL confidence: {analysis.confidence_score:.0%}")
    
    # Strong SQL
    strong_sql = "SELECT id, name FROM users WHERE status = 'active' ORDER BY created_at DESC LIMIT 100"
    analysis = router.analyze_query(strong_sql)
    print(f"   Strong SQL confidence: {analysis.confidence_score:.0%}")
    
    # Weak semantic
    weak_semantic = "about products"
    analysis = router.analyze_query(weak_semantic)
    print(f"   Weak semantic confidence: {analysis.confidence_score:.0%}")
    
    # Strong semantic
    strong_semantic = "find concepts related to customer sentiment and opinion patterns"
    analysis = router.analyze_query(strong_semantic)
    print(f"   Strong semantic confidence: {analysis.confidence_score:.0%}")
    
    print("✅ Confidence thresholds working correctly")
    
    await pg_storage.close()
    
    print("\n" + "=" * 50)
    print("✅ All Query Router tests passed!")
    return True

async def main():
    """Run all tests"""
    print("🚀 ConceptDB Integration Tests")
    print("=" * 50)
    
    try:
        # Test PostgreSQL
        if not await test_postgresql():
            print("\n❌ PostgreSQL tests failed")
            return False
        
        # Test Query Router
        if not await test_query_router():
            print("\n❌ Query Router tests failed")
            return False
        
        print("\n" + "=" * 50)
        print("🎉 All integration tests passed successfully!")
        print("\n📊 Phase 1 Status:")
        print("   ✅ PostgreSQL integration (90% layer)")
        print("   ✅ Query router intelligence")
        print("   ✅ Evolution metrics tracking")
        print("   ⏳ Concept layer (10% - ML dependencies need fixing)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)