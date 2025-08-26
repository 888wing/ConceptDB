"""Storage layer for concepts using Qdrant and SQLite"""

import os
import json
import sqlite3
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue,
    SearchRequest, UpdateStatus
)
from loguru import logger

from .concept import Concept, ConceptMetadata
from .semantic_engine import SemanticEngine


class ConceptStorage:
    """Storage manager for concepts using Qdrant for vectors and SQLite for metadata"""
    
    def __init__(self, 
                 qdrant_host: str = None,
                 qdrant_port: int = None,
                 collection_name: str = None,
                 database_path: str = None,
                 semantic_engine: SemanticEngine = None):
        """Initialize storage connections
        
        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            collection_name: Name of the Qdrant collection
            database_path: Path to SQLite database
            semantic_engine: Semantic engine for vector operations
        """
        # Qdrant configuration
        self.qdrant_host = qdrant_host or os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = qdrant_port or int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION_NAME", "concepts")
        
        # SQLite configuration
        self.database_path = database_path or os.getenv("DATABASE_PATH", "./data/concepts.db")
        
        # Initialize semantic engine
        self.semantic_engine = semantic_engine or SemanticEngine()
        
        # Initialize connections
        self._init_qdrant()
        self._init_sqlite()
        
        logger.info("ConceptStorage initialized successfully")
    
    def _init_qdrant(self):
        """Initialize Qdrant client and collection"""
        try:
            self.qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port
            )
            
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Using existing Qdrant collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise
    
    def _init_sqlite(self):
        """Initialize SQLite database and tables"""
        try:
            # Create data directory if it doesn't exist
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.db_conn = sqlite3.connect(self.database_path, check_same_thread=False)
            self.db_conn.row_factory = sqlite3.Row
            
            # Create concepts table
            self.db_conn.execute("""
                CREATE TABLE IF NOT EXISTS concepts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metadata TEXT,
                    strength REAL DEFAULT 1.0,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    parent_ids TEXT,
                    child_ids TEXT,
                    related_ids TEXT,
                    opposite_ids TEXT
                )
            """)
            
            # Create indices for better performance
            self.db_conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON concepts(name)")
            self.db_conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON concepts(created_at)")
            self.db_conn.execute("CREATE INDEX IF NOT EXISTS idx_usage ON concepts(usage_count)")
            
            self.db_conn.commit()
            logger.info(f"SQLite database initialized at: {self.database_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            raise
    
    def create_concept(self, concept: Concept) -> Concept:
        """Create a new concept in storage
        
        Args:
            concept: Concept to create
            
        Returns:
            Created concept with generated vector
        """
        try:
            # Generate embedding if not provided
            if concept.vector is None:
                embedding_text = concept.get_embedding_text()
                concept.vector = self.semantic_engine.generate_embedding(embedding_text)
            
            # Store in Qdrant
            point = PointStruct(
                id=concept.id,
                vector=concept.vector,
                payload={
                    "name": concept.name,
                    "description": concept.description,
                    "strength": concept.strength,
                    "created_at": concept.created_at.isoformat()
                }
            )
            
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            # Store in SQLite
            self.db_conn.execute("""
                INSERT INTO concepts (
                    id, name, description, metadata, strength, usage_count,
                    created_at, updated_at, parent_ids, child_ids, 
                    related_ids, opposite_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                concept.id,
                concept.name,
                concept.description,
                json.dumps(concept.metadata.dict()),
                concept.strength,
                concept.usage_count,
                concept.created_at.isoformat(),
                concept.updated_at.isoformat(),
                json.dumps(concept.parent_ids),
                json.dumps(concept.child_ids),
                json.dumps(concept.related_ids),
                json.dumps(concept.opposite_ids)
            ))
            
            self.db_conn.commit()
            
            logger.info(f"Created concept: {concept.id} - {concept.name}")
            return concept
            
        except Exception as e:
            logger.error(f"Failed to create concept: {e}")
            self.db_conn.rollback()
            raise
    
    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Retrieve a concept by ID
        
        Args:
            concept_id: ID of the concept
            
        Returns:
            Concept if found, None otherwise
        """
        try:
            # Get from SQLite
            cursor = self.db_conn.execute(
                "SELECT * FROM concepts WHERE id = ?",
                (concept_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Get vector from Qdrant
            points = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=[concept_id]
            )
            
            vector = None
            if points:
                vector = points[0].vector
            
            # Reconstruct concept
            concept = Concept(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                vector=vector,
                metadata=ConceptMetadata(**json.loads(row["metadata"])),
                strength=row["strength"],
                usage_count=row["usage_count"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                parent_ids=json.loads(row["parent_ids"]),
                child_ids=json.loads(row["child_ids"]),
                related_ids=json.loads(row["related_ids"]),
                opposite_ids=json.loads(row["opposite_ids"])
            )
            
            return concept
            
        except Exception as e:
            logger.error(f"Failed to get concept {concept_id}: {e}")
            return None
    
    def update_concept(self, concept: Concept) -> bool:
        """Update an existing concept
        
        Args:
            concept: Updated concept
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update vector in Qdrant if changed
            if concept.vector:
                point = PointStruct(
                    id=concept.id,
                    vector=concept.vector,
                    payload={
                        "name": concept.name,
                        "description": concept.description,
                        "strength": concept.strength,
                        "created_at": concept.created_at.isoformat()
                    }
                )
                
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
            
            # Update in SQLite
            concept.updated_at = datetime.utcnow()
            
            self.db_conn.execute("""
                UPDATE concepts SET
                    name = ?, description = ?, metadata = ?,
                    strength = ?, usage_count = ?, updated_at = ?,
                    parent_ids = ?, child_ids = ?, related_ids = ?, opposite_ids = ?
                WHERE id = ?
            """, (
                concept.name,
                concept.description,
                json.dumps(concept.metadata.dict()),
                concept.strength,
                concept.usage_count,
                concept.updated_at.isoformat(),
                json.dumps(concept.parent_ids),
                json.dumps(concept.child_ids),
                json.dumps(concept.related_ids),
                json.dumps(concept.opposite_ids),
                concept.id
            ))
            
            self.db_conn.commit()
            
            logger.info(f"Updated concept: {concept.id} - {concept.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update concept: {e}")
            self.db_conn.rollback()
            return False
    
    def delete_concept(self, concept_id: str) -> bool:
        """Delete a concept from storage
        
        Args:
            concept_id: ID of the concept to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from Qdrant
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=[concept_id]
            )
            
            # Delete from SQLite
            self.db_conn.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))
            self.db_conn.commit()
            
            logger.info(f"Deleted concept: {concept_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete concept {concept_id}: {e}")
            self.db_conn.rollback()
            return False
    
    def search_similar_concepts(self,
                               query_vector: List[float],
                               limit: int = 10,
                               threshold: float = 0.7) -> List[Tuple[Concept, float]]:
        """Search for concepts similar to a query vector
        
        Args:
            query_vector: Query vector
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            
        Returns:
            List of tuples (concept, similarity_score)
        """
        try:
            # Search in Qdrant
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=threshold
            )
            
            results = []
            for point in search_result:
                # Get full concept from SQLite
                concept = self.get_concept(point.id)
                if concept:
                    results.append((concept, point.score))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search concepts: {e}")
            return []
    
    def search_by_text(self,
                      query: str,
                      limit: int = 10,
                      threshold: float = 0.7) -> List[Tuple[Concept, float]]:
        """Search for concepts using natural language query
        
        Args:
            query: Natural language search query
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            
        Returns:
            List of tuples (concept, similarity_score)
        """
        # Generate query vector
        query_vector = self.semantic_engine.generate_embedding(query)
        
        # Search similar concepts
        return self.search_similar_concepts(query_vector, limit, threshold)
    
    def get_all_concepts(self, 
                        page: int = 1, 
                        page_size: int = 10) -> List[Concept]:
        """Get all concepts with pagination
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of concepts per page
            
        Returns:
            List of concepts
        """
        try:
            offset = (page - 1) * page_size
            
            cursor = self.db_conn.execute("""
                SELECT * FROM concepts
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (page_size, offset))
            
            concepts = []
            for row in cursor:
                # Get vector from Qdrant
                points = self.qdrant_client.retrieve(
                    collection_name=self.collection_name,
                    ids=[row["id"]]
                )
                
                vector = None
                if points:
                    vector = points[0].vector
                
                concept = Concept(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    vector=vector,
                    metadata=ConceptMetadata(**json.loads(row["metadata"])),
                    strength=row["strength"],
                    usage_count=row["usage_count"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    parent_ids=json.loads(row["parent_ids"]),
                    child_ids=json.loads(row["child_ids"]),
                    related_ids=json.loads(row["related_ids"]),
                    opposite_ids=json.loads(row["opposite_ids"])
                )
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"Failed to get all concepts: {e}")
            return []
    
    def get_concept_count(self) -> int:
        """Get total number of concepts
        
        Returns:
            Total count of concepts
        """
        try:
            cursor = self.db_conn.execute("SELECT COUNT(*) as count FROM concepts")
            return cursor.fetchone()["count"]
        except Exception as e:
            logger.error(f"Failed to get concept count: {e}")
            return 0
    
    def close(self):
        """Close storage connections"""
        if hasattr(self, 'db_conn'):
            self.db_conn.close()
        logger.info("ConceptStorage connections closed")