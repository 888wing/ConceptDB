"""Core Concept entity and related models"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field, validator
import numpy as np


class ConceptMetadata(BaseModel):
    """Metadata associated with a concept"""
    
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    language: str = Field(default="en")
    domain: Optional[str] = None
    custom_properties: Dict[str, Any] = Field(default_factory=dict)


class Concept(BaseModel):
    """Core Concept entity representing a semantic unit of meaning
    
    This is the fundamental building block of the Concept-Type Database.
    Each concept captures not just data, but meaning and relationships.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    vector: Optional[List[float]] = Field(default=None)
    metadata: ConceptMetadata = Field(default_factory=ConceptMetadata)
    
    # Temporal tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Concept strength and relevance
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    usage_count: int = Field(default=0, ge=0)
    
    # Relationships (stored as IDs)
    parent_ids: List[str] = Field(default_factory=list)
    child_ids: List[str] = Field(default_factory=list)
    related_ids: List[str] = Field(default_factory=list)
    opposite_ids: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    @validator('vector')
    def validate_vector_dimension(cls, v):
        """Ensure vector has correct dimensions (384 for all-MiniLM-L6-v2)"""
        if v is not None and len(v) != 384:
            raise ValueError(f"Vector must have 384 dimensions, got {len(v)}")
        return v
    
    @validator('name')
    def normalize_name(cls, v):
        """Normalize concept name"""
        return v.strip().lower()
    
    def update_usage(self) -> None:
        """Update usage statistics for the concept"""
        self.usage_count += 1
        self.updated_at = datetime.utcnow()
    
    def get_embedding_text(self) -> str:
        """Get text representation for embedding generation"""
        return f"{self.name}: {self.description}"
    
    def calculate_relevance_score(self, query_vector: List[float]) -> float:
        """Calculate relevance score based on vector similarity
        
        Args:
            query_vector: Vector representation of search query
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        if self.vector is None or query_vector is None:
            return 0.0
        
        # Convert to numpy arrays for calculation
        vec1 = np.array(self.vector)
        vec2 = np.array(query_vector)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(max(0.0, min(1.0, similarity)))
    
    def to_dict(self, include_vector: bool = False) -> Dict[str, Any]:
        """Convert concept to dictionary representation
        
        Args:
            include_vector: Whether to include the vector in output
            
        Returns:
            Dictionary representation of the concept
        """
        data = self.dict(exclude={'vector'} if not include_vector else set())
        return data
    
    def add_relationship(self, 
                        other_concept_id: str, 
                        relationship_type: str) -> None:
        """Add a relationship to another concept
        
        Args:
            other_concept_id: ID of the related concept
            relationship_type: Type of relationship (is_a, part_of, related_to, opposite_of)
        """
        if relationship_type == "is_a":
            if other_concept_id not in self.parent_ids:
                self.parent_ids.append(other_concept_id)
        elif relationship_type == "part_of":
            if other_concept_id not in self.child_ids:
                self.child_ids.append(other_concept_id)
        elif relationship_type == "related_to":
            if other_concept_id not in self.related_ids:
                self.related_ids.append(other_concept_id)
        elif relationship_type == "opposite_of":
            if other_concept_id not in self.opposite_ids:
                self.opposite_ids.append(other_concept_id)
        else:
            raise ValueError(f"Unknown relationship type: {relationship_type}")
        
        self.updated_at = datetime.utcnow()
    
    def remove_relationship(self, 
                           other_concept_id: str, 
                           relationship_type: str) -> None:
        """Remove a relationship to another concept
        
        Args:
            other_concept_id: ID of the related concept
            relationship_type: Type of relationship to remove
        """
        if relationship_type == "is_a" and other_concept_id in self.parent_ids:
            self.parent_ids.remove(other_concept_id)
        elif relationship_type == "part_of" and other_concept_id in self.child_ids:
            self.child_ids.remove(other_concept_id)
        elif relationship_type == "related_to" and other_concept_id in self.related_ids:
            self.related_ids.remove(other_concept_id)
        elif relationship_type == "opposite_of" and other_concept_id in self.opposite_ids:
            self.opposite_ids.remove(other_concept_id)
        
        self.updated_at = datetime.utcnow()
    
    def get_all_relationships(self) -> Dict[str, List[str]]:
        """Get all relationships for this concept
        
        Returns:
            Dictionary mapping relationship types to concept IDs
        """
        return {
            "is_a": self.parent_ids,
            "part_of": self.child_ids,
            "related_to": self.related_ids,
            "opposite_of": self.opposite_ids,
        }
    
    def __str__(self) -> str:
        """String representation of the concept"""
        return f"Concept(id={self.id}, name='{self.name}', strength={self.strength})"
    
    def __repr__(self) -> str:
        """Developer-friendly representation"""
        return (f"Concept(id='{self.id}', name='{self.name}', "
                f"description='{self.description[:50]}...', "
                f"vector={'Yes' if self.vector else 'No'}, "
                f"relationships={sum(len(v) for v in self.get_all_relationships().values())})")


class ConceptCollection(BaseModel):
    """Collection of concepts for batch operations"""
    
    concepts: List[Concept]
    total_count: int
    page: int = 1
    page_size: int = 10
    
    def get_concept_by_id(self, concept_id: str) -> Optional[Concept]:
        """Get a concept by its ID from the collection"""
        for concept in self.concepts:
            if concept.id == concept_id:
                return concept
        return None
    
    def get_concept_by_name(self, name: str) -> Optional[Concept]:
        """Get a concept by its name from the collection"""
        normalized_name = name.strip().lower()
        for concept in self.concepts:
            if concept.name == normalized_name:
                return concept
        return None