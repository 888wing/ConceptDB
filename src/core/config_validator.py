"""Configuration validation for ConceptDB deployment"""

import os
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates configuration and environment variables on startup"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def validate_all(self) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Validate all configuration settings
        
        Returns:
            Tuple of (is_valid, messages_dict)
        """
        self.errors = []
        self.warnings = []
        self.info = []
        
        # Check database configuration
        self._validate_database()
        
        # Check Qdrant configuration
        self._validate_qdrant()
        
        # Check authentication configuration
        self._validate_auth()
        
        # Check Zeabur-specific configuration
        self._validate_zeabur()
        
        # Check optional performance settings
        self._validate_performance()
        
        # Log validation results
        for error in self.errors:
            logger.error(f"Config Error: {error}")
        for warning in self.warnings:
            logger.warning(f"Config Warning: {warning}")
        for info in self.info:
            logger.info(f"Config Info: {info}")
        
        is_valid = len(self.errors) == 0
        
        return is_valid, {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info
        }
    
    def _validate_database(self):
        """Validate database configuration"""
        db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        
        if not db_url:
            self.warnings.append("No DATABASE_URL or POSTGRES_URL configured, will use SQLite")
        else:
            if db_url.startswith("postgresql://"):
                self.info.append(f"PostgreSQL configured")
                # Check if connection string has all required parts
                if "@" not in db_url or "/" not in db_url.split("@")[-1]:
                    self.errors.append("Invalid PostgreSQL connection string format")
            elif db_url.startswith("sqlite://"):
                self.info.append("SQLite configured")
            else:
                self.errors.append(f"Unknown database type in URL: {db_url[:20]}...")
    
    def _validate_qdrant(self):
        """Validate Qdrant configuration"""
        use_simple = os.getenv("USE_SIMPLE_VECTOR", "true").lower() == "true"
        is_zeabur = "ZEABUR" in os.environ or "zeabur" in os.getenv("ENVIRONMENT", "").lower()
        
        if use_simple and not is_zeabur:
            self.info.append("Using simple vector store (no Qdrant required)")
            return
        
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url:
            self.warnings.append("QDRANT_URL not set, will use default http://localhost:6333")
        else:
            self.info.append(f"Qdrant URL configured: {qdrant_url}")
        
        # Check if Qdrant requires API key
        if is_zeabur:
            if not qdrant_api_key:
                self.warnings.append(
                    "QDRANT_API_KEY not set on Zeabur - Qdrant may require authentication. "
                    "Set QDRANT_API_KEY in ConceptDB service and QDRANT__SERVICE__API_KEY in Qdrant service."
                )
            else:
                self.info.append("Qdrant API key configured for Zeabur deployment")
        
        # Validate timeout
        timeout = os.getenv("QDRANT_TIMEOUT", "30")
        try:
            int(timeout)
            self.info.append(f"Qdrant timeout: {timeout}s")
        except ValueError:
            self.errors.append(f"Invalid QDRANT_TIMEOUT value: {timeout}")
    
    def _validate_auth(self):
        """Validate authentication configuration"""
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        
        if not jwt_secret:
            self.warnings.append("JWT_SECRET_KEY not set - authentication will not work properly")
        elif len(jwt_secret) < 32:
            self.warnings.append("JWT_SECRET_KEY is too short (< 32 chars) - consider using a stronger key")
        else:
            self.info.append("JWT authentication configured")
    
    def _validate_zeabur(self):
        """Validate Zeabur-specific configuration"""
        is_zeabur = "ZEABUR" in os.environ or "zeabur" in os.getenv("ENVIRONMENT", "").lower()
        
        if is_zeabur:
            self.info.append("Running on Zeabur platform")
            
            # Check for Zeabur-specific requirements
            if not os.getenv("QDRANT_URL"):
                self.warnings.append(
                    "On Zeabur but QDRANT_URL not set - should be http://qdrant.zeabur.internal:6333"
                )
            
            # Check evolution phase
            phase = os.getenv("EVOLUTION_PHASE", "1")
            ratio = os.getenv("CONCEPT_RATIO", "0.1")
            self.info.append(f"Evolution phase: {phase}, Concept ratio: {ratio}")
    
    def _validate_performance(self):
        """Validate performance configuration"""
        # Check database pool settings
        pool_size = os.getenv("DB_POOL_SIZE", "10")
        max_overflow = os.getenv("DB_MAX_OVERFLOW", "20")
        
        try:
            int(pool_size)
            int(max_overflow)
            self.info.append(f"DB Pool: size={pool_size}, max_overflow={max_overflow}")
        except ValueError:
            self.warnings.append(f"Invalid DB pool settings: size={pool_size}, overflow={max_overflow}")
        
        # Check vector batch size
        batch_size = os.getenv("VECTOR_BATCH_SIZE", "100")
        try:
            int(batch_size)
            self.info.append(f"Vector batch size: {batch_size}")
        except ValueError:
            self.warnings.append(f"Invalid VECTOR_BATCH_SIZE: {batch_size}")


def validate_config_on_startup() -> bool:
    """
    Validate configuration on application startup
    
    Returns:
        True if configuration is valid, False otherwise
    """
    validator = ConfigValidator()
    is_valid, messages = validator.validate_all()
    
    if not is_valid:
        logger.error("=" * 60)
        logger.error("CONFIGURATION VALIDATION FAILED")
        logger.error("=" * 60)
        for error in messages["errors"]:
            logger.error(f"  ❌ {error}")
        logger.error("=" * 60)
        logger.error("Please fix the above configuration errors before starting")
        logger.error("=" * 60)
    else:
        logger.info("=" * 60)
        logger.info("Configuration validation successful")
        logger.info("=" * 60)
    
    return is_valid