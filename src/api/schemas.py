"""Pydantic schemas for API request/response models"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator


class ConceptMetadataSchema(BaseModel):
    """Schema for concept metadata"""
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    language: str = Field(default="en")
    domain: Optional[str] = None
    custom_properties: Dict[str, Any] = Field(default_factory=dict)


class ConceptCreate(BaseModel):
    """Schema for creating a new concept"""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    metadata: Optional[ConceptMetadataSchema] = None
    
    @validator('name')
    def normalize_name(cls, v):
        return v.strip().lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "customer satisfaction",
                "description": "The degree to which customers are happy with a product, service, or experience",
                "metadata": {
                    "category": "business",
                    "tags": ["customer", "metrics", "kpi"],
                    "domain": "customer service"
                }
            }
        }


class ConceptResponse(BaseModel):
    """Schema for concept response"""
    id: str
    name: str
    description: str
    metadata: ConceptMetadataSchema
    strength: float
    usage_count: int
    created_at: datetime
    updated_at: datetime
    relationships: Dict[str, List[str]]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConceptSearch(BaseModel):
    """Schema for concept search request"""
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    include_vector: bool = Field(default=False)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "user happiness and satisfaction",
                "limit": 5,
                "threshold": 0.6
            }
        }


class ConceptSearchResult(BaseModel):
    """Schema for concept search result"""
    concept: ConceptResponse
    similarity_score: float = Field(ge=0.0, le=1.0)
    explanation: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Schema for text analysis request"""
    text: str = Field(..., min_length=1, max_length=5000)
    extract_concepts: bool = Field(default=True)
    max_concepts: int = Field(default=5, ge=1, le=20)
    auto_create: bool = Field(default=False)
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "The customer service was excellent. The staff was very helpful and resolved my issue quickly.",
                "extract_concepts": True,
                "max_concepts": 3,
                "auto_create": False
            }
        }


class AnalyzeResponse(BaseModel):
    """Schema for text analysis response"""
    extracted_concepts: List[str]
    existing_concepts: List[ConceptResponse]
    new_concepts: List[ConceptResponse]
    keywords: List[str]
    sentiment: Optional[Dict[str, float]] = None


class RelationshipRequest(BaseModel):
    """Schema for relationship management request"""
    concept1_id: str
    concept2_id: str
    relationship_type: str = Field(..., pattern="^(is_a|part_of|related_to|opposite_of)$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "concept1_id": "uuid-1234",
                "concept2_id": "uuid-5678",
                "relationship_type": "related_to"
            }
        }


class RelationshipResponse(BaseModel):
    """Schema for relationship response"""
    concept1: ConceptResponse
    concept2: ConceptResponse
    relationship_type: str
    strength: Optional[float] = None


class BulkImportRequest(BaseModel):
    """Schema for bulk import request"""
    concepts: List[ConceptCreate]
    auto_relate: bool = Field(default=True)
    similarity_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class BulkImportResponse(BaseModel):
    """Schema for bulk import response"""
    total: int
    successful: int
    failed: int
    created_concepts: List[str]
    errors: List[Dict[str, str]]


class InsightRequest(BaseModel):
    """Schema for customer insight request"""
    feedbacks: List[str] = Field(..., min_items=1, max_items=1000)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "feedbacks": [
                    "Great product but shipping was slow",
                    "Love the quality, worth the price",
                    "Customer service needs improvement"
                ],
                "min_confidence": 0.6
            }
        }


class InsightResponse(BaseModel):
    """Schema for customer insight response"""
    total_feedbacks: int
    concepts_found: List[Dict[str, Any]]
    sentiment_analysis: Dict[str, float]
    key_themes: List[str]
    recommendations: List[str]
    concept_heatmap: Dict[str, int]


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str
    detail: Optional[str] = None
    status_code: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Concept not found",
                "detail": "No concept with ID 'invalid-id' exists",
                "status_code": 404
            }
        }


class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    version: str
    qdrant_connected: bool
    database_connected: bool
    model_loaded: bool
    total_concepts: int