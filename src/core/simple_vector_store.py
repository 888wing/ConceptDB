"""
Simple in-memory vector store for initial deployment
Uses sklearn for similarity search instead of Qdrant
"""

import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
import json
import os

class SimpleVectorStore:
    """Simple in-memory vector store using sklearn"""
    
    def __init__(self, persist_path: Optional[str] = None):
        self.vectors = []
        self.metadata = []
        self.persist_path = persist_path or "/tmp/vectors.json"
        self.vector_size = 384
        self.load_from_disk()
    
    async def initialize(self) -> bool:
        """Initialize the vector store"""
        return True
    
    def load_from_disk(self):
        """Load vectors from disk if exists"""
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, 'r') as f:
                    data = json.load(f)
                    self.vectors = [np.array(v) for v in data.get('vectors', [])]
                    self.metadata = data.get('metadata', [])
            except:
                self.vectors = []
                self.metadata = []
    
    def save_to_disk(self):
        """Save vectors to disk"""
        try:
            data = {
                'vectors': [v.tolist() for v in self.vectors],
                'metadata': self.metadata
            }
            with open(self.persist_path, 'w') as f:
                json.dump(data, f)
        except:
            pass
    
    async def add_vector(
        self,
        vector: List[float],
        metadata: Dict[str, Any]
    ) -> str:
        """Add a vector with metadata"""
        vector_id = f"vec_{len(self.vectors)}"
        self.vectors.append(np.array(vector))
        self.metadata.append({**metadata, 'id': vector_id})
        self.save_to_disk()
        return vector_id
    
    async def search_similar(
        self,
        query_vector: List[float],
        limit: int = 10,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        if not self.vectors:
            return []
        
        # Convert to numpy array
        query = np.array(query_vector).reshape(1, -1)
        vectors_matrix = np.array(self.vectors)
        
        # Calculate similarities
        similarities = cosine_similarity(query, vectors_matrix)[0]
        
        # Get top results
        indices = np.argsort(similarities)[::-1][:limit]
        
        results = []
        for idx in indices:
            if similarities[idx] >= min_similarity:
                results.append({
                    **self.metadata[idx],
                    'similarity': float(similarities[idx])
                })
        
        return results
    
    async def get_vector(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID"""
        for i, meta in enumerate(self.metadata):
            if meta.get('id') == vector_id:
                return {
                    'vector': self.vectors[i].tolist(),
                    'metadata': meta
                }
        return None
    
    async def delete_vector(self, vector_id: str) -> bool:
        """Delete a vector by ID"""
        for i, meta in enumerate(self.metadata):
            if meta.get('id') == vector_id:
                del self.vectors[i]
                del self.metadata[i]
                self.save_to_disk()
                return True
        return False
    
    async def clear_collection(self, collection_name: str = "default") -> bool:
        """Clear all vectors"""
        self.vectors = []
        self.metadata = []
        self.save_to_disk()
        return True
    
    async def get_collection_info(self, collection_name: str = "default") -> Dict[str, Any]:
        """Get collection information"""
        return {
            'name': collection_name,
            'vector_count': len(self.vectors),
            'vector_size': self.vector_size,
            'status': 'ready'
        }