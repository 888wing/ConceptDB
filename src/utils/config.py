"""Configuration management for ConceptDB"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_config() -> Dict[str, Any]:
    """Get configuration from environment variables"""
    
    return {
        # Qdrant Configuration
        "qdrant": {
            "host": os.getenv("QDRANT_HOST", "localhost"),
            "port": int(os.getenv("QDRANT_PORT", "6333")),
            "collection_name": os.getenv("QDRANT_COLLECTION_NAME", "concepts"),
            "grpc_port": int(os.getenv("QDRANT_GRPC_PORT", "6334"))
        },
        
        # Database Configuration
        "database": {
            "path": os.getenv("DATABASE_PATH", "./data/concepts.db")
        },
        
        # API Configuration
        "api": {
            "host": os.getenv("API_HOST", "0.0.0.0"),
            "port": int(os.getenv("API_PORT", "8000")),
            "prefix": os.getenv("API_PREFIX", "/api/v1")
        },
        
        # Model Configuration
        "model": {
            "name": os.getenv("MODEL_NAME", "all-MiniLM-L6-v2"),
            "cache_dir": os.getenv("MODEL_CACHE_DIR", "./models"),
            "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", "384"))
        },
        
        # Semantic Search Configuration
        "search": {
            "similarity_threshold": float(os.getenv("SIMILARITY_THRESHOLD", "0.7")),
            "max_results": int(os.getenv("MAX_SEARCH_RESULTS", "10")),
            "min_confidence": float(os.getenv("MIN_CONFIDENCE_SCORE", "0.5"))
        },
        
        # Performance Configuration
        "performance": {
            "max_concepts": int(os.getenv("MAX_CONCEPTS", "10000")),
            "batch_size": int(os.getenv("BATCH_SIZE", "100")),
            "cache_ttl": int(os.getenv("CACHE_TTL", "3600")),
            "connection_pool_size": int(os.getenv("CONNECTION_POOL_SIZE", "10"))
        },
        
        # Logging Configuration
        "logging": {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "file": os.getenv("LOG_FILE", "./logs/conceptdb.log")
        },
        
        # UI Configuration
        "ui": {
            "port": int(os.getenv("STREAMLIT_PORT", "8501")),
            "theme": os.getenv("STREAMLIT_THEME", "light")
        }
    }