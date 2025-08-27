"""
Quota Service
Manages usage quotas and tracks resource consumption
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from src.models.usage import (
    Quota, UsageMetric, UsageSnapshot, 
    QuotaExceeded, UsageAlert, MetricType
)

logger = logging.getLogger(__name__)


class QuotaService:
    """Service for managing quotas and usage tracking"""
    
    def __init__(self, storage=None, redis_client=None):
        self.storage = storage  # PostgreSQL for persistent storage
        self.redis = redis_client  # Redis for fast quota checks
        
    async def initialize_organization_quota(self, organization_id: str, plan: str = "free") -> Quota:
        """Initialize quota for a new organization"""
        
        # Create quota based on plan
        quota = Quota(
            organization_id=organization_id,
            max_concepts=100000 if plan == "free" else 1000000,
            max_queries_per_month=100000 if plan == "free" else 1000000,
            max_api_calls_per_month=100000 if plan == "free" else 1000000,
            max_storage_gb=1.0 if plan == "free" else 10.0,
            max_concurrent_connections=10 if plan == "free" else 100,
            max_evolution_phase=1 if plan == "free" else 4,
            custom_models_enabled=plan == "enterprise",
            sso_enabled=plan == "enterprise",
            audit_logs_enabled=plan in ["professional", "enterprise"],
            white_labeling_enabled=plan == "enterprise"
        )
        
        if self.storage:
            # Save to database
            await self.storage.execute_query(
                """
                INSERT INTO quotas (
                    organization_id, max_concepts, max_queries_per_month,
                    max_api_calls_per_month, max_storage_gb, max_concurrent_connections,
                    max_evolution_phase, max_queries_per_minute, max_api_calls_per_second,
                    custom_models_enabled, sso_enabled, audit_logs_enabled,
                    white_labeling_enabled, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (organization_id) DO UPDATE SET
                    max_concepts = EXCLUDED.max_concepts,
                    max_queries_per_month = EXCLUDED.max_queries_per_month,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [
                    quota.organization_id, quota.max_concepts, quota.max_queries_per_month,
                    quota.max_api_calls_per_month, quota.max_storage_gb, quota.max_concurrent_connections,
                    quota.max_evolution_phase, quota.max_queries_per_minute, quota.max_api_calls_per_second,
                    quota.custom_models_enabled, quota.sso_enabled, quota.audit_logs_enabled,
                    quota.white_labeling_enabled, quota.created_at
                ]
            )
        
        # Cache in Redis for fast access
        if self.redis:
            await self._cache_quota(quota)
        
        return quota
    
    async def get_quota(self, organization_id: str) -> Optional[Quota]:
        """Get quota for an organization"""
        
        # Try Redis first
        if self.redis:
            cached = await self._get_cached_quota(organization_id)
            if cached:
                return cached
        
        # Fall back to database
        if self.storage:
            result = await self.storage.execute_query(
                "SELECT * FROM quotas WHERE organization_id = $1",
                [organization_id]
            )
            
            if result:
                quota = Quota(**result[0])
                
                # Cache it
                if self.redis:
                    await self._cache_quota(quota)
                
                return quota
        
        return None
    
    async def update_quota(self, organization_id: str, updates: Dict[str, Any]) -> Quota:
        """Update quota limits for an organization"""
        
        if self.storage:
            # Build UPDATE query
            set_clauses = [f"{k} = ${i+2}" for i, k in enumerate(updates.keys())]
            values = [organization_id] + list(updates.values())
            
            query = f"""
            UPDATE quotas 
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE organization_id = $1
            RETURNING *
            """
            
            result = await self.storage.execute_query(query, values)
            
            if result:
                quota = Quota(**result[0])
                
                # Update cache
                if self.redis:
                    await self._cache_quota(quota)
                
                return quota
        
        raise ValueError("Quota not found")
    
    async def track_usage(
        self,
        organization_id: str,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Track usage of a specific metric"""
        
        # Create usage metric
        metric = UsageMetric(
            organization_id=organization_id,
            metric_type=metric_type,
            value=value,
            metadata=metadata or {}
        )
        
        if self.storage:
            # Save to database
            await self.storage.execute_query(
                """
                INSERT INTO usage_metrics (
                    id, organization_id, metric_type, value, 
                    timestamp, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                [
                    metric.id, metric.organization_id, metric.metric_type.value,
                    metric.value, metric.timestamp, metric.metadata
                ]
            )
        
        # Update Redis counters for real-time checks
        if self.redis:
            await self._update_redis_counter(organization_id, metric_type, value)
        
        # Check if alerts need to be created
        await self._check_and_create_alerts(organization_id, metric_type)
        
        return True
    
    async def check_quota(
        self,
        organization_id: str,
        metric_type: MetricType,
        requested_amount: float = 1
    ) -> bool:
        """Check if an operation is within quota limits"""
        
        # Get current quota
        quota = await self.get_quota(organization_id)
        if not quota:
            # No quota means free tier defaults
            quota = await self.initialize_organization_quota(organization_id)
        
        # Get current usage
        usage = await self.get_current_usage(organization_id, metric_type)
        
        # Check against limits
        if metric_type == MetricType.CONCEPTS:
            return usage + requested_amount <= quota.max_concepts
        elif metric_type == MetricType.QUERIES:
            return usage + requested_amount <= quota.max_queries_per_month
        elif metric_type == MetricType.API_CALLS:
            return usage + requested_amount <= quota.max_api_calls_per_month
        elif metric_type == MetricType.STORAGE_GB:
            return usage + requested_amount <= quota.max_storage_gb
        
        return True
    
    async def enforce_quota(
        self,
        organization_id: str,
        metric_type: MetricType,
        requested_amount: float = 1
    ):
        """Enforce quota limits, raising exception if exceeded"""
        
        quota = await self.get_quota(organization_id)
        if not quota:
            quota = await self.initialize_organization_quota(organization_id)
        
        usage = await self.get_current_usage(organization_id, metric_type)
        
        # Check and raise if exceeded
        limit = 0
        if metric_type == MetricType.CONCEPTS:
            limit = quota.max_concepts
        elif metric_type == MetricType.QUERIES:
            limit = quota.max_queries_per_month
        elif metric_type == MetricType.API_CALLS:
            limit = quota.max_api_calls_per_month
        elif metric_type == MetricType.STORAGE_GB:
            limit = quota.max_storage_gb
        
        if usage + requested_amount > limit:
            raise QuotaExceeded(
                metric_type=metric_type.value,
                current=usage,
                limit=limit
            )
    
    async def get_current_usage(
        self,
        organization_id: str,
        metric_type: Optional[MetricType] = None
    ) -> float:
        """Get current usage for a specific metric or all metrics"""
        
        # Try Redis first for real-time data
        if self.redis:
            cached = await self._get_redis_usage(organization_id, metric_type)
            if cached is not None:
                return cached
        
        # Fall back to database
        if self.storage:
            # For monthly metrics, only count current month
            if metric_type in [MetricType.QUERIES, MetricType.API_CALLS]:
                start_of_month = datetime.utcnow().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                
                result = await self.storage.execute_query(
                    """
                    SELECT SUM(value) as total
                    FROM usage_metrics
                    WHERE organization_id = $1
                    AND metric_type = $2
                    AND timestamp >= $3
                    """,
                    [organization_id, metric_type.value, start_of_month]
                )
                
                if result and result[0]["total"]:
                    return float(result[0]["total"])
            else:
                # For cumulative metrics (concepts, storage)
                result = await self.storage.execute_query(
                    """
                    SELECT value
                    FROM usage_metrics
                    WHERE organization_id = $1
                    AND metric_type = $2
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    [organization_id, metric_type.value if metric_type else None]
                )
                
                if result:
                    return float(result[0]["value"])
        
        return 0.0
    
    async def get_usage_snapshot(self, organization_id: str) -> UsageSnapshot:
        """Get complete usage snapshot for organization"""
        
        # Get quota
        quota = await self.get_quota(organization_id)
        if not quota:
            quota = await self.initialize_organization_quota(organization_id)
        
        # Get current usage for all metrics
        concepts = await self.get_current_usage(organization_id, MetricType.CONCEPTS)
        queries = await self.get_current_usage(organization_id, MetricType.QUERIES)
        api_calls = await self.get_current_usage(organization_id, MetricType.API_CALLS)
        storage = await self.get_current_usage(organization_id, MetricType.STORAGE_GB)
        
        # Get concurrent connections from Redis or estimate
        connections = 0
        if self.redis:
            connections = await self._get_redis_connections(organization_id)
        
        # Create snapshot
        snapshot = UsageSnapshot(
            organization_id=organization_id,
            concepts_count=int(concepts),
            queries_this_month=int(queries),
            api_calls_this_month=int(api_calls),
            storage_gb_used=storage,
            concurrent_connections=connections,
            max_concepts=quota.max_concepts,
            max_queries_per_month=quota.max_queries_per_month,
            max_api_calls_per_month=quota.max_api_calls_per_month,
            max_storage_gb=quota.max_storage_gb,
            max_concurrent_connections=quota.max_concurrent_connections
        )
        
        # Calculate percentages
        snapshot.calculate_percentages()
        
        return snapshot
    
    async def reset_monthly_usage(self, organization_id: Optional[str] = None):
        """Reset monthly usage counters (called by cron job)"""
        
        if self.storage:
            if organization_id:
                # Reset for specific organization
                await self._reset_org_monthly_usage(organization_id)
            else:
                # Reset for all organizations
                result = await self.storage.execute_query(
                    "SELECT DISTINCT organization_id FROM quotas"
                )
                
                if result:
                    for row in result:
                        await self._reset_org_monthly_usage(row["organization_id"])
        
        logger.info(f"Monthly usage reset completed for {organization_id or 'all organizations'}")
    
    # Private helper methods
    
    async def _cache_quota(self, quota: Quota):
        """Cache quota in Redis"""
        if self.redis:
            key = f"quota:{quota.organization_id}"
            # Cache for 1 hour
            await self.redis.setex(key, 3600, quota.json())
    
    async def _get_cached_quota(self, organization_id: str) -> Optional[Quota]:
        """Get quota from Redis cache"""
        if self.redis:
            key = f"quota:{organization_id}"
            data = await self.redis.get(key)
            if data:
                return Quota.parse_raw(data)
        return None
    
    async def _update_redis_counter(
        self,
        organization_id: str,
        metric_type: MetricType,
        value: float
    ):
        """Update Redis counter for real-time tracking"""
        if self.redis:
            key = f"usage:{organization_id}:{metric_type.value}"
            
            if metric_type in [MetricType.QUERIES, MetricType.API_CALLS]:
                # Monthly counters - increment
                await self.redis.incrbyfloat(key, value)
                # Set expiry to end of month
                days_left = (datetime.utcnow().replace(
                    month=(datetime.utcnow().month % 12) + 1, day=1
                ) - datetime.utcnow()).days
                await self.redis.expire(key, days_left * 86400)
            else:
                # Absolute values - set
                await self.redis.set(key, str(value))
    
    async def _get_redis_usage(
        self,
        organization_id: str,
        metric_type: Optional[MetricType]
    ) -> Optional[float]:
        """Get usage from Redis"""
        if self.redis and metric_type:
            key = f"usage:{organization_id}:{metric_type.value}"
            value = await self.redis.get(key)
            if value:
                return float(value)
        return None
    
    async def _get_redis_connections(self, organization_id: str) -> int:
        """Get concurrent connections from Redis"""
        if self.redis:
            key = f"connections:{organization_id}"
            value = await self.redis.get(key)
            if value:
                return int(value)
        return 0
    
    async def _check_and_create_alerts(
        self,
        organization_id: str,
        metric_type: MetricType
    ):
        """Check usage levels and create alerts if needed"""
        
        quota = await self.get_quota(organization_id)
        if not quota:
            return
        
        usage = await self.get_current_usage(organization_id, metric_type)
        
        # Determine limit and calculate percentage
        limit = 0
        if metric_type == MetricType.CONCEPTS:
            limit = quota.max_concepts
        elif metric_type == MetricType.QUERIES:
            limit = quota.max_queries_per_month
        elif metric_type == MetricType.API_CALLS:
            limit = quota.max_api_calls_per_month
        elif metric_type == MetricType.STORAGE_GB:
            limit = quota.max_storage_gb
        
        if limit > 0:
            percentage = (usage / limit) * 100
            
            # Check alert thresholds (80% and 95%)
            for threshold in [80, 95]:
                if percentage >= threshold:
                    await self._create_usage_alert(
                        organization_id=organization_id,
                        metric_type=metric_type,
                        threshold_percentage=threshold,
                        current_usage=usage,
                        limit=limit
                    )
    
    async def _create_usage_alert(
        self,
        organization_id: str,
        metric_type: MetricType,
        threshold_percentage: float,
        current_usage: float,
        limit: float
    ):
        """Create a usage alert"""
        
        if self.storage:
            # Check if alert already exists
            result = await self.storage.execute_query(
                """
                SELECT id FROM usage_alerts
                WHERE organization_id = $1
                AND metric_type = $2
                AND threshold_percentage = $3
                AND is_resolved = FALSE
                """,
                [organization_id, metric_type.value, threshold_percentage]
            )
            
            if not result:
                # Create new alert
                alert = UsageAlert(
                    organization_id=organization_id,
                    metric_type=metric_type,
                    threshold_percentage=threshold_percentage,
                    current_usage=current_usage,
                    limit=limit
                )
                
                await self.storage.execute_query(
                    """
                    INSERT INTO usage_alerts (
                        id, organization_id, metric_type, threshold_percentage,
                        current_usage, limit_value, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    [
                        alert.id, alert.organization_id, alert.metric_type.value,
                        alert.threshold_percentage, alert.current_usage,
                        alert.limit, alert.created_at
                    ]
                )
                
                # TODO: Send notification to organization
                logger.warning(
                    f"Usage alert: {organization_id} has reached {threshold_percentage}% "
                    f"of {metric_type.value} quota ({current_usage}/{limit})"
                )
    
    async def _reset_org_monthly_usage(self, organization_id: str):
        """Reset monthly usage for an organization"""
        
        # Clear Redis counters
        if self.redis:
            for metric in [MetricType.QUERIES, MetricType.API_CALLS]:
                key = f"usage:{organization_id}:{metric.value}"
                await self.redis.delete(key)
        
        # Mark alerts as resolved
        if self.storage:
            await self.storage.execute_query(
                """
                UPDATE usage_alerts
                SET is_resolved = TRUE, resolved_at = CURRENT_TIMESTAMP
                WHERE organization_id = $1
                AND metric_type IN ('queries', 'api_calls')
                AND is_resolved = FALSE
                """,
                [organization_id]
            )