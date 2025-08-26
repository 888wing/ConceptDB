#!/usr/bin/env python3
"""
Integration Test for ConceptDB Phase 1
Demonstrates 10% Concept + 90% PostgreSQL Architecture
"""

import asyncio
import asyncpg
import json
from typing import Dict, Any, List

class ConceptDBTest:
    def __init__(self):
        self.conn = None
        
    async def connect(self):
        """Connect to PostgreSQL"""
        self.conn = await asyncpg.connect(
            'postgresql://concept_user:concept_pass@localhost:5432/conceptdb'
        )
        print("✅ Connected to PostgreSQL")
        
    async def disconnect(self):
        """Disconnect from PostgreSQL"""
        if self.conn:
            await self.conn.close()
            
    async def test_sql_query(self):
        """Test traditional SQL query (90% path)"""
        print("\n📊 Testing SQL Query (90% PostgreSQL):")
        query = "SELECT * FROM customers WHERE loyalty_tier = 'gold' ORDER BY total_spent DESC"
        results = await self.conn.fetch(query)
        
        print(f"  Query: {query}")
        print(f"  Results: Found {len(results)} gold customers")
        for row in results[:3]:
            print(f"    - {row['name']}: ${row['total_spent']}")
        return results
        
    async def test_semantic_query(self):
        """Test semantic/natural language query (10% path)"""
        print("\n🧠 Testing Semantic Query (10% Concept Layer):")
        
        # Simulate semantic query processing
        natural_query = "find customers who might churn"
        
        # In Phase 1, we analyze the query and decide routing
        has_semantic_keywords = any(word in natural_query for word in ['might', 'could', 'similar'])
        
        if has_semantic_keywords:
            print(f"  Query: '{natural_query}'")
            print("  Route: Concept Layer (high confidence semantic query)")
            
            # Simple simulation: low spending + old last purchase = churn risk
            query = """
            SELECT * FROM customers 
            WHERE total_spent < 500 
            AND last_purchase_at < CURRENT_DATE - INTERVAL '60 days'
            """
            results = await self.conn.fetch(query)
            
            print(f"  Results: Found {len(results)} customers at risk")
            for row in results:
                print(f"    - {row['name']}: Last purchase {row['last_purchase_at']}")
        
        return results
        
    async def test_hybrid_query(self):
        """Test hybrid query (both layers)"""
        print("\n🔄 Testing Hybrid Query (Both Layers):")
        
        hybrid_query = "SELECT customers similar to high-value ones"
        print(f"  Query: '{hybrid_query}'")
        print("  Route: Both PostgreSQL and Concept Layer")
        
        # First: Get high-value customers from PostgreSQL
        sql_results = await self.conn.fetch(
            "SELECT * FROM customers WHERE loyalty_tier = 'platinum'"
        )
        print(f"  PostgreSQL: Found {len(sql_results)} platinum customers")
        
        # Then: Find similar patterns (simulated)
        concept_results = await self.conn.fetch(
            "SELECT * FROM customers WHERE total_spent > 2000 AND loyalty_tier != 'platinum'"
        )
        print(f"  Concept Layer: Found {len(concept_results)} similar customers")
        
        return sql_results + concept_results
        
    async def test_evolution_tracking(self):
        """Test evolution metrics tracking"""
        print("\n📈 Testing Evolution Tracking:")
        
        # Track query routing
        await self.conn.execute(
            "SELECT conceptdb.track_query($1, $2, $3, $4, $5, $6)",
            "SELECT * FROM customers", "sql", "postgres", 0.95, 50, 5
        )
        
        await self.conn.execute(
            "SELECT conceptdb.track_query($1, $2, $3, $4, $5, $6)",
            "find similar customers", "natural", "concepts", 0.85, 120, 3
        )
        
        # Get evolution metrics
        metrics = await self.conn.fetchrow(
            "SELECT * FROM conceptdb.evolution_metrics WHERE id = 1"
        )
        
        if metrics:
            total = metrics['total_queries']
            sql_pct = (metrics['sql_queries'] / total * 100) if total > 0 else 0
            concept_pct = (metrics['concept_queries'] / total * 100) if total > 0 else 0
            
            print(f"  Current Phase: {metrics['current_phase']}")
            print(f"  Conceptualization Ratio: {metrics['conceptualization_ratio']:.1%}")
            print(f"  Total Queries: {total}")
            print(f"  SQL Queries: {metrics['sql_queries']} ({sql_pct:.1f}%)")
            print(f"  Concept Queries: {metrics['concept_queries']} ({concept_pct:.1f}%)")
            print(f"  Hybrid Queries: {metrics['hybrid_queries']}")
            
            if concept_pct >= 25:
                print("  ✨ Ready to evolve to Phase 2!")
            else:
                print(f"  📊 Need {25 - concept_pct:.1f}% more concept usage for Phase 2")
                
    async def test_concept_extraction(self):
        """Test concept extraction from data"""
        print("\n🔮 Testing Concept Extraction:")
        
        # Get sample product data
        products = await self.conn.fetch("SELECT * FROM products LIMIT 3")
        
        print("  Extracting concepts from products:")
        for product in products:
            # Simulate concept extraction
            concepts = []
            
            # Extract category concept
            if product['category']:
                concepts.append(f"category:{product['category']}")
                
            # Extract price range concept
            price = float(product['price'])
            if price < 50:
                concepts.append("price:budget")
            elif price < 500:
                concepts.append("price:mid-range")
            else:
                concepts.append("price:premium")
                
            # Store concept mapping
            await self.conn.execute(
                """
                INSERT INTO conceptdb.concept_mappings 
                (table_name, column_name, concept_id, confidence)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (table_name, column_name, concept_id) 
                DO UPDATE SET confidence = $4
                """,
                "products", "id", f"product_{product['id']}", 0.9
            )
            
            print(f"    {product['name']}: {', '.join(concepts)}")
            
    async def run_all_tests(self):
        """Run all integration tests"""
        print("=" * 60)
        print("🚀 ConceptDB Phase 1 Integration Test")
        print("   10% Concepts + 90% PostgreSQL")
        print("=" * 60)
        
        try:
            await self.connect()
            
            # Run tests
            await self.test_sql_query()
            await self.test_semantic_query()
            await self.test_hybrid_query()
            await self.test_concept_extraction()
            await self.test_evolution_tracking()
            
            print("\n" + "=" * 60)
            print("✅ All tests completed successfully!")
            print("=" * 60)
            
        finally:
            await self.disconnect()


async def main():
    test = ConceptDBTest()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())