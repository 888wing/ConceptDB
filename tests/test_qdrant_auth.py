"""Unit tests for Qdrant authentication and vector store initialization"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.vector_store import QdrantStore
from src.core.simple_vector_store import SimpleVectorStore


class TestQdrantAuthentication:
    """Test Qdrant authentication mechanisms"""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock QdrantClient"""
        with patch('src.core.vector_store.QdrantClient') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_qdrant_init_with_api_key(self, mock_qdrant_client):
        """Test QdrantStore initialization with API key"""
        # Setup
        api_key = "test-api-key-123"
        url = "http://test-qdrant:6333"
        
        # Mock the client instance
        mock_client_instance = MagicMock()
        mock_client_instance.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.return_value = mock_client_instance
        
        # Create store with API key
        store = QdrantStore(url=url, api_key=api_key)
        
        # Initialize
        await store.initialize()
        
        # Verify QdrantClient was called with correct parameters
        mock_qdrant_client.assert_called_once()
        call_kwargs = mock_qdrant_client.call_args.kwargs
        assert call_kwargs['url'] == url
        assert call_kwargs['api_key'] == api_key
        assert 'timeout' in call_kwargs
    
    @pytest.mark.asyncio
    async def test_qdrant_init_without_api_key(self, mock_qdrant_client):
        """Test QdrantStore initialization without API key"""
        # Setup
        url = "http://test-qdrant:6333"
        
        # Mock the client instance
        mock_client_instance = MagicMock()
        mock_client_instance.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.return_value = mock_client_instance
        
        # Create store without API key
        store = QdrantStore(url=url)
        
        # Initialize
        await store.initialize()
        
        # Verify QdrantClient was called without API key
        mock_qdrant_client.assert_called_once()
        call_kwargs = mock_qdrant_client.call_args.kwargs
        assert call_kwargs['url'] == url
        assert 'api_key' not in call_kwargs or call_kwargs.get('api_key') is None
    
    @pytest.mark.asyncio
    async def test_qdrant_timeout_from_env(self, mock_qdrant_client):
        """Test QdrantStore uses timeout from environment variable"""
        # Setup
        os.environ['QDRANT_TIMEOUT'] = '60'
        url = "http://test-qdrant:6333"
        
        # Mock the client instance
        mock_client_instance = MagicMock()
        mock_client_instance.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.return_value = mock_client_instance
        
        try:
            # Create and initialize store
            store = QdrantStore(url=url)
            await store.initialize()
            
            # Verify timeout was used
            mock_qdrant_client.assert_called_once()
            call_kwargs = mock_qdrant_client.call_args.kwargs
            assert call_kwargs['timeout'] == 60
        finally:
            # Cleanup
            if 'QDRANT_TIMEOUT' in os.environ:
                del os.environ['QDRANT_TIMEOUT']
    
    @pytest.mark.asyncio
    async def test_qdrant_connection_failure_raises(self, mock_qdrant_client):
        """Test that connection failure raises exception"""
        # Setup
        url = "http://test-qdrant:6333"
        
        # Mock client to raise exception
        mock_qdrant_client.side_effect = Exception("Connection refused")
        
        # Create store
        store = QdrantStore(url=url)
        
        # Verify exception is raised
        with pytest.raises(Exception) as exc_info:
            await store.initialize()
        assert "Connection refused" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_qdrant_unauthorized_error(self, mock_qdrant_client):
        """Test handling of 401 Unauthorized error"""
        # Setup
        url = "http://test-qdrant:6333"
        
        # Mock client instance that raises 401 on get_collections
        mock_client_instance = MagicMock()
        mock_client_instance.get_collections.side_effect = Exception(
            "Unexpected Response: 401 (Unauthorized)\n"
            "Raw response content:\n"
            "b'Must provide an API key or an Authorization bearer token'"
        )
        mock_qdrant_client.return_value = mock_client_instance
        
        # Create store without API key
        store = QdrantStore(url=url)
        
        # Verify exception is raised
        with pytest.raises(Exception) as exc_info:
            await store.initialize()
        assert "401" in str(exc_info.value)
        assert "Unauthorized" in str(exc_info.value)


