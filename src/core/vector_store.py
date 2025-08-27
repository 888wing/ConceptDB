"""
Qdrant Vector Store Implementation
Handles vector storage and similarity search for concepts
"""

import uuid
from typing import List, Dict, Any, Optional
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct, 
    Filter, 
    FieldCondition, 
    MatchValue,
    SearchRequest
)

logger = logging.getLogger(__name__)


class QdrantStore:
    """Qdrant vector store for concept embeddings"""
    
    def __init__(self, url: str = "http://localhost:6333", collection_name: str = "concepts", api_key: Optional[str] = None):
        self.url = url
        self.collection_name = collection_name
        self.api_key = api_key
        self.client = None
        self.vector_size = 384  # Size for all-MiniLM-L6-v2 model
        
    async def initialize(self) -> None:
        """Initialize Qdrant client and create collection if needed"""
        try:
            # Initialize client with API key if provided
            if self.api_key:
                # Log for debugging
                logger.info(f"Initializing Qdrant client with URL: {self.url} and API key")
                # Use correct parameter name for QdrantClient
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=30
                )
            else:
                logger.info(f"Initializing Qdrant client with URL: {self.url} without API key")
                self.client = QdrantClient(url=self.url, timeout=30)
            
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection with vector configuration
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Using existing Qdrant collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise
            
    async def add_vector(
        self, 
        vector: List[float], 
        payload: Dict[str, Any], 
        vector_id: Optional[str] = None
    ) -> str:
        """Add a vector with metadata to the store"""
        try:
            if not vector_id:
                vector_id = str(uuid.uuid4())
                
            point = PointStruct(
                id=vector_id,
                vector=vector,
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.debug(f"Added vector {vector_id} to collection")
            return vector_id
            
        except Exception as e:
            logger.error(f"Failed to add vector: {e}")
            raise
            
    async def search(
        self,
        vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        try:
            # Build filter if conditions provided
            search_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                if conditions:
                    search_filter = Filter(must=conditions)
            
            # Perform search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                query_filter=search_filter,
                score_threshold=score_threshold
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload or {}
                })
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
            
    async def get_by_id(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by its ID"""
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[vector_id],
                with_vectors=True,
                with_payload=True
            )
            
            if points:
                point = points[0]
                return {
                    'id': point.id,
                    'vector': point.vector,
                    'payload': point.payload
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve vector {vector_id}: {e}")
            return None
            
    async def update_payload(
        self,
        vector_id: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Update the payload of an existing vector"""
        try:
            self.client.update_payload(
                collection_name=self.collection_name,
                payload=payload,
                points=[vector_id]
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to update payload for {vector_id}: {e}")
            return False
            
    async def delete(self, vector_ids: List[str]) -> bool:
        """Delete vectors by IDs"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=vector_ids
            )
            logger.info(f"Deleted {len(vector_ids)} vectors")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False
            
    async def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            # Try to get collections as a health check
            self.client.get_collections()
            return True
        except:
            return False
            
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                'vectors_count': collection_info.vectors_count,
                'indexed_vectors_count': collection_info.indexed_vectors_count,
                'points_count': collection_info.points_count,
                'segments_count': collection_info.segments_count,
                'status': collection_info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}