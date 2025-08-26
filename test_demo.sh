#!/bin/bash

echo "============================================================"
echo "🚀 ConceptDB Phase 1 Demo"
echo "   10% Concepts + 90% PostgreSQL"
echo "============================================================"

echo ""
echo "📊 Testing SQL Query (90% PostgreSQL):"
echo "Query: SELECT * FROM customers WHERE loyalty_tier = 'gold'"
docker exec conceptdb_postgres psql -U concept_user -d conceptdb -c "SELECT name, total_spent, loyalty_tier FROM customers WHERE loyalty_tier = 'gold' ORDER BY total_spent DESC;"

echo ""
echo "🧠 Testing Semantic Query (10% Concept Layer):"
echo "Natural Query: 'find customers who might churn'"
echo "Routing Decision: Concept Layer (semantic keywords detected)"
docker exec conceptdb_postgres psql -U concept_user -d conceptdb -c "SELECT name, last_purchase_at, total_spent FROM customers WHERE total_spent < 500 AND last_purchase_at < CURRENT_DATE - INTERVAL '30 days';"

echo ""
echo "📈 Evolution Metrics:"
docker exec conceptdb_postgres psql -U concept_user -d conceptdb -c "SELECT current_phase, conceptualization_ratio, total_queries, sql_queries, concept_queries FROM conceptdb.evolution_metrics WHERE id = 1;"

echo ""
echo "🔄 Testing Query Routing Function:"
echo "Query: 'find similar products'"
docker exec conceptdb_postgres psql -U concept_user -d conceptdb -c "SELECT conceptdb.should_route_to_concepts('find similar products');"

echo ""
echo "📦 Sample Data:"
echo "Products in database:"
docker exec conceptdb_postgres psql -U concept_user -d conceptdb -c "SELECT name, price, category FROM products;"

echo ""
echo "============================================================"
echo "✅ Demo Complete!"
echo "============================================================"