#!/bin/bash

# ConceptDB Phase 1 API Demo Script
# Demonstrates 10% Concept + 90% PostgreSQL hybrid functionality

API_URL="http://localhost:8002"

echo "🚀 ConceptDB Phase 1 API Demo"
echo "=============================="
echo ""

# 1. Check health
echo "1️⃣ Checking API Health..."
curl -s "$API_URL/api/v1/metrics/evolution" | python3 -m json.tool | head -15
echo ""

# 2. SQL Query (90% PostgreSQL)
echo "2️⃣ Testing SQL Query (PostgreSQL Layer)..."
curl -s -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT name, price FROM products WHERE category = '\''Electronics'\'' LIMIT 3"}' \
  | python3 -m json.tool | head -20
echo ""

# 3. Create Concept (10% Semantic Layer)
echo "3️⃣ Creating New Concept..."
curl -s -X POST "$API_URL/api/v1/concepts" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smart Home Devices",
    "description": "Internet-connected devices for home automation and control",
    "metadata": {"category": "technology", "trend": "growing"}
  }' | python3 -m json.tool | head -15
echo ""

# 4. Semantic Search
echo "4️⃣ Testing Semantic Search (Concept Layer)..."
curl -s -X POST "$API_URL/api/v1/concepts/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "home automation IoT devices",
    "limit": 3
  }' | python3 -m json.tool | head -25
echo ""

# 5. Extract Concepts from Text
echo "5️⃣ Extracting Concepts from Text..."
curl -s -X POST "$API_URL/api/v1/concepts/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Our e-commerce platform uses machine learning for personalized product recommendations. The system analyzes customer behavior to suggest similar items.",
    "min_confidence": 0.6
  }' | python3 -m json.tool
echo ""

# 6. Hybrid Query (Natural Language)
echo "6️⃣ Testing Natural Language Query..."
curl -s -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "show me all electronics products"}' \
  | python3 -m json.tool | head -20
echo ""

# 7. Evolution Metrics
echo "7️⃣ Checking Evolution Progress..."
curl -s "$API_URL/api/v1/metrics/evolution" | python3 -m json.tool
echo ""

echo "✅ Demo Complete!"
echo ""
echo "Key Insights:"
echo "- PostgreSQL handles precise queries (90%)"
echo "- Concept layer enables semantic search (10%)"
echo "- Gradual evolution from SQL to concepts"
echo "- Natural language queries work alongside SQL"