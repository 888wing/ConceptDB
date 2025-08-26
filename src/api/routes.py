"""API route handlers for ConceptDB"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Request, Query, Path
from loguru import logger

from src.core import Concept, ConceptMetadata
from .schemas import (
    ConceptCreate, ConceptResponse, ConceptSearch, ConceptSearchResult,
    AnalyzeRequest, AnalyzeResponse, RelationshipRequest, RelationshipResponse,
    BulkImportRequest, BulkImportResponse, InsightRequest, InsightResponse,
    ConceptMetadataSchema
)

# Create routers
concepts_router = APIRouter()
search_router = APIRouter()
analysis_router = APIRouter()
relationships_router = APIRouter()


# Concept CRUD endpoints
@concepts_router.post("/concepts", response_model=ConceptResponse)
async def create_concept(request: Request, concept_data: ConceptCreate):
    """Create a new concept"""
    try:
        storage = request.app.state.storage
        
        # Create concept instance
        metadata = concept_data.metadata or ConceptMetadataSchema()
        concept = Concept(
            name=concept_data.name,
            description=concept_data.description,
            metadata=ConceptMetadata(**metadata.dict())
        )
        
        # Store concept
        created_concept = storage.create_concept(concept)
        
        # Return response
        return ConceptResponse(
            id=created_concept.id,
            name=created_concept.name,
            description=created_concept.description,
            metadata=created_concept.metadata,
            strength=created_concept.strength,
            usage_count=created_concept.usage_count,
            created_at=created_concept.created_at,
            updated_at=created_concept.updated_at,
            relationships=created_concept.get_all_relationships()
        )
        
    except Exception as e:
        logger.error(f"Failed to create concept: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create concept: {str(e)}"
        )


@concepts_router.get("/concepts/{concept_id}", response_model=ConceptResponse)
async def get_concept(request: Request, concept_id: str = Path(...)):
    """Get a concept by ID"""
    try:
        storage = request.app.state.storage
        concept = storage.get_concept(concept_id)
        
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID '{concept_id}' not found"
            )
        
        # Update usage count
        concept.update_usage()
        storage.update_concept(concept)
        
        return ConceptResponse(
            id=concept.id,
            name=concept.name,
            description=concept.description,
            metadata=concept.metadata,
            strength=concept.strength,
            usage_count=concept.usage_count,
            created_at=concept.created_at,
            updated_at=concept.updated_at,
            relationships=concept.get_all_relationships()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get concept: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get concept: {str(e)}"
        )


@concepts_router.get("/concepts", response_model=List[ConceptResponse])
async def list_concepts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """List all concepts with pagination"""
    try:
        storage = request.app.state.storage
        concepts = storage.get_all_concepts(page, page_size)
        
        return [
            ConceptResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                metadata=c.metadata,
                strength=c.strength,
                usage_count=c.usage_count,
                created_at=c.created_at,
                updated_at=c.updated_at,
                relationships=c.get_all_relationships()
            )
            for c in concepts
        ]
        
    except Exception as e:
        logger.error(f"Failed to list concepts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list concepts: {str(e)}"
        )


@concepts_router.delete("/concepts/{concept_id}")
async def delete_concept(request: Request, concept_id: str = Path(...)):
    """Delete a concept"""
    try:
        storage = request.app.state.storage
        
        # Check if concept exists
        concept = storage.get_concept(concept_id)
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID '{concept_id}' not found"
            )
        
        # Delete concept
        success = storage.delete_concept(concept_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete concept"
            )
        
        return {"message": f"Concept '{concept_id}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete concept: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete concept: {str(e)}"
        )


# Search endpoints
@search_router.post("/search", response_model=List[ConceptSearchResult])
async def search_concepts(request: Request, search_data: ConceptSearch):
    """Semantic search for concepts"""
    try:
        storage = request.app.state.storage
        
        # Perform search
        results = storage.search_by_text(
            search_data.query,
            search_data.limit,
            search_data.threshold
        )
        
        # Format response
        search_results = []
        for concept, score in results:
            # Update usage
            concept.update_usage()
            storage.update_concept(concept)
            
            search_results.append(ConceptSearchResult(
                concept=ConceptResponse(
                    id=concept.id,
                    name=concept.name,
                    description=concept.description,
                    metadata=concept.metadata,
                    strength=concept.strength,
                    usage_count=concept.usage_count,
                    created_at=concept.created_at,
                    updated_at=concept.updated_at,
                    relationships=concept.get_all_relationships()
                ),
                similarity_score=score,
                explanation=f"Matched with {score:.2%} similarity"
            ))
        
        return search_results
        
    except Exception as e:
        logger.error(f"Failed to search concepts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search concepts: {str(e)}"
        )


# Analysis endpoints
@analysis_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: Request, analyze_data: AnalyzeRequest):
    """Analyze text and extract concepts"""
    try:
        storage = request.app.state.storage
        semantic_engine = request.app.state.semantic_engine
        
        # Extract keywords
        keywords = semantic_engine.extract_keywords(
            analyze_data.text,
            analyze_data.max_concepts
        )
        
        # Search for existing concepts
        existing_concepts = []
        new_concepts = []
        
        if analyze_data.extract_concepts:
            # Generate embedding for the text
            text_vector = semantic_engine.generate_embedding(analyze_data.text)
            
            # Find similar existing concepts
            similar_concepts = storage.search_similar_concepts(
                text_vector,
                limit=analyze_data.max_concepts,
                threshold=0.5
            )
            
            for concept, score in similar_concepts:
                existing_concepts.append(ConceptResponse(
                    id=concept.id,
                    name=concept.name,
                    description=concept.description,
                    metadata=concept.metadata,
                    strength=concept.strength,
                    usage_count=concept.usage_count,
                    created_at=concept.created_at,
                    updated_at=concept.updated_at,
                    relationships=concept.get_all_relationships()
                ))
        
        # Auto-create concepts from keywords if requested
        if analyze_data.auto_create:
            for keyword in keywords:
                # Check if concept already exists
                existing = False
                for ec in existing_concepts:
                    if ec.name == keyword.lower():
                        existing = True
                        break
                
                if not existing:
                    # Create new concept
                    new_concept = Concept(
                        name=keyword,
                        description=f"Concept extracted from: {analyze_data.text[:100]}...",
                        metadata=ConceptMetadata(
                            source="auto-extraction",
                            tags=["auto-generated"]
                        )
                    )
                    created = storage.create_concept(new_concept)
                    
                    new_concepts.append(ConceptResponse(
                        id=created.id,
                        name=created.name,
                        description=created.description,
                        metadata=created.metadata,
                        strength=created.strength,
                        usage_count=created.usage_count,
                        created_at=created.created_at,
                        updated_at=created.updated_at,
                        relationships=created.get_all_relationships()
                    ))
        
        # Simple sentiment analysis (can be enhanced)
        positive_words = ["good", "excellent", "great", "happy", "love", "best", "wonderful"]
        negative_words = ["bad", "poor", "terrible", "hate", "worst", "awful", "horrible"]
        
        text_lower = analyze_data.text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        total = positive_count + negative_count
        
        sentiment = {
            "positive": positive_count / total if total > 0 else 0.5,
            "negative": negative_count / total if total > 0 else 0.5,
            "neutral": 1 - (positive_count + negative_count) / (total + 1)
        }
        
        return AnalyzeResponse(
            extracted_concepts=[c.name for c in existing_concepts],
            existing_concepts=existing_concepts,
            new_concepts=new_concepts,
            keywords=keywords,
            sentiment=sentiment
        )
        
    except Exception as e:
        logger.error(f"Failed to analyze text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze text: {str(e)}"
        )


# Relationship endpoints
@relationships_router.get("/concepts/{concept_id}/related", response_model=List[ConceptResponse])
async def get_related_concepts(
    request: Request,
    concept_id: str = Path(...),
    relationship_type: Optional[str] = Query(None),
    depth: int = Query(1, ge=1, le=3)
):
    """Get concepts related to a given concept"""
    try:
        storage = request.app.state.storage
        relationship_engine = request.app.state.relationship_engine
        
        # Check if concept exists
        concept = storage.get_concept(concept_id)
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID '{concept_id}' not found"
            )
        
        # Get related concept IDs
        related_ids = relationship_engine.get_related_concepts(
            concept_id,
            relationship_type,
            depth
        )
        
        # Get full concept objects
        related_concepts = []
        for rid in related_ids:
            related_concept = storage.get_concept(rid)
            if related_concept:
                related_concepts.append(ConceptResponse(
                    id=related_concept.id,
                    name=related_concept.name,
                    description=related_concept.description,
                    metadata=related_concept.metadata,
                    strength=related_concept.strength,
                    usage_count=related_concept.usage_count,
                    created_at=related_concept.created_at,
                    updated_at=related_concept.updated_at,
                    relationships=related_concept.get_all_relationships()
                ))
        
        return related_concepts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get related concepts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get related concepts: {str(e)}"
        )


@relationships_router.post("/relationships", response_model=RelationshipResponse)
async def add_relationship(request: Request, relationship_data: RelationshipRequest):
    """Add a relationship between two concepts"""
    try:
        storage = request.app.state.storage
        relationship_engine = request.app.state.relationship_engine
        
        # Check if both concepts exist
        concept1 = storage.get_concept(relationship_data.concept1_id)
        concept2 = storage.get_concept(relationship_data.concept2_id)
        
        if not concept1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID '{relationship_data.concept1_id}' not found"
            )
        
        if not concept2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID '{relationship_data.concept2_id}' not found"
            )
        
        # Add relationship
        success = relationship_engine.add_relationship(
            relationship_data.concept1_id,
            relationship_data.concept2_id,
            relationship_data.relationship_type
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add relationship"
            )
        
        # Calculate relationship strength if vectors available
        strength = None
        if concept1.vector and concept2.vector:
            strength = storage.semantic_engine.calculate_similarity(
                concept1.vector,
                concept2.vector
            )
        
        return RelationshipResponse(
            concept1=ConceptResponse(
                id=concept1.id,
                name=concept1.name,
                description=concept1.description,
                metadata=concept1.metadata,
                strength=concept1.strength,
                usage_count=concept1.usage_count,
                created_at=concept1.created_at,
                updated_at=concept1.updated_at,
                relationships=concept1.get_all_relationships()
            ),
            concept2=ConceptResponse(
                id=concept2.id,
                name=concept2.name,
                description=concept2.description,
                metadata=concept2.metadata,
                strength=concept2.strength,
                usage_count=concept2.usage_count,
                created_at=concept2.created_at,
                updated_at=concept2.updated_at,
                relationships=concept2.get_all_relationships()
            ),
            relationship_type=relationship_data.relationship_type,
            strength=strength
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add relationship: {str(e)}"
        )