"""
Unit tests for Query Router
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.query_router import QueryRouter, QueryType, RouteDecision


@pytest.fixture
def mock_pg_storage():
    """Mock PostgreSQL storage"""
    storage = AsyncMock()
    storage.execute_query = AsyncMock(return_value=[])
    storage.analyze_query_complexity = AsyncMock(return_value={'complexity_score': 0.5})
    storage.track_query_routing = AsyncMock()
    storage.get_evolution_metrics = AsyncMock(return_value={
        'current_phase': 1,
        'conceptualization_ratio': 0.1,
        'total_queries': 0
    })
    return storage


@pytest.fixture
def mock_vector_store():
    """Mock vector store"""
    store = AsyncMock()
    store.search = AsyncMock(return_value=[])
    return store


@pytest.fixture
def mock_semantic_engine():
    """Mock semantic engine"""
    engine = AsyncMock()
    engine.text_to_vector = AsyncMock(return_value=[0.1] * 768)
    return engine


@pytest.fixture
def query_router(mock_pg_storage, mock_vector_store, mock_semantic_engine):
    """Create QueryRouter instance"""
    return QueryRouter(
        pg_storage=mock_pg_storage,
        vector_store=mock_vector_store,
        semantic_engine=mock_semantic_engine,
        concept_threshold=0.8
    )


class TestQueryRouter:
    
    @pytest.mark.asyncio
    async def test_analyze_query_sql(self, query_router):
        """Test SQL query analysis"""
        query = "SELECT * FROM users WHERE id = 1"
        query_type, confidence = await query_router._analyze_query(query)
        
        assert query_type == QueryType.SQL
        assert confidence == 0.95
        
    @pytest.mark.asyncio
    async def test_analyze_query_natural_language(self, query_router):
        """Test natural language query analysis"""
        query = "find similar products to laptop"
        query_type, confidence = await query_router._analyze_query(query)
        
        assert query_type == QueryType.NATURAL_LANGUAGE
        assert confidence >= 0.5
        
    @pytest.mark.asyncio
    async def test_analyze_query_hybrid(self, query_router):
        """Test hybrid query analysis"""
        query = "SELECT customers similar to high-value ones"
        query_type, confidence = await query_router._analyze_query(query)
        
        assert query_type == QueryType.HYBRID
        assert confidence == 0.6
        
    def test_determine_route_sql(self, query_router):
        """Test routing determination for SQL queries"""
        route = query_router._determine_route(QueryType.SQL, 0.95)
        assert route == RouteDecision.POSTGRES
        
    def test_determine_route_high_confidence_semantic(self, query_router):
        """Test routing for high confidence semantic queries"""
        route = query_router._determine_route(QueryType.NATURAL_LANGUAGE, 0.85)
        assert route == RouteDecision.CONCEPTS
        
    def test_determine_route_low_confidence_semantic(self, query_router):
        """Test routing for low confidence semantic queries"""
        route = query_router._determine_route(QueryType.NATURAL_LANGUAGE, 0.6)
        assert route == RouteDecision.BOTH
        
    @pytest.mark.asyncio
    async def test_route_query_to_postgres(self, query_router, mock_pg_storage):
        """Test routing query to PostgreSQL"""
        query = "SELECT * FROM products"
        mock_pg_storage.execute_query.return_value = [
            {'id': 1, 'name': 'Product 1'}
        ]
        
        result = await query_router.route_query(query)
        
        assert result['route'] == 'postgres'
        assert result['query_type'] == 'sql'
        assert len(result['results']) == 1
        assert result['confidence'] == 0.95
        mock_pg_storage.execute_query.assert_called()
        
    @pytest.mark.asyncio
    async def test_route_query_to_concepts(self, query_router, mock_vector_store):
        """Test routing query to concept layer"""
        query = "find similar items like smartphone"
        mock_vector_store.search.return_value = [
            {'id': 'c1', 'score': 0.9, 'payload': {'name': 'iPhone'}}
        ]
        
        result = await query_router.route_query(query)
        
        assert result['route'] == 'concepts'
        assert result['query_type'] == 'natural_language'
        assert len(result['results']) == 1
        mock_vector_store.search.assert_called()
        
    @pytest.mark.asyncio
    async def test_route_query_to_both(self, query_router, mock_pg_storage, mock_vector_store):
        """Test routing query to both layers"""
        query = "products related to electronics"
        mock_pg_storage.execute_query.return_value = [
            {'id': 1, 'name': 'Laptop'}
        ]
        mock_vector_store.search.return_value = [
            {'id': 'c2', 'score': 0.8, 'payload': {'name': 'Tablet'}}
        ]
        
        result = await query_router.route_query(query)
        
        assert result['route'] == 'both'
        assert len(result['results']) == 2
        mock_pg_storage.execute_query.assert_called()
        mock_vector_store.search.assert_called()
        
    @pytest.mark.asyncio
    async def test_fallback_on_error(self, query_router, mock_pg_storage):
        """Test fallback to PostgreSQL on routing error"""
        query = "malformed query"
        # Force an error in analysis
        query_router._analyze_query = AsyncMock(side_effect=Exception("Analysis error"))
        mock_pg_storage.execute_query.return_value = []
        
        result = await query_router.route_query(query)
        
        assert result['route'] == 'postgres_fallback'
        assert result['confidence'] == 0.0
        assert 'Analysis error' in result['explanation']
        
    def test_convert_to_sql_basic_patterns(self, query_router):
        """Test basic natural language to SQL conversion"""
        # Test "find all" pattern
        sql = query_router._convert_to_sql("find all customers")
        assert sql == "SELECT * FROM customers"
        
        # Test "count" pattern
        sql = query_router._convert_to_sql("count products")
        assert sql == "SELECT COUNT(*) FROM products"
        
        # Test "show me" pattern
        sql = query_router._convert_to_sql("show me orders")
        assert sql == "SELECT * FROM orders LIMIT 10"
        
    def test_convert_to_sql_no_match(self, query_router):
        """Test when no SQL pattern matches"""
        sql = query_router._convert_to_sql("something completely different")
        assert sql is None
        
    @pytest.mark.asyncio
    async def test_get_routing_stats(self, query_router, mock_pg_storage):
        """Test getting routing statistics"""
        mock_metrics = {
            'current_phase': 1,
            'conceptualization_ratio': 0.1,
            'total_queries': 100,
            'sql_queries': 90,
            'concept_queries': 10,
            'concept_percentage': 10
        }
        mock_pg_storage.get_evolution_metrics.return_value = mock_metrics
        
        stats = await query_router.get_routing_stats()
        
        assert stats['current_phase'] == 1
        assert stats['total_queries'] == 100
        assert stats['concept_percentage'] == 10
        assert stats['evolution_ready'] is False  # 10% < 25%