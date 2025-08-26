#!/usr/bin/env python3
"""Simple test API server for ConceptDB"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules directly
from src.core.pg_storage import PostgreSQLStorage, PGConfig, DataRecord
from src.core.query_router import QueryRouter

app = FastAPI(
    title="ConceptDB API",
    description="Phase 1: 10% Concept Layer + 90% PostgreSQL",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage instances
pg_storage = None
query_router = None

class QueryRequest(BaseModel):
    query: str
    options: Optional[Dict[str, Any]] = {}

class DataCreateRequest(BaseModel):
    type: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize storage on startup"""
    global pg_storage, query_router
    
    config = PGConfig(
        host="localhost",
        port=5433,
        database="conceptdb",
        user="concept_user",
        password="concept_pass"
    )
    
    pg_storage = PostgreSQLStorage(config)
    await pg_storage.initialize()
    
    # Create query router (without ML components for now)
    query_router = QueryRouter(pg_storage, None, None)
    
    print("✅ ConceptDB API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if pg_storage:
        await pg_storage.close()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "ConceptDB",
        "version": "0.1.0",
        "phase": 1,
        "conceptualization_ratio": 0.1,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ConceptDB API"}

@app.post("/api/v1/query")
async def execute_query(request: QueryRequest):
    """Execute a query with intelligent routing"""
    try:
        # Analyze the query
        analysis = query_router.analyze_query(request.query)
        
        # For now, return the analysis
        return {
            "success": True,
            "query": request.query,
            "analysis": {
                "type": analysis.query_type.value,
                "has_sql": analysis.has_sql_keywords,
                "has_semantic": analysis.has_semantic_intent,
                "confidence": analysis.confidence_score,
                "routing": analysis.suggested_routing.value
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/query/explain")
async def explain_query(query: str):
    """Explain how a query would be routed"""
    try:
        explanation = await query_router.explain_routing(query)
        return {
            "success": True,
            "explanation": explanation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/data")
async def create_data(request: DataCreateRequest):
    """Create a new data record"""
    try:
        record = DataRecord(
            type=request.type,
            content=request.content,
            metadata=request.metadata
        )
        
        record_id = await pg_storage.create_record(record)
        
        return {
            "success": True,
            "id": record_id,
            "message": "Record created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/data/{record_id}")
async def get_data(record_id: str):
    """Get a data record by ID"""
    try:
        record = await pg_storage.get_record(record_id)
        
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        return {
            "success": True,
            "record": {
                "id": record.id,
                "type": record.type,
                "content": record.content,
                "metadata": record.metadata,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "concept_extracted": record.concept_extracted
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics/evolution")
async def get_evolution_metrics():
    """Get current evolution metrics"""
    try:
        metrics = await pg_storage.get_evolution_metrics()
        return {
            "success": True,
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics/routing")
async def get_routing_stats():
    """Get query routing statistics"""
    try:
        # Get recent routing stats
        stats = await pg_storage.execute_sql("""
            SELECT 
                query_type,
                routed_to,
                COUNT(*) as count,
                AVG(confidence_score) as avg_confidence,
                AVG(response_time_ms) as avg_response_time
            FROM query_routing_stats
            WHERE created_at > NOW() - INTERVAL '1 hour'
            GROUP BY query_type, routed_to
            ORDER BY count DESC
        """)
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)