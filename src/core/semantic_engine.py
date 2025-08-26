"""
Semantic Engine
Handles text-to-vector conversion and semantic operations
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
import faiss
import hashlib
import json

logger = logging.getLogger(__name__)


class SemanticEngine:
    """Engine for semantic understanding and vector operations"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.cache = {}  # Simple in-memory cache for embeddings
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize the transformer model and tokenizer"""
        try:
            logger.info(f"Loading model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"Model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Fallback to random vectors for demo
            self.model = None
            
    async def text_to_vector(self, text: str) -> List[float]:
        """Convert text to vector embedding"""
        # Check cache first
        cache_key = self._get_cache_key(text)
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            if self.model:
                # Use actual model for embedding
                inputs = self.tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    padding=True,
                    max_length=512
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    # Use mean pooling
                    embeddings = outputs.last_hidden_state.mean(dim=1)
                    vector = embeddings[0].cpu().numpy().tolist()
            else:
                # Fallback: Generate consistent pseudo-embedding
                # This ensures same text always produces same vector
                np.random.seed(hash(text) % (2**32))
                vector = np.random.randn(384).tolist()
                
            # Cache the result
            self.cache[cache_key] = vector
            return vector
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return random vector as last resort
            return np.random.randn(384).tolist()
            
    async def batch_text_to_vectors(self, texts: List[str]) -> List[List[float]]:
        """Convert multiple texts to vectors efficiently"""
        vectors = []
        
        # Check for cached vectors first
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self.cache:
                vectors.append(self.cache[cache_key])
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
                vectors.append(None)
                
        # Process uncached texts
        if uncached_texts:
            if self.model:
                try:
                    # Batch processing with model
                    inputs = self.tokenizer(
                        uncached_texts,
                        return_tensors="pt",
                        truncation=True,
                        padding=True,
                        max_length=512
                    )
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        outputs = self.model(**inputs)
                        embeddings = outputs.last_hidden_state.mean(dim=1)
                        batch_vectors = embeddings.cpu().numpy().tolist()
                        
                    # Fill in results and cache
                    for idx, vec, text in zip(uncached_indices, batch_vectors, uncached_texts):
                        vectors[idx] = vec
                        cache_key = self._get_cache_key(text)
                        self.cache[cache_key] = vec
                        
                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    # Fallback to individual processing
                    for idx, text in zip(uncached_indices, uncached_texts):
                        vectors[idx] = await self.text_to_vector(text)
            else:
                # Fallback for all uncached
                for idx, text in zip(uncached_indices, uncached_texts):
                    vectors[idx] = await self.text_to_vector(text)
                    
        return vectors
        
    def calculate_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            v1 = np.array(vector1)
            v2 = np.array(vector2)
            
            # Cosine similarity
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
            
    async def extract_concepts(
        self,
        text: str,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Extract concepts from text"""
        concepts = []
        
        try:
            # Simple concept extraction based on keywords and patterns
            # In production, this would use NER, dependency parsing, etc.
            
            # Split into sentences
            sentences = text.split('. ')
            
            for sentence in sentences:
                # Look for key patterns
                if any(keyword in sentence.lower() for keyword in ['product', 'item', 'service']):
                    concepts.append({
                        'text': sentence[:50],
                        'type': 'entity',
                        'confidence': 0.7
                    })
                    
                if any(keyword in sentence.lower() for keyword in ['similar', 'related', 'like']):
                    concepts.append({
                        'text': sentence[:50],
                        'type': 'relation',
                        'confidence': 0.6
                    })
                    
                if any(keyword in sentence.lower() for keyword in ['high', 'low', 'best', 'worst']):
                    concepts.append({
                        'text': sentence[:50],
                        'type': 'attribute',
                        'confidence': 0.65
                    })
                    
            # Filter by minimum confidence
            concepts = [c for c in concepts if c['confidence'] >= min_confidence]
            
            # Add embeddings to concepts
            for concept in concepts:
                concept['vector'] = await self.text_to_vector(concept['text'])
                
            return concepts
            
        except Exception as e:
            logger.error(f"Concept extraction failed: {e}")
            return []
            
    def cluster_vectors(
        self,
        vectors: List[List[float]],
        n_clusters: int = 5
    ) -> List[int]:
        """Cluster vectors using k-means"""
        try:
            if len(vectors) < n_clusters:
                n_clusters = len(vectors)
                
            # Convert to numpy array
            X = np.array(vectors).astype('float32')
            
            # Use Faiss for efficient k-means
            kmeans = faiss.Kmeans(d=X.shape[1], k=n_clusters, niter=20)
            kmeans.train(X)
            
            # Get cluster assignments
            _, labels = kmeans.index.search(X, 1)
            
            return labels.flatten().tolist()
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            # Return all points in same cluster
            return [0] * len(vectors)
            
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
        
    async def find_analogies(
        self,
        positive: List[str],
        negative: List[str] = []
    ) -> List[float]:
        """Find analogies using vector arithmetic (king - man + woman = queen)"""
        try:
            # Get vectors for positive and negative terms
            pos_vectors = await self.batch_text_to_vectors(positive)
            neg_vectors = await self.batch_text_to_vectors(negative) if negative else []
            
            # Calculate result vector
            result = np.zeros(384)
            
            for vec in pos_vectors:
                result += np.array(vec)
                
            for vec in neg_vectors:
                result -= np.array(vec)
                
            # Normalize
            norm = np.linalg.norm(result)
            if norm > 0:
                result = result / norm
                
            return result.tolist()
            
        except Exception as e:
            logger.error(f"Analogy calculation failed: {e}")
            return [0.0] * 384