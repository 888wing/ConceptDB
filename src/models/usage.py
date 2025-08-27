"""
Usage and Quota Models
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class MetricType(str, Enum):
    """Types of usage metrics"""
    CONCEPTS = "concepts"
    QUERIES = "queries"
    API_CALLS = "api_calls"
    STORAGE_GB = "storage_gb"
    VECTOR_OPERATIONS = "vector_operations"


class UsageMetric(BaseModel):
    """Usage metric model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    
    # Metric details
    metric_type: MetricType
    value: float
    
    # Time window
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Metadata
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        orm_mode = True


class Quota(BaseModel):
    """Quota limits for organization"""
    organization_id: str
    
    # Phase 1 limits (Free tier defaults)
    max_concepts: int = 100000
    max_queries_per_month: int = 100000
    max_api_calls_per_month: int = 100000
    max_storage_gb: float = 1.0
    max_concurrent_connections: int = 10
    max_evolution_phase: int = 1  # Phase 1 for free users
    
    # Rate limits
    max_queries_per_minute: int = 100
    max_api_calls_per_second: int = 10
    
    # Advanced features (Pro/Enterprise)
    custom_models_enabled: bool = False
    sso_enabled: bool = False
    audit_logs_enabled: bool = False
    white_labeling_enabled: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class UsageSnapshot(BaseModel):
    """Current usage snapshot for organization"""
    organization_id: str
    snapshot_time: datetime = Field(default_factory=datetime.utcnow)
    
    # Current usage
    concepts_count: int = 0
    queries_this_month: int = 0
    api_calls_this_month: int = 0
    storage_gb_used: float = 0.0
    concurrent_connections: int = 0
    
    # Quota limits
    max_concepts: int
    max_queries_per_month: int
    max_api_calls_per_month: int
    max_storage_gb: float
    max_concurrent_connections: int
    
    # Usage percentages
    concepts_usage_pct: float = 0.0
    queries_usage_pct: float = 0.0
    api_calls_usage_pct: float = 0.0
    storage_usage_pct: float = 0.0
    
    def calculate_percentages(self):
        """Calculate usage percentages"""
        if self.max_concepts > 0:
            self.concepts_usage_pct = (self.concepts_count / self.max_concepts) * 100
        if self.max_queries_per_month > 0:
            self.queries_usage_pct = (self.queries_this_month / self.max_queries_per_month) * 100
        if self.max_api_calls_per_month > 0:
            self.api_calls_usage_pct = (self.api_calls_this_month / self.max_api_calls_per_month) * 100
        if self.max_storage_gb > 0:
            self.storage_usage_pct = (self.storage_gb_used / self.max_storage_gb) * 100


class QuotaExceeded(Exception):
    """Exception raised when quota is exceeded"""
    def __init__(self, metric_type: str, current: float, limit: float):
        self.metric_type = metric_type
        self.current = current
        self.limit = limit
        super().__init__(f"Quota exceeded for {metric_type}: {current}/{limit}")


class UsageAlert(BaseModel):
    """Usage alert model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    
    # Alert details
    metric_type: MetricType
    threshold_percentage: float  # e.g., 80 for 80%
    current_usage: float
    limit: float
    
    # Status
    is_resolved: bool = False
    notified_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True