class TestVectorStoreFallback:
    """Test fallback mechanism from Qdrant to SimpleVectorStore"""
    
    @pytest.mark.asyncio
    async def test_simple_vector_store_initialization(self):
        """Test SimpleVectorStore initialization"""
        store = SimpleVectorStore()
        
        # Initialize should not raise any errors
        await store.initialize()
        
        # Verify basic functionality
        assert store.vectors == {}
        assert store.payloads == {}
        assert store.vector_size == 384
    
    @pytest.mark.asyncio
    async def test_simple_vector_store_add_vector(self):
        """Test adding vectors to SimpleVectorStore"""
        store = SimpleVectorStore()
        await store.initialize()
        
        # Add a vector
        vector = [0.1] * 384
        payload = {"name": "test", "description": "test concept"}
        vector_id = await store.add_vector(vector, payload)
        
        # Verify vector was added
        assert vector_id in store.vectors
        assert store.vectors[vector_id] == vector
        assert store.payloads[vector_id] == payload
    
    @pytest.mark.asyncio
    async def test_simple_vector_store_search(self):
        """Test searching in SimpleVectorStore"""
        store = SimpleVectorStore()
        await store.initialize()
        
        # Add some test vectors
        vector1 = [1.0] + [0.0] * 383
        vector2 = [0.9] + [0.0] * 383
        vector3 = [0.0] + [1.0] + [0.0] * 382
        
        id1 = await store.add_vector(vector1, {"name": "concept1"})
        id2 = await store.add_vector(vector2, {"name": "concept2"})
        id3 = await store.add_vector(vector3, {"name": "concept3"})
        
        # Search with query vector similar to vector1
        query_vector = [0.95] + [0.0] * 383
        results = await store.search(query_vector, limit=2)
        
        # Verify results
        assert len(results) == 2
        assert results[0]['id'] in [id1, id2]  # Should match vector1 or vector2
        assert results[0]['score'] > 0.9  # High similarity score


class TestConfigurationValidation:
    """Test configuration validation"""
    
    def test_config_validator_import(self):
        """Test that config validator can be imported"""
        from src.core.config_validator import ConfigValidator, validate_config_on_startup
        assert ConfigValidator is not None
        assert validate_config_on_startup is not None
    
    def test_config_validator_database_validation(self):
        """Test database configuration validation"""
        from src.core.config_validator import ConfigValidator
        
        validator = ConfigValidator()
        
        # Test with PostgreSQL URL
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost:5432/db'
        validator._validate_database()
        assert len(validator.errors) == 0
        assert any('PostgreSQL configured' in msg for msg in validator.info)
        
        # Test with invalid URL
        os.environ['DATABASE_URL'] = 'invalid://url'
        validator.errors = []
        validator.info = []
        validator._validate_database()
        assert len(validator.errors) > 0
        
        # Cleanup
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
    
    def test_config_validator_qdrant_validation(self):
        """Test Qdrant configuration validation"""
        from src.core.config_validator import ConfigValidator
        
        validator = ConfigValidator()
        
        # Test with Zeabur environment
        os.environ['ZEABUR'] = 'true'
        os.environ['QDRANT_URL'] = 'http://qdrant.zeabur.internal:6333'
        os.environ['QDRANT_API_KEY'] = 'test-key'
        
        validator._validate_qdrant()
        assert any('Qdrant API key configured' in msg for msg in validator.info)
        
        # Test without API key on Zeabur (should warn)
        del os.environ['QDRANT_API_KEY']
        validator.warnings = []
        validator._validate_qdrant()
        assert any('QDRANT_API_KEY not set' in msg for msg in validator.warnings)
        
        # Cleanup
        for key in ['ZEABUR', 'QDRANT_URL', 'QDRANT_API_KEY']:
            if key in os.environ:
                del os.environ[key]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])