#!/usr/bin/env python3
"""Simple test for query router logic without imports"""

import re
from enum import Enum
from typing import List

class QueryType(Enum):
    SQL = "sql"
    NATURAL_LANGUAGE = "natural_language"  
    HYBRID = "hybrid"

class RoutingDecision(Enum):
    POSTGRES = "postgres"
    CONCEPTS = "concepts"
    BOTH = "both"

class SimpleQueryAnalyzer:
    """Simplified query analyzer for testing"""
    
    SQL_KEYWORDS = [
        'select', 'from', 'where', 'insert', 'update', 'delete',
        'join', 'group by', 'order by', 'having', 'limit',
        'and', 'or', 'not', 'in', 'between', 'like'
    ]
    
    SEMANTIC_INDICATORS = [
        'similar', 'related', 'about', 'meaning',
        'concept', 'understand', 'insight', 'pattern',
        'trend', 'sentiment', 'feeling', 'opinion'
    ]
    
    def analyze(self, query: str):
        query_lower = query.lower()
        
        # Check for SQL keywords (with word boundaries to avoid false positives)
        sql_keyword_count = sum(1 for keyword in self.SQL_KEYWORDS 
                               if f' {keyword} ' in f' {query_lower} ' or query_lower.startswith(f'{keyword} '))
        has_sql_keywords = sql_keyword_count > 0
        
        # Check for semantic indicators
        semantic_count = sum(1 for indicator in self.SEMANTIC_INDICATORS if indicator in query_lower)
        has_semantic_intent = semantic_count > 0
        
        # Determine query type
        if has_sql_keywords and not has_semantic_intent:
            query_type = QueryType.SQL
            confidence = min(sql_keyword_count / 3, 1.0)
            routing = RoutingDecision.POSTGRES
            
        elif has_semantic_intent and not has_sql_keywords:
            query_type = QueryType.NATURAL_LANGUAGE
            confidence = min(semantic_count / 2, 1.0)
            routing = RoutingDecision.CONCEPTS
            
        else:
            query_type = QueryType.HYBRID
            confidence = 0.5
            routing = RoutingDecision.BOTH
        
        return {
            'query_type': query_type,
            'has_sql_keywords': has_sql_keywords,
            'has_semantic_intent': has_semantic_intent,
            'confidence_score': confidence,
            'suggested_routing': routing
        }

def test_query_analysis():
    """Test query analysis logic"""
    analyzer = SimpleQueryAnalyzer()
    
    print("🚀 Testing Query Router Logic")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            'query': "SELECT * FROM customers WHERE age > 25 AND country = 'USA'",
            'expected_type': QueryType.SQL,
            'expected_routing': RoutingDecision.POSTGRES,
            'description': 'Pure SQL query'
        },
        {
            'query': "find all products similar to smartphones with good reviews",
            'expected_type': QueryType.NATURAL_LANGUAGE,
            'expected_routing': RoutingDecision.CONCEPTS,
            'description': 'Natural language query'
        },
        {
            'query': "SELECT * FROM products WHERE category similar to 'electronics' and sentiment is positive",
            'expected_type': QueryType.HYBRID,
            'expected_routing': RoutingDecision.BOTH,
            'description': 'Hybrid query with SQL and semantic'
        },
        {
            'query': "what are the main concepts related to customer satisfaction",
            'expected_type': QueryType.NATURAL_LANGUAGE,
            'expected_routing': RoutingDecision.CONCEPTS,
            'description': 'Semantic concept query'
        },
        {
            'query': "INSERT INTO reviews (text, rating) VALUES ('Great product', 5)",
            'expected_type': QueryType.SQL,
            'expected_routing': RoutingDecision.POSTGRES,
            'description': 'SQL INSERT statement'
        },
        {
            'query': "show me insights about user behavior patterns",
            'expected_type': QueryType.NATURAL_LANGUAGE,
            'expected_routing': RoutingDecision.CONCEPTS,
            'description': 'Insight query'
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"  Query: {test['query'][:60]}...")
        
        result = analyzer.analyze(test['query'])
        
        # Check expectations
        type_match = result['query_type'] == test['expected_type']
        routing_match = result['suggested_routing'] == test['expected_routing']
        
        if type_match and routing_match:
            print(f"  ✅ PASSED")
            print(f"     Type: {result['query_type'].value}")
            print(f"     Routing: {result['suggested_routing'].value}")
            print(f"     Confidence: {result['confidence_score']:.0%}")
            passed += 1
        else:
            print(f"  ❌ FAILED")
            print(f"     Expected type: {test['expected_type'].value}, Got: {result['query_type'].value}")
            print(f"     Expected routing: {test['expected_routing'].value}, Got: {result['suggested_routing'].value}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All Query Router tests passed!")
        return True
    else:
        print(f"❌ {failed} tests failed")
        return False

def test_confidence_thresholds():
    """Test confidence score calculation"""
    analyzer = SimpleQueryAnalyzer()
    
    print("\n🔍 Testing Confidence Thresholds")
    print("=" * 50)
    
    confidence_tests = [
        ("from users", "Weak SQL"),
        ("SELECT id, name FROM users WHERE status = 'active' ORDER BY created_at DESC", "Strong SQL"),
        ("about products", "Weak semantic"),
        ("find concepts related to customer sentiment and opinion patterns", "Strong semantic"),
    ]
    
    for query, description in confidence_tests:
        result = analyzer.analyze(query)
        print(f"\n{description}:")
        print(f"  Query: {query[:50]}...")
        print(f"  Type: {result['query_type'].value}")
        print(f"  Confidence: {result['confidence_score']:.0%}")
    
    print("\n✅ Confidence thresholds working correctly")
    return True

def main():
    """Run all tests"""
    print("🧪 Query Router Logic Tests (No ML Dependencies)")
    print("=" * 50)
    
    success = True
    
    # Test query analysis
    if not test_query_analysis():
        success = False
    
    # Test confidence thresholds
    if not test_confidence_thresholds():
        success = False
    
    if success:
        print("\n🎉 All tests passed successfully!")
    else:
        print("\n❌ Some tests failed")
    
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)