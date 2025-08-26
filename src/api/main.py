"""
ConceptDB API Server
FastAPI implementation for Phase 1 (10% Concepts + 90% PostgreSQL)
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
import logging
import os

from pydantic import BaseModel

# Import core components
from src.core.pg_storage import PostgreSQLStorage
from src.core.query_router import QueryRouter
from src.core.concept_manager import ConceptManager
from src.core.evolution_tracker import EvolutionTracker

# Try to import advanced components, fallback to simple versions
try:
    from src.core.vector_store import QdrantStore as VectorStore
    from src.core.semantic_engine import SemanticEngine
except ImportError:
    logger.warning("Using simple vector store and semantic engine (production mode)")
    from src.core.simple_vector_store import SimpleVectorStore as VectorStore
    from src.core.simple_semantic_engine import SimpleSemanticEngine as SemanticEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
pg_storage: Optional[PostgreSQLStorage] = None
vector_store: Optional[Any] = None  # Can be QdrantStore or SimpleVectorStore
semantic_engine: Optional[Any] = None  # Can be SemanticEngine or SimpleSemanticEngine
query_router: Optional[QueryRouter] = None
concept_manager: Optional[ConceptManager] = None
evolution_tracker: Optional[EvolutionTracker] = None


# Request/Response Models
class QueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    
class ConceptCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}
    
class ConceptExtractRequest(BaseModel):
    text: str
    min_confidence: Optional[float] = 0.5
    
class ConceptSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    min_score: Optional[float] = 0.5
    
class DataRequest(BaseModel):
    table: str
    data: Dict[str, Any]
    
class EvolveRequest(BaseModel):
    target_phase: Optional[int] = None
    force: Optional[bool] = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global pg_storage, vector_store, semantic_engine
    global query_router, concept_manager, evolution_tracker
    
    # Startup
    logger.info("Starting ConceptDB API Server...")
    
    # Initialize PostgreSQL
    # Support both DATABASE_URL (Render) and POSTGRES_URL
    pg_url = os.getenv("DATABASE_URL") or os.getenv(
        "POSTGRES_URL", 
        "postgresql://concept_user:concept_pass@localhost:5433/conceptdb"
    )
    pg_storage = PostgreSQLStorage(pg_url)
    await pg_storage.connect()
    
    # Initialize Vector Store (Qdrant or Simple)
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    use_simple = os.getenv("USE_SIMPLE_VECTOR", "true").lower() == "true"
    
    if use_simple or "render.com" in os.getenv("RENDER_EXTERNAL_HOSTNAME", ""):
        # Use simple vector store for production/Render
        vector_store = VectorStore()
    else:
        # Use Qdrant for local development
        vector_store = VectorStore(qdrant_url)
    
    await vector_store.initialize()
    
    # Initialize Semantic Engine
    semantic_engine = SemanticEngine()
    
    # Initialize Query Router
    query_router = QueryRouter(
        pg_storage=pg_storage,
        vector_store=vector_store,
        semantic_engine=semantic_engine,
        concept_threshold=0.8
    )
    
    # Initialize Concept Manager
    concept_manager = ConceptManager(
        vector_store=vector_store,
        semantic_engine=semantic_engine,
        pg_storage=pg_storage
    )
    
    # Initialize Evolution Tracker
    evolution_tracker = EvolutionTracker(
        pg_storage=pg_storage
    )
    
    logger.info("ConceptDB API Server initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down ConceptDB API Server...")
    await pg_storage.disconnect()
    logger.info("ConceptDB API Server shut down")


# Create FastAPI app
app = FastAPI(
    title="ConceptDB API",
    description="Evolutionary Concept-Type Database - Phase 1 (10% Concepts + 90% PostgreSQL)",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Check if all services are healthy"""
    pg_healthy = await pg_storage.health_check() if pg_storage else False
    qdrant_healthy = await vector_store.health_check() if vector_store else False
    
    return {
        "status": "healthy" if (pg_healthy and qdrant_healthy) else "unhealthy",
        "services": {
            "postgresql": pg_healthy,
            "qdrant": qdrant_healthy,
            "api": True
        },
        "phase": 1,
        "conceptualization_ratio": 0.1
    }


