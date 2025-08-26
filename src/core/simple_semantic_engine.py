"""
Simple semantic engine using sklearn
For initial deployment without heavy ML dependencies
"""

import hashlib
import numpy as np
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
import re

class SimpleSemanticEngine:
    """Simple semantic engine using TF-IDF"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=384)
        self.is_fitted = False
        
    async def text_to_vector(self, text: str) -> List[float]:
        """Convert text to vector using simple hashing"""
        # Simple approach: Use hash-based vector for initial deployment
        # This creates a deterministic 384-dimensional vector from text
        
        # Clean text
        text = text.lower().strip()
        
        # Create hash-based vector
        vector = []
        for i in range(384):
            # Create unique hash for each dimension
            hash_input = f"{text}_dim_{i}"
            hash_value = hashlib.md5(hash_input.encode()).hexdigest()
            # Convert hash to float between -1 and 1
            normalized = (int(hash_value[:8], 16) / 0xFFFFFFFF) * 2 - 1
            vector.append(normalized)
        
        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    async def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        text = text.lower()
        
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
            'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
            'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'shall', 'can', 'need', 'dare', 'ought'
        }
        
        # Extract words
        words = re.findall(r'\b[a-z]+\b', text)
        
        # Filter and get unique keywords
        keywords = []
        seen = set()
        for word in words:
            if word not in stop_words and word not in seen and len(word) > 2:
                keywords.append(word)
                seen.add(word)
        
        return keywords[:10]  # Return top 10 keywords
    
    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        vec1 = await self.text_to_vector(text1)
        vec2 = await self.text_to_vector(text2)
        
        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 * norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def is_natural_language_query(self, query: str) -> bool:
        """Check if query is natural language or SQL"""
        query_lower = query.lower().strip()
        
        # SQL keywords
        sql_keywords = [
            'select', 'from', 'where', 'insert', 'update', 'delete',
            'create', 'drop', 'alter', 'table', 'join', 'group by',
            'order by', 'having', 'union', 'limit', 'offset'
        ]
        
        # Check for SQL patterns
        for keyword in sql_keywords:
            if keyword in query_lower:
                return False
        
        # Check for SQL-like syntax
        if re.match(r'^\s*(select|insert|update|delete|create|drop|alter)', query_lower):
            return False
        
        return True
    
    async def extract_concepts_from_text(
        self,
        text: str,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Extract concepts from text"""
        keywords = await self.extract_keywords(text)
        
        concepts = []
        for keyword in keywords:
            concepts.append({
                'name': keyword,
                'type': 'keyword',
                'confidence': 0.7,  # Simple fixed confidence
                'description': f"Concept extracted from: {keyword}"
            })
        
        return concepts