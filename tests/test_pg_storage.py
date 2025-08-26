"""
Unit tests for PostgreSQL Storage Layer
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.pg_storage import PostgreSQLStorage


@pytest.fixture
def mock_pool():
    """Create a mock connection pool"""
    pool = AsyncMock()
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def pg_storage():
    """Create PostgreSQLStorage instance"""
    return PostgreSQLStorage("postgresql://test:test@localhost:5432/test")


class TestPostgreSQLStorage:
    
    @pytest.mark.asyncio
    async def test_connect_success(self, pg_storage, mock_pool):
        """Test successful connection"""
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await pg_storage.connect()
            assert pg_storage.pool == mock_pool
            
    @pytest.mark.asyncio
    async def test_connect_failure(self, pg_storage):
        """Test connection failure handling"""
        with patch('asyncpg.create_pool', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                await pg_storage.connect()
                
    @pytest.mark.asyncio
    async def test_disconnect(self, pg_storage, mock_pool):
        """Test disconnection"""
        pg_storage.pool = mock_pool
        await pg_storage.disconnect()
        mock_pool.close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_execute_query_with_params(self, pg_storage):
        """Test query execution with parameters"""
        mock_connection = AsyncMock()
        mock_connection.fetch = AsyncMock(return_value=[
            {'id': 1, 'name': 'Test'}
        ])
        
        mock_pool = AsyncMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire().__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.acquire().__aexit__ = AsyncMock()
        
        pg_storage.pool = mock_pool
        
        result = await pg_storage.execute_query(
            "SELECT * FROM test WHERE id = $1", 
            [1]
        )
        
        assert len(result) == 1
        assert result[0]['id'] == 1
        mock_connection.fetch.assert_called_once_with("SELECT * FROM test WHERE id = $1", 1)
        
    @pytest.mark.asyncio
    async def test_execute_query_without_params(self, pg_storage):
        """Test query execution without parameters"""
        mock_connection = AsyncMock()
        mock_connection.fetch = AsyncMock(return_value=[])
        
        mock_pool = AsyncMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire().__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.acquire().__aexit__ = AsyncMock()
        
        pg_storage.pool = mock_pool
        
        result = await pg_storage.execute_query("SELECT * FROM test")
        
        assert result == []
        mock_connection.fetch.assert_called_once_with("SELECT * FROM test")
        
    @pytest.mark.asyncio
    async def test_health_check_success(self, pg_storage):
        """Test successful health check"""
        pg_storage.execute_query = AsyncMock(return_value=[{'?column?': 1}])
        
        result = await pg_storage.health_check()
        assert result is True
        
    @pytest.mark.asyncio
    async def test_health_check_failure(self, pg_storage):
        """Test failed health check"""
        pg_storage.execute_query = AsyncMock(side_effect=Exception("Database error"))
        
        result = await pg_storage.health_check()
        assert result is False
        
    @pytest.mark.asyncio
    async def test_get_evolution_metrics(self, pg_storage):
        """Test getting evolution metrics"""
        mock_metrics = {
            'current_phase': 1,
            'conceptualization_ratio': 0.1,
            'total_queries': 100,
            'sql_queries': 90,
            'concept_queries': 10
        }
        
        pg_storage.execute_query = AsyncMock(return_value=[mock_metrics])
        
        result = await pg_storage.get_evolution_metrics()
        assert result == mock_metrics
        
    @pytest.mark.asyncio
    async def test_get_evolution_metrics_empty(self, pg_storage):
        """Test getting evolution metrics when no data exists"""
        pg_storage.execute_query = AsyncMock(return_value=[])
        
        result = await pg_storage.get_evolution_metrics()
        assert result['current_phase'] == 1
        assert result['conceptualization_ratio'] == 0.1
        assert result['total_queries'] == 0