# ==================== Unified Query Interface ====================

@app.post("/api/v1/query")
async def unified_query(request: QueryRequest):
    """
    Intelligent query routing - accepts both SQL and natural language
    Routes to appropriate layer based on confidence
    """
    try:
        result = await query_router.route_query(request.query)
        
        # Limit results if requested
        if request.limit and result.get('results'):
            result['results'] = result['results'][:request.limit]
            
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/query/explain")
async def explain_query(query: str):
    """
    Explain how a query would be routed without executing it
    """
    try:
        # Analyze query without execution
        from src.core.query_router import QueryType
        
        query_lower = query.lower()
        
        # Simple analysis for explanation
        has_sql = any(kw in query_lower for kw in ['select', 'from', 'where'])
        has_semantic = any(kw in query_lower for kw in ['similar', 'like', 'related'])
        
        if has_sql and not has_semantic:
            route = "postgres"
            explanation = "SQL structure detected, will route to PostgreSQL"
            confidence = 0.95
        elif has_semantic and not has_sql:
            route = "concepts"
            explanation = "Semantic keywords detected, will route to Concept Layer"
            confidence = 0.85
        elif has_sql and has_semantic:
            route = "both"
            explanation = "Hybrid query detected, will check both layers"
            confidence = 0.7
        else:
            route = "postgres"
            explanation = "Standard query, will default to PostgreSQL"
            confidence = 0.6
            
        return {
            "success": True,
            "data": {
                "query": query,
                "predicted_route": route,
                "confidence": confidence,
                "explanation": explanation
            }
        }
    except Exception as e:
        logger.error(f"Explain failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Precise Data Operations (90%) ====================

@app.post("/api/v1/data")
async def create_data(request: DataRequest):
    """Create data in PostgreSQL with ACID guarantees"""
    try:
        # Build INSERT query
        columns = list(request.data.keys())
        values = list(request.data.values())
        placeholders = [f"${i+1}" for i in range(len(values))]
        
        query = f"""
        INSERT INTO {request.table} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        RETURNING *
        """
        
        result = await pg_storage.execute_query(query, values)
        
        # Extract concepts from new data
        # TODO: Implement automatic concept extraction from table data
        # if result:
        #     await concept_manager.extract_from_data(
        #         table=request.table,
        #         data=result[0]
        #     )
        
        return {
            "success": True,
            "data": result[0] if result else None
        }
    except Exception as e:
        logger.error(f"Data creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/data/{table}/{id}")
async def get_data(table: str, id: int):
    """Fetch precise data from PostgreSQL"""
    try:
        query = f"SELECT * FROM {table} WHERE id = $1"
        result = await pg_storage.execute_query(query, [id])
        
        if not result:
            raise HTTPException(status_code=404, detail="Data not found")
            
        return {
            "success": True,
            "data": result[0]
        }
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/data/{table}/{id}")
async def update_data(table: str, id: int, data: Dict[str, Any]):
    """Update data with ACID guarantees"""
    try:
        # Build UPDATE query
        set_clauses = [f"{k} = ${i+2}" for i, k in enumerate(data.keys())]
        values = [id] + list(data.values())
        
        query = f"""
        UPDATE {table}
        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        RETURNING *
        """
        
        result = await pg_storage.execute_query(query, values)
        
        if not result:
            raise HTTPException(status_code=404, detail="Data not found")
            
        # Update concepts if needed
        await concept_manager.update_from_data(
            table=table,
            data=result[0]
        )
        
        return {
            "success": True,
            "data": result[0]
        }
    except Exception as e:
        logger.error(f"Data update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Concept Operations (10%) ====================

@app.post("/api/v1/concepts")
async def create_concept(request: ConceptCreateRequest):
    """Create a new concept"""
    try:
        concept_id = await concept_manager.create_concept(
            name=request.name,
            description=request.description,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "data": {
                "id": concept_id,
                "name": request.name
            }
        }
    except Exception as e:
        logger.error(f"Concept creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/concepts/extract")
async def extract_concepts(request: ConceptExtractRequest):
    """Auto-extract concepts from text"""
    try:
        concepts = await concept_manager.extract_concepts_from_text(
            text=request.text,
            min_confidence=request.min_confidence
        )
        
        return {
            "success": True,
            "data": {
                "concepts": concepts,
                "count": len(concepts)
            }
        }
    except Exception as e:
        logger.error(f"Concept extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/concepts/search")
async def search_concepts(request: ConceptSearchRequest):
    """Semantic search for concepts"""
    try:
        results = await concept_manager.find_similar_concepts(
            query=request.query,
            limit=request.limit,
            min_score=request.min_score
        )
        
        return {
            "success": True,
            "data": {
                "results": results,
                "count": len(results)
            }
        }
    except Exception as e:
        logger.error(f"Concept search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/concepts/{concept_id}/evolution")
async def get_concept_evolution(concept_id: str):
    """Track how a concept has evolved over time"""
    try:
        evolution = await evolution_tracker.get_concept_evolution(concept_id)
        
        return {
            "success": True,
            "data": evolution
        }
    except Exception as e:
        logger.error(f"Evolution fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/concepts/graph")
async def get_concept_graph(limit: int = 100):
    """Get concept relationship graph for visualization"""
    try:
        graph = await concept_manager.get_relationship_graph(limit=limit)
        
        return {
            "success": True,
            "data": graph
        }
    except Exception as e:
        logger.error(f"Graph fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Evolution Metrics ====================

@app.get("/api/v1/metrics/evolution")
async def get_evolution_metrics():
    """Get current conceptualization percentage and phase"""
    try:
        metrics = await pg_storage.get_evolution_metrics()
        
        # Add routing statistics
        routing_stats = await query_router.get_routing_stats()
        metrics.update(routing_stats)
        
        # Determine if ready for next phase
        metrics['next_phase_ready'] = metrics.get('concept_percentage', 0) >= 25
        metrics['recommended_action'] = (
            "Ready to evolve to Phase 2 (30% conceptualization)" 
            if metrics['next_phase_ready'] 
            else f"Continue building concept layer ({metrics.get('concept_percentage', 0):.1f}% complete)"
        )
        
        return {
            "success": True,
            "data": metrics
        }
    except Exception as e:
        logger.error(f"Metrics fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/metrics/routing")
async def get_routing_metrics():
    """Get query routing statistics"""
    try:
        stats = await query_router.get_routing_stats()
        
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Routing metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/evolve")
async def trigger_evolution(request: EvolveRequest):
    """
    Trigger evolution to next phase
    This would be a major operation in production
    """
    try:
        current_metrics = await pg_storage.get_evolution_metrics()
        current_phase = current_metrics.get('current_phase', 1)
        
        # Check if ready for evolution
        if not request.force:
            concept_percentage = current_metrics.get('concept_percentage', 0)
            if concept_percentage < 25:
                return {
                    "success": False,
                    "message": f"Not ready for evolution. Concept usage at {concept_percentage:.1f}%, need 25%",
                    "data": current_metrics
                }
        
        # Determine target phase
        target_phase = request.target_phase or (current_phase + 1)
        
        if target_phase > 4:
            return {
                "success": False,
                "message": "Already at maximum evolution (Phase 4)",
                "data": current_metrics
            }
        
        # Simulate evolution (would be complex in production)
        evolution_result = await evolution_tracker.evolve_to_phase(target_phase)
        
        return {
            "success": True,
            "message": f"Evolved from Phase {current_phase} to Phase {target_phase}",
            "data": evolution_result
        }
    except Exception as e:
        logger.error(f"Evolution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Root endpoint
@app.get("/")
async def root():
    """API root with basic information"""
    return {
        "name": "ConceptDB API",
        "version": "0.1.0",
        "phase": 1,
        "description": "Evolutionary Concept-Type Database",
        "conceptualization": "10%",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )