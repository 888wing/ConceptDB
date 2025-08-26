"""
Concept Manager
Manages concept lifecycle, relationships, and operations
"""

import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from .semantic_engine import SemanticEngine
from .vector_store import QdrantStore
from .pg_storage import PostgreSQLStorage

logger = logging.getLogger(__name__)


class ConceptManager:
    """Manages concepts, their relationships, and lifecycle"""
    
    def __init__(
        self,
        semantic_engine: SemanticEngine,
        vector_store: QdrantStore,
        pg_storage: PostgreSQLStorage
    ):
        self.semantic_engine = semantic_engine
        self.vector_store = vector_store
        self.pg_storage = pg_storage
        
    async def create_concept(
        self,
        name: str,
        description: str,
        type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new concept with semantic embedding"""
        try:
            # Generate unique ID
            concept_id = str(uuid.uuid4())
            
            # Create text representation for embedding
            text = f"{name}: {description}"
            
            # Generate semantic embedding
            vector = await self.semantic_engine.text_to_vector(text)
            
            # Prepare payload
            payload = {
                'id': concept_id,
                'name': name,
                'description': description,
                'type': type,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat(),
                'usage_count': 0,
                'confidence_score': 0.5
            }
            
            # Store in vector database
            await self.vector_store.add_vector(
                vector=vector,
                payload=payload,
                vector_id=concept_id
            )
            
            # Also store in PostgreSQL for hybrid access
            await self._store_concept_in_pg(payload)
            
            logger.info(f"Created concept: {concept_id} - {name}")
            return {
                'success': True,
                'concept': payload
            }
            
        except Exception as e:
            logger.error(f"Failed to create concept: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def find_similar_concepts(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Find concepts similar to query"""
        try:
            # Convert query to vector
            query_vector = await self.semantic_engine.text_to_vector(query)
            
            # Search in vector store
            results = await self.vector_store.search(
                vector=query_vector,
                limit=limit,
                score_threshold=min_score
            )
            
            # Enrich results with usage tracking
            enriched_results = []
            for result in results:
                concept = result['payload']
                concept['similarity_score'] = result['score']
                
                # Track usage
                await self._track_concept_usage(concept['id'])
                
                enriched_results.append(concept)
                
            return enriched_results
            
        except Exception as e:
            logger.error(f"Failed to find similar concepts: {e}")
            return []
            
    async def get_concept_by_id(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific concept by ID"""
        try:
            result = await self.vector_store.get_by_id(concept_id)
            if result:
                return result['payload']
            return None
            
        except Exception as e:
            logger.error(f"Failed to get concept {concept_id}: {e}")
            return None
            
    async def update_concept(
        self,
        concept_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update concept metadata and optionally re-embed"""
        try:
            # Get existing concept
            existing = await self.get_concept_by_id(concept_id)
            if not existing:
                return {
                    'success': False,
                    'error': 'Concept not found'
                }
                
            # Merge updates
            updated_concept = {**existing, **updates}
            updated_concept['updated_at'] = datetime.utcnow().isoformat()
            
            # If name or description changed, re-generate embedding
            if 'name' in updates or 'description' in updates:
                text = f"{updated_concept['name']}: {updated_concept['description']}"
                new_vector = await self.semantic_engine.text_to_vector(text)
                
                # Delete old and add new
                await self.vector_store.delete([concept_id])
                await self.vector_store.add_vector(
                    vector=new_vector,
                    payload=updated_concept,
                    vector_id=concept_id
                )
            else:
                # Just update payload
                await self.vector_store.update_payload(
                    vector_id=concept_id,
                    payload=updated_concept
                )
                
            # Update in PostgreSQL
            await self._update_concept_in_pg(concept_id, updated_concept)
            
            return {
                'success': True,
                'concept': updated_concept
            }
            
        except Exception as e:
            logger.error(f"Failed to update concept {concept_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def delete_concept(self, concept_id: str) -> Dict[str, Any]:
        """Delete a concept"""
        try:
            # Delete from vector store
            success = await self.vector_store.delete([concept_id])
            
            # Delete from PostgreSQL
            if success:
                await self._delete_concept_from_pg(concept_id)
                
            return {
                'success': success,
                'message': f"Concept {concept_id} deleted"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete concept {concept_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        strength: float = 0.5
    ) -> Dict[str, Any]:
        """Create a relationship between concepts"""
        try:
            # Verify both concepts exist
            source = await self.get_concept_by_id(source_id)
            target = await self.get_concept_by_id(target_id)
            
            if not source or not target:
                return {
                    'success': False,
                    'error': 'One or both concepts not found'
                }
                
            # Store relationship in PostgreSQL
            query = """
                INSERT INTO concept_relationships 
                (source_id, target_id, relationship_type, strength, created_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """
            
            result = await self.pg_storage.execute_query(
                query,
                [source_id, target_id, relationship_type, strength, datetime.utcnow()]
            )
            
            if result:
                return {
                    'success': True,
                    'relationship_id': result[0]['id'],
                    'source': source_id,
                    'target': target_id,
                    'type': relationship_type,
                    'strength': strength
                }
                
            return {
                'success': False,
                'error': 'Failed to create relationship'
            }
            
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def get_concept_relationships(
        self,
        concept_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all relationships for a concept"""
        try:
            query = """
                SELECT r.*, 
                       cs.name as source_name, 
                       ct.name as target_name
                FROM concept_relationships r
                LEFT JOIN concepts cs ON r.source_id = cs.id
                LEFT JOIN concepts ct ON r.target_id = ct.id
                WHERE (r.source_id = $1 OR r.target_id = $1)
            """
            
            params = [concept_id]
            
            if relationship_type:
                query += " AND r.relationship_type = $2"
                params.append(relationship_type)
                
            results = await self.pg_storage.execute_query(query, params)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get relationships for {concept_id}: {e}")
            return []
            
    async def extract_concepts_from_text(
        self,
        text: str,
        min_confidence: float = 0.5,
        auto_create: bool = False
    ) -> List[Dict[str, Any]]:
        """Extract concepts from text and optionally create them"""
        try:
            # Use semantic engine to extract concepts
            extracted = await self.semantic_engine.extract_concepts(
                text,
                min_confidence
            )
            
            results = []
            
            for concept_data in extracted:
                # Check if similar concept exists
                similar = await self.find_similar_concepts(
                    concept_data['text'],
                    limit=1,
                    min_score=0.8
                )
                
                if similar:
                    # Use existing concept
                    results.append(similar[0])
                elif auto_create:
                    # Create new concept
                    new_concept = await self.create_concept(
                        name=concept_data['text'][:50],
                        description=concept_data['text'],
                        type=concept_data['type'],
                        metadata={'confidence': concept_data['confidence']}
                    )
                    if new_concept['success']:
                        results.append(new_concept['concept'])
                else:
                    # Return as candidate
                    results.append({
                        'text': concept_data['text'],
                        'type': concept_data['type'],
                        'confidence': concept_data['confidence'],
                        'is_candidate': True
                    })
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to extract concepts: {e}")
            return []
            
    async def cluster_concepts(
        self,
        concept_ids: Optional[List[str]] = None,
        n_clusters: int = 5
    ) -> Dict[str, List[str]]:
        """Cluster concepts based on semantic similarity"""
        try:
            # Get concepts and their vectors
            if concept_ids:
                concepts = []
                vectors = []
                for cid in concept_ids:
                    result = await self.vector_store.get_by_id(cid)
                    if result:
                        concepts.append(result['payload'])
                        vectors.append(result['vector'])
            else:
                # Get all concepts (limited for performance)
                sample_vector = [0.0] * 768
                all_concepts = await self.vector_store.search(
                    vector=sample_vector,
                    limit=100
                )
                concepts = [c['payload'] for c in all_concepts]
                vectors = []
                for c in all_concepts:
                    vec_data = await self.vector_store.get_by_id(c['id'])
                    if vec_data:
                        vectors.append(vec_data['vector'])
                        
            if len(vectors) < n_clusters:
                n_clusters = len(vectors)
                
            # Perform clustering
            cluster_labels = self.semantic_engine.cluster_vectors(
                vectors,
                n_clusters
            )
            
            # Group concepts by cluster
            clusters = {}
            for i, label in enumerate(cluster_labels):
                cluster_key = f"cluster_{label}"
                if cluster_key not in clusters:
                    clusters[cluster_key] = []
                clusters[cluster_key].append(concepts[i]['id'])
                
            return clusters
            
        except Exception as e:
            logger.error(f"Failed to cluster concepts: {e}")
            return {}
            
    # Private helper methods
    
    async def _store_concept_in_pg(self, concept: Dict[str, Any]) -> None:
        """Store concept in PostgreSQL"""
        try:
            query = """
                INSERT INTO concepts 
                (id, name, description, type, metadata, created_at, usage_count, confidence_score)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
            """
            
            await self.pg_storage.execute_query(
                query,
                [
                    concept['id'],
                    concept['name'],
                    concept['description'],
                    concept['type'],
                    json.dumps(concept.get('metadata', {})),
                    concept['created_at'],
                    concept.get('usage_count', 0),
                    concept.get('confidence_score', 0.5)
                ]
            )
        except Exception as e:
            logger.error(f"Failed to store concept in PostgreSQL: {e}")
            
    async def _update_concept_in_pg(self, concept_id: str, concept: Dict[str, Any]) -> None:
        """Update concept in PostgreSQL"""
        try:
            query = """
                UPDATE concepts
                SET name = $2, description = $3, metadata = $4, updated_at = $5
                WHERE id = $1
            """
            
            await self.pg_storage.execute_query(
                query,
                [
                    concept_id,
                    concept['name'],
                    concept['description'],
                    json.dumps(concept.get('metadata', {})),
                    concept.get('updated_at', datetime.utcnow().isoformat())
                ]
            )
        except Exception as e:
            logger.error(f"Failed to update concept in PostgreSQL: {e}")
            
    async def _delete_concept_from_pg(self, concept_id: str) -> None:
        """Delete concept from PostgreSQL"""
        try:
            # Delete relationships first
            await self.pg_storage.execute_query(
                "DELETE FROM concept_relationships WHERE source_id = $1 OR target_id = $1",
                [concept_id]
            )
            
            # Delete concept
            await self.pg_storage.execute_query(
                "DELETE FROM concepts WHERE id = $1",
                [concept_id]
            )
        except Exception as e:
            logger.error(f"Failed to delete concept from PostgreSQL: {e}")
            
    async def _track_concept_usage(self, concept_id: str) -> None:
        """Track concept usage for evolution metrics"""
        try:
            query = """
                UPDATE concepts
                SET usage_count = usage_count + 1,
                    last_accessed = $2
                WHERE id = $1
            """
            
            await self.pg_storage.execute_query(
                query,
                [concept_id, datetime.utcnow()]
            )
        except Exception as e:
            logger.error(f"Failed to track concept usage: {e}")