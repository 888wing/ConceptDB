"""Logging configuration for ConceptDB"""

import sys
import os
from loguru import logger


def setup_logger():
    """Setup loguru logger with custom configuration"""
    
    # Remove default handler
    logger.remove()
    
    # Get log level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "./logs/conceptdb.log")
    
    # Console handler with color
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File handler
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days",
            compression="zip"
        )
    
    return logger