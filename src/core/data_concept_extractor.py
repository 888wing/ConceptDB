"""
Data Concept Extractor
Automatically extracts concepts from PostgreSQL data
Phase 1-2: Bridge between precise data and conceptual understanding
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


class DataConceptExtractor:
    """Extracts concepts from structured PostgreSQL data"""
    
    def __init__(
        self,
        pg_storage,
        concept_manager,
        semantic_engine,
        min_confidence: float = 0.5
    ):
        """
        Initialize concept extractor
        
        Args:
            pg_storage: PostgreSQL storage instance
            concept_manager: Concept manager for storing extracted concepts
            semantic_engine: Semantic engine for vectorization
            min_confidence: Minimum confidence for concept creation
        """
        self.pg_storage = pg_storage
        self.concept_manager = concept_manager
        self.semantic_engine = semantic_engine
        self.min_confidence = min_confidence
        
        # Track extraction progress
        self.extraction_stats = {
            'tables_processed': 0,
            'concepts_created': 0,
            'relationships_discovered': 0,
            'last_extraction': None
        }
        
    async def extract_from_table(
        self,
        table_name: str,
        sample_size: int = 1000,
        text_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract concepts from a specific table
        
        Args:
            table_name: Name of the table to extract from
            sample_size: Number of rows to sample
            text_columns: Specific columns to extract text from
            
        Returns:
            Extraction results
        """
        try:
            logger.info(f"Extracting concepts from table: {table_name}")
            
            # Get table schema
            schema = await self.pg_storage.get_table_schema(table_name)
            
            # Identify text columns if not specified
            if not text_columns:
                text_columns = self._identify_text_columns(schema)
                
            if not text_columns:
                logger.warning(f"No text columns found in {table_name}")
                return {
                    'success': False,
                    'message': 'No text columns for concept extraction'
                }
                
            # Sample data from table
            sample_data = await self.pg_storage.get_sample_data(
                table_name, 
                sample_size
            )
            
            if not sample_data:
                return {
                    'success': False,
                    'message': 'No data to extract from'
                }
                
            # Extract concepts from data
            concepts = await self._extract_concepts_from_rows(
                sample_data,
                text_columns,
                table_name
            )
            
            # Discover relationships
            relationships = await self._discover_relationships(concepts)
            
            # Store concepts and relationships
            stored_concepts = await self._store_concepts(concepts, table_name)
            stored_relationships = await self._store_relationships(relationships)
            
            # Update extraction stats
            self.extraction_stats['tables_processed'] += 1
            self.extraction_stats['concepts_created'] += len(stored_concepts)
            self.extraction_stats['relationships_discovered'] += len(stored_relationships)
            self.extraction_stats['last_extraction'] = datetime.utcnow().isoformat()
            
            return {
                'success': True,
                'table': table_name,
                'concepts_extracted': len(stored_concepts),
                'relationships_discovered': len(stored_relationships),
                'sample_size': len(sample_data),
                'concepts': stored_concepts[:10]  # Return first 10 as preview
            }
            
        except Exception as e:
            logger.error(f"Failed to extract from table {table_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def _identify_text_columns(self, schema: List[Dict[str, Any]]) -> List[str]:
        """Identify columns suitable for text extraction"""
        text_columns = []
        text_types = [
            'text', 'varchar', 'character varying', 'char', 
            'character', 'json', 'jsonb', 'name'
        ]
        
        for column in schema:
            data_type = column.get('data_type', '').lower()
            column_name = column.get('column_name', '')
            
            # Check if it's a text type
            if any(t in data_type for t in text_types):
                # Skip system columns
                if column_name not in ['id', 'uuid', 'created_at', 'updated_at']:
                    text_columns.append(column_name)
                    
        return text_columns
        
    async def _extract_concepts_from_rows(
        self,
        rows: List[Dict[str, Any]],
        text_columns: List[str],
        table_name: str
    ) -> List[Dict[str, Any]]:
        """Extract concepts from data rows"""
        concepts = []
        text_corpus = []
        
        # Collect text from all rows
        for row in rows:
            row_text = []
            for col in text_columns:
                value = row.get(col)
                if value:
                    row_text.append(str(value))
            if row_text:
                text_corpus.append(' '.join(row_text))
                
        if not text_corpus:
            return []
            
        # Use TF-IDF to identify important terms
        try:
            vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words='english',
                ngram_range=(1, 3),
                min_df=2
            )
            
            tfidf_matrix = vectorizer.fit_transform(text_corpus)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get top terms with scores
            scores = tfidf_matrix.sum(axis=0).A1
            top_indices = scores.argsort()[-30:][::-1]
            
            for idx in top_indices:
                term = feature_names[idx]
                score = scores[idx]
                
                # Calculate confidence based on TF-IDF score
                confidence = min(score / 10, 1.0)  # Normalize score
                
                if confidence >= self.min_confidence:
                    concept = {
                        'name': term,
                        'description': f"Concept extracted from {table_name}",
                        'type': 'extracted',
                        'source_table': table_name,
                        'confidence': confidence,
                        'frequency': int(score),
                        'metadata': {
                            'extraction_method': 'tfidf',
                            'source_columns': text_columns,
                            'extraction_date': datetime.utcnow().isoformat()
                        }
                    }
                    concepts.append(concept)
                    
        except Exception as e:
            logger.warning(f"TF-IDF extraction failed: {e}, using fallback")
            # Fallback to simple frequency-based extraction
            concepts = self._fallback_extraction(text_corpus, table_name)
            
        # Cluster concepts if we have enough
        if len(concepts) > 10:
            concepts = await self._cluster_concepts(concepts)
            
        return concepts
        
    def _fallback_extraction(
        self, 
        text_corpus: List[str], 
        table_name: str
    ) -> List[Dict[str, Any]]:
        """Fallback extraction using simple frequency analysis"""
        word_freq = defaultdict(int)
        
        for text in text_corpus:
            words = text.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_freq[word] += 1
                    
        # Get top words
        concepts = []
        for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]:
            if freq > 2:  # Minimum frequency threshold
                concept = {
                    'name': word,
                    'description': f"Frequently occurring term in {table_name}",
                    'type': 'extracted',
                    'source_table': table_name,
                    'confidence': min(freq / 100, 1.0),
                    'frequency': freq,
                    'metadata': {
                        'extraction_method': 'frequency',
                        'extraction_date': datetime.utcnow().isoformat()
                    }
                }
                concepts.append(concept)
                
        return concepts
        
    async def _cluster_concepts(
        self, 
        concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Cluster similar concepts to reduce redundancy"""
        try:
            # Create vectors for concepts
            concept_texts = [c['name'] for c in concepts]
            vectors = []
            
            for text in concept_texts:
                vector = await self.semantic_engine.text_to_vector(text)
                vectors.append(vector)
                
            vectors = np.array(vectors)
            
            # Cluster using KMeans
            n_clusters = min(len(concepts) // 3, 10)  # Adaptive cluster count
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(vectors)
            
            # Select representative concept from each cluster
            clustered_concepts = []
            for cluster_id in range(n_clusters):
                cluster_indices = np.where(clusters == cluster_id)[0]
                
                # Select concept with highest confidence in cluster
                cluster_concepts = [concepts[i] for i in cluster_indices]
                best_concept = max(cluster_concepts, key=lambda x: x['confidence'])
                
                # Merge information from cluster
                best_concept['metadata']['cluster_size'] = len(cluster_concepts)
                best_concept['metadata']['merged_concepts'] = [
                    c['name'] for c in cluster_concepts if c != best_concept
                ][:5]  # Keep first 5 merged concepts
                
                clustered_concepts.append(best_concept)
                
            return clustered_concepts
            
        except Exception as e:
            logger.warning(f"Clustering failed: {e}, returning original concepts")
            return concepts
            
    async def _discover_relationships(
        self, 
        concepts: List[Dict[str, Any]]
    ) -> List[Tuple[str, str, str, float]]:
        """Discover relationships between extracted concepts"""
        relationships = []
        
        if len(concepts) < 2:
            return relationships
            
        try:
            # Create similarity matrix
            vectors = []
            for concept in concepts:
                text = f"{concept['name']} {concept.get('description', '')}"
                vector = await self.semantic_engine.text_to_vector(text)
                vectors.append(vector)
                
            vectors = np.array(vectors)
            
            # Calculate pairwise similarities
            for i in range(len(concepts)):
                for j in range(i + 1, len(concepts)):
                    similarity = np.dot(vectors[i], vectors[j]) / (
                        np.linalg.norm(vectors[i]) * np.linalg.norm(vectors[j])
                    )
                    
                    # Determine relationship type based on similarity
                    if similarity > 0.9:
                        rel_type = 'is_a'
                        confidence = similarity
                    elif similarity > 0.7:
                        rel_type = 'related_to'
                        confidence = similarity
                    elif similarity < 0.3:
                        rel_type = 'opposite_of'
                        confidence = 1 - similarity
                    else:
                        continue  # No clear relationship
                        
                    relationships.append((
                        concepts[i]['name'],
                        concepts[j]['name'],
                        rel_type,
                        confidence
                    ))
                    
        except Exception as e:
            logger.warning(f"Relationship discovery failed: {e}")
            
        return relationships
        
    async def _store_concepts(
        self, 
        concepts: List[Dict[str, Any]], 
        table_name: str
    ) -> List[Dict[str, Any]]:
        """Store extracted concepts"""
        stored = []
        
        for concept in concepts:
            try:
                # Check if concept already exists
                existing = await self.concept_manager.find_similar_concepts(
                    concept['name'],
                    limit=1,
                    min_score=0.95
                )
                
                if not existing:
                    # Create new concept
                    result = await self.concept_manager.create_concept(
                        name=concept['name'],
                        description=concept.get('description', ''),
                        type=concept.get('type', 'extracted'),
                        metadata=concept.get('metadata', {})
                    )
                    
                    if result['success']:
                        stored.append(result['concept'])
                        
                        # Update concept mapping in PostgreSQL
                        await self.pg_storage.update_concept_mapping(
                            table_name=table_name,
                            column_name='*',  # All columns
                            concept_id=result['concept']['id'],
                            confidence=concept['confidence']
                        )
                else:
                    # Update existing concept's metadata
                    existing_concept = existing[0]
                    existing_concept['metadata']['extraction_count'] = \
                        existing_concept.get('metadata', {}).get('extraction_count', 0) + 1
                    stored.append(existing_concept)
                    
            except Exception as e:
                logger.error(f"Failed to store concept {concept['name']}: {e}")
                
        return stored
        
    async def _store_relationships(
        self,
        relationships: List[Tuple[str, str, str, float]]
    ) -> List[Dict[str, Any]]:
        """Store discovered relationships"""
        stored = []
        
        for concept1_name, concept2_name, rel_type, confidence in relationships:
            if confidence < self.min_confidence:
                continue
                
            try:
                # Find concept IDs
                concepts1 = await self.concept_manager.find_similar_concepts(
                    concept1_name, limit=1, min_score=0.9
                )
                concepts2 = await self.concept_manager.find_similar_concepts(
                    concept2_name, limit=1, min_score=0.9
                )
                
                if concepts1 and concepts2:
                    # Store relationship
                    # Note: This would need to be implemented in concept_manager
                    stored.append({
                        'concept1': concept1_name,
                        'concept2': concept2_name,
                        'type': rel_type,
                        'confidence': confidence
                    })
                    
            except Exception as e:
                logger.error(f"Failed to store relationship: {e}")
                
        return stored
        
    async def extract_from_all_tables(
        self,
        exclude_tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract concepts from all tables in the database
        
        Args:
            exclude_tables: Tables to skip
            
        Returns:
            Overall extraction results
        """
        exclude_tables = exclude_tables or ['migrations', 'schema_versions']
        
        # Get all tables
        query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
        """
        
        tables = await self.pg_storage.execute_query(query)
        results = {
            'total_tables': len(tables),
            'processed': 0,
            'total_concepts': 0,
            'total_relationships': 0,
            'table_results': {}
        }
        
        for table_row in tables:
            table_name = table_row['tablename']
            
            if table_name in exclude_tables:
                continue
                
            logger.info(f"Processing table: {table_name}")
            
            # Extract from table
            result = await self.extract_from_table(table_name)
            
            if result['success']:
                results['processed'] += 1
                results['total_concepts'] += result.get('concepts_extracted', 0)
                results['total_relationships'] += result.get('relationships_discovered', 0)
                results['table_results'][table_name] = result
                
        return results
        
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return self.extraction_stats