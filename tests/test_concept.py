"""Tests for the Concept model and core functionality"""

import pytest
from datetime import datetime
from src.core.concept import Concept, ConceptMetadata


class TestConcept:
    """Test suite for Concept class"""
    
    def test_concept_creation(self):
        """Test basic concept creation"""
        concept = Concept(
            name="test concept",
            description="A test concept for unit testing"
        )
        
        assert concept.name == "test concept"
        assert concept.description == "A test concept for unit testing"
        assert concept.id is not None
        assert concept.strength == 1.0
        assert concept.usage_count == 0
        assert isinstance(concept.created_at, datetime)
        
    def test_concept_name_normalization(self):
        """Test that concept names are normalized"""
        concept = Concept(
            name="  Test CONCEPT  ",
            description="Test description"
        )
        
        assert concept.name == "test concept"
    
    def test_concept_metadata(self):
        """Test concept metadata"""
        metadata = ConceptMetadata(
            category="test",
            tags=["tag1", "tag2"],
            domain="testing"
        )
        
        concept = Concept(
            name="test",
            description="test",
            metadata=metadata
        )
        
        assert concept.metadata.category == "test"
        assert concept.metadata.tags == ["tag1", "tag2"]
        assert concept.metadata.domain == "testing"
    
    def test_add_relationship(self):
        """Test adding relationships between concepts"""
        concept = Concept(
            name="parent",
            description="Parent concept"
        )
        
        # Add different types of relationships
        concept.add_relationship("child_id", "part_of")
        concept.add_relationship("related_id", "related_to")
        concept.add_relationship("opposite_id", "opposite_of")
        
        assert "child_id" in concept.child_ids
        assert "related_id" in concept.related_ids
        assert "opposite_id" in concept.opposite_ids
    
    def test_remove_relationship(self):
        """Test removing relationships"""
        concept = Concept(
            name="test",
            description="test"
        )
        
        # Add and then remove a relationship
        concept.add_relationship("other_id", "related_to")
        assert "other_id" in concept.related_ids
        
        concept.remove_relationship("other_id", "related_to")
        assert "other_id" not in concept.related_ids
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation"""
        concept = Concept(
            name="test",
            description="test",
            vector=[0.1] * 384  # 384-dimensional vector
        )
        
        # Test with identical vector
        score = concept.calculate_relevance_score([0.1] * 384)
        assert score == pytest.approx(1.0, rel=1e-5)
        
        # Test with orthogonal vector
        orthogonal = [0.0] * 384
        score = concept.calculate_relevance_score(orthogonal)
        assert score == pytest.approx(0.0, rel=1e-5)
    
    def test_update_usage(self):
        """Test usage count update"""
        concept = Concept(
            name="test",
            description="test"
        )
        
        initial_count = concept.usage_count
        initial_time = concept.updated_at
        
        concept.update_usage()
        
        assert concept.usage_count == initial_count + 1
        assert concept.updated_at > initial_time
    
    def test_get_embedding_text(self):
        """Test embedding text generation"""
        concept = Concept(
            name="customer satisfaction",
            description="How happy customers are with the service"
        )
        
        embedding_text = concept.get_embedding_text()
        assert "customer satisfaction" in embedding_text
        assert "How happy customers are" in embedding_text
    
    def test_vector_validation(self):
        """Test that vector dimension validation works"""
        with pytest.raises(ValueError):
            # Wrong dimension vector should raise error
            Concept(
                name="test",
                description="test",
                vector=[0.1] * 100  # Wrong dimension
            )