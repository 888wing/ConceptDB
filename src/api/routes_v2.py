"""API Routes v2 for Phase 1 - Evolutionary Architecture"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.core.pg_storage import PostgreSQLStorage, DataRecord
from src.core.storage import ConceptStorage
from src.core.query_router import QueryRouter
from src.core.semantic_engine import SemanticEngine


router = APIRouter(prefix="/api/v1", tags=["ConceptDB Phase 1"])

# Shared instances (should be properly initialized in main.py)
pg_storage = PostgreSQLStorage()
concept_storage = ConceptStorage()
semantic_engine = SemanticEngine()
query_router = QueryRouter(pg_storage, concept_storage, semantic_engine)


# Request/Response Models
class UnifiedQueryRequest(BaseModel):
    """Unified query request that can handle SQL or natural language"""
    query: str = Field(..., description="SQL or natural language query")
    prefer_layer: Optional[str] = Field(None, description="Preferred layer: 'postgres', 'concepts', or 'auto'")
    limit: Optional[int] = Field(100, description="Maximum results to return")


class UnifiedQueryResponse(BaseModel):
    """Response from unified query"""
    success: bool
    query: str
    routing_decision: str
    results: List[Dict[str, Any]]
    result_count: int
    confidence_score: float
    response_time_ms: int
    explanation: str


class DataCreateRequest(BaseModel):
    """Request to create data in PostgreSQL layer"""
    type: str = Field(..., description="Type of data record")
    content: Dict[str, Any] = Field(..., description="Data content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    extract_concepts: bool = Field(False, description="Whether to extract concepts immediately")


class DataResponse(BaseModel):
    """Response for data operations"""
    success: bool
    id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    message: str


class ConceptExtractionRequest(BaseModel):
    """Request to extract concepts from existing data"""
    record_ids: Optional[List[str]] = Field(None, description="Specific record IDs to process")
    limit: int = Field(100, description="Maximum records to process")
    
    
class EvolutionMetricsResponse(BaseModel):
    """Evolution metrics response"""
    phase: int
    conceptualization_ratio: float
    total_queries: int
    concept_queries: int
    postgres_queries: int
    hybrid_queries: int
    avg_concept_confidence: Optional[float]
    recommendation: str


# Unified Query Endpoint
@router.post("/query", response_model=UnifiedQueryResponse)
async def unified_query(request: UnifiedQueryRequest):
    """
    Unified query interface that intelligently routes to PostgreSQL (90%) or ConceptDB (10%)
    
    Examples:
    - SQL: "SELECT * FROM data_records WHERE type = 'customer_feedback'"
    - Natural Language: "Find all customer complaints about shipping"
    - Hybrid: Automatically detected and routed to both layers
    """
    try:
        # Override routing if preference specified
        if request.prefer_layer:
            if request.prefer_layer == 'postgres':
                query_router.sql_confidence_threshold = 0.1
            elif request.prefer_layer == 'concepts':
                query_router.semantic_confidence_threshold = 0.1
        
        # Route the query
        result = await query_router.route_query(request.query)
        
        # Limit results if specified
        if request.limit and len(result.merged_results) > request.limit:
            result.merged_results = result.merged_results[:request.limit]
        
        return UnifiedQueryResponse(
            success=True,
            query=request.query,
            routing_decision=result.routing_decision.value,
            results=result.merged_results,
            result_count=len(result.merged_results),
            confidence_score=result.confidence_score,
            response_time_ms=result.response_time_ms,
            explanation=result.explanation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/explain")
async def explain_query_routing(query: str = Query(..., description="Query to explain")):
    """
    Explain how a query would be routed between PostgreSQL and ConceptDB layers
    """
    try:
        explanation = await query_router.explain_routing(query)
        return {
            "success": True,
            "explanation": explanation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# PostgreSQL Data Operations (90% Layer)
@router.post("/data", response_model=DataResponse)
async def create_data(request: DataCreateRequest):
    """
    Create data in PostgreSQL layer (90% of operations)
    """
    try:
        record = DataRecord(
            type=request.type,
            content=request.content,
            metadata=request.metadata
        )
        
        record_id = await pg_storage.create_record(record)
        
        if not record_id:
            return DataResponse(
                success=False,
                message="Failed to create record"
            )
        
        # Optionally extract concepts immediately
        if request.extract_concepts:
            # Extract text from content for concept creation
            text_content = _extract_text_from_content(request.content)
            if text_content:
                vector = semantic_engine.generate_embedding(text_content)
                concept = await concept_storage.create_concept(
                    name=f"{request.type}_{record_id[:8]}",
                    description=text_content[:500],
                    vector=vector,
                    metadata={'source_record_id': record_id, 'type': request.type}
                )
                if concept:
                    await pg_storage.mark_concepts_extracted(record_id, [concept.id])
        
        return DataResponse(
            success=True,
            id=record_id,
            message="Data created successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{record_id}", response_model=DataResponse)
async def get_data(record_id: str):
    """
    Get data from PostgreSQL layer
    """
    try:
        record = await pg_storage.get_record(record_id)
        
        if not record:
            return DataResponse(
                success=False,
                message="Record not found"
            )
        
        return DataResponse(
            success=True,
            id=record.id,
            data={
                'type': record.type,
                'content': record.content,
                'metadata': record.metadata,
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'concept_extracted': record.concept_extracted,
                'concept_ids': record.concept_ids
            },
            message="Data retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/data/{record_id}")
async def update_data(record_id: str, updates: Dict[str, Any]):
    """
    Update data in PostgreSQL layer with ACID guarantees
    """
    try:
        success = await pg_storage.update_record(record_id, updates)
        
        if not success:
            return DataResponse(
                success=False,
                message="Failed to update record"
            )
        
        return DataResponse(
            success=True,
            id=record_id,
            message="Data updated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Concept Operations (10% Layer)
@router.post("/concepts/extract")
async def extract_concepts(request: ConceptExtractionRequest):
    """
    Extract concepts from PostgreSQL data to populate concept layer
    """
    try:
        # Get unprocessed records
        if request.record_ids:
            records = []
            for record_id in request.record_ids:
                record = await pg_storage.get_record(record_id)
                if record:
                    records.append(record)
        else:
            records = await pg_storage.get_unprocessed_records(limit=request.limit)
        
        extracted_count = 0
        failed_count = 0
        
        for record in records:
            try:
                # Extract text content
                text_content = _extract_text_from_content(record.content)
                if not text_content:
                    continue
                
                # Generate embedding
                vector = semantic_engine.generate_embedding(text_content)
                
                # Create concept
                concept = await concept_storage.create_concept(
                    name=f"{record.type}_{record.id[:8]}",
                    description=text_content[:500],
                    vector=vector,
                    metadata={
                        'source_record_id': record.id,
                        'type': record.type,
                        'extracted_from': 'postgres'
                    }
                )
                
                if concept:
                    await pg_storage.mark_concepts_extracted(record.id, [concept.id])
                    extracted_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to extract concept from record {record.id}: {e}")
                failed_count += 1
        
        return {
            "success": True,
            "processed_records": len(records),
            "concepts_extracted": extracted_count,
            "failed": failed_count,
            "message": f"Extracted {extracted_count} concepts from {len(records)} records"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concepts/{concept_id}/evolution")
async def get_concept_evolution(concept_id: str):
    """
    Track how a concept has evolved over time
    """
    try:
        concept = await concept_storage.get_concept(concept_id)
        
        if not concept:
            raise HTTPException(status_code=404, detail="Concept not found")
        
        # Get evolution history (simplified for now)
        evolution = {
            "concept_id": concept_id,
            "name": concept.name,
            "created_at": concept.created_at.isoformat() if concept.created_at else None,
            "usage_count": concept.usage_count,
            "strength": concept.strength,
            "evolution_phases": [
                {
                    "phase": 1,
                    "description": "Initial extraction from PostgreSQL data",
                    "timestamp": concept.created_at.isoformat() if concept.created_at else None
                }
            ],
            "future_phases": [
                {"phase": 2, "description": "30% conceptualization - Enhanced relationships"},
                {"phase": 3, "description": "70% conceptualization - Primary storage"},
                {"phase": 4, "description": "100% conceptualization - Pure concept database"}
            ]
        }
        
        return evolution
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concepts/graph")
async def get_concept_graph(limit: int = 50):
    """
    Get concept relationship graph for visualization
    """
    try:
        # Get concepts
        concepts = await concept_storage.list_concepts(limit=limit)
        
        # Build graph data
        nodes = []
        edges = []
        
        for concept in concepts:
            nodes.append({
                "id": concept.id,
                "label": concept.name,
                "metadata": concept.metadata.dict() if concept.metadata else {},
                "usage_count": concept.usage_count
            })
            
            # Add relationships
            for child_id in concept.child_ids:
                edges.append({
                    "from": concept.id,
                    "to": child_id,
                    "type": "part_of"
                })
            
            for related_id in concept.related_ids:
                edges.append({
                    "from": concept.id,
                    "to": related_id,
                    "type": "related_to"
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Evolution Metrics
@router.get("/metrics/evolution", response_model=EvolutionMetricsResponse)
async def get_evolution_metrics():
    """
    Get current evolution metrics showing progress from 10% to 100% conceptualization
    """
    try:
        metrics = await pg_storage.get_evolution_metrics()
        
        # Generate recommendation based on metrics
        ratio = metrics.get('conceptualization_ratio', 0.1)
        if ratio < 0.15:
            recommendation = "Continue building concept extraction. Focus on high-value data first."
        elif ratio < 0.3:
            recommendation = "Ready to consider Phase 2 (30% conceptualization). Evaluate concept quality."
        elif ratio < 0.7:
            recommendation = "Strong concept adoption. Consider expanding concept operations."
        else:
            recommendation = "High conceptualization achieved. Ready for Phase 4 transition planning."
        
        return EvolutionMetricsResponse(
            phase=metrics.get('phase', 1),
            conceptualization_ratio=ratio,
            total_queries=metrics.get('total_queries', 0),
            concept_queries=metrics.get('concept_queries', 0),
            postgres_queries=metrics.get('postgres_queries', 0),
            hybrid_queries=metrics.get('hybrid_queries', 0),
            avg_concept_confidence=metrics.get('avg_concept_confidence'),
            recommendation=recommendation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/routing")
async def get_routing_statistics(hours: int = 24):
    """
    Get query routing statistics for the specified time period
    """
    try:
        query = f"""
            SELECT 
                routed_to,
                COUNT(*) as count,
                AVG(confidence_score) as avg_confidence,
                AVG(response_time_ms) as avg_response_time,
                AVG(result_count) as avg_results
            FROM query_routing_stats
            WHERE created_at > NOW() - INTERVAL '{hours} hours'
            GROUP BY routed_to
        """
        
        stats = await pg_storage.execute_sql(query)
        
        return {
            "success": True,
            "period_hours": hours,
            "routing_stats": stats,
            "summary": {
                "total_queries": sum(s['count'] for s in stats),
                "postgres_percentage": next((s['count'] for s in stats if s['routed_to'] == 'postgres'), 0) / max(sum(s['count'] for s in stats), 1) * 100,
                "concept_percentage": next((s['count'] for s in stats if s['routed_to'] == 'concepts'), 0) / max(sum(s['count'] for s in stats), 1) * 100
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolve")
async def trigger_evolution(target_phase: int = 2):
    """
    Trigger evolution to the next phase (for demonstration purposes)
    """
    if target_phase not in [2, 3, 4]:
        raise HTTPException(status_code=400, detail="Invalid target phase. Must be 2, 3, or 4")
    
    phase_descriptions = {
        2: "30% conceptualization - Hybrid storage with intelligent routing",
        3: "70% conceptualization - Concept-first with PostgreSQL backup",
        4: "100% conceptualization - Pure concept database"
    }
    
    return {
        "success": True,
        "current_phase": 1,
        "target_phase": target_phase,
        "description": phase_descriptions[target_phase],
        "status": "Evolution planning initiated",
        "next_steps": [
            "Evaluate current concept quality",
            "Plan data migration strategy",
            "Update routing algorithms",
            "Adjust conceptualization ratio"
        ]
    }


# Helper functions
def _extract_text_from_content(content: Dict[str, Any]) -> str:
    """Extract text from various content formats"""
    text_parts = []
    
    # Direct text field
    if 'text' in content:
        text_parts.append(str(content['text']))
    
    # Description field
    if 'description' in content:
        text_parts.append(str(content['description']))
    
    # Name field
    if 'name' in content:
        text_parts.append(str(content['name']))
    
    # Title field
    if 'title' in content:
        text_parts.append(str(content['title']))
    
    # Concatenate all text parts
    return ' '.join(text_parts)


from loguru import logger  # Add this import