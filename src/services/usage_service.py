"""
Usage Service
Tracks API usage and provides analytics
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
from src.models.usage import MetricType, UsageMetric

logger = logging.getLogger(__name__)


class UsageService:
    """Service for tracking and analyzing usage"""
    
    def __init__(self, storage=None, quota_service=None):
        self.storage = storage
        self.quota_service = quota_service
        
    async def track_api_call(
        self,
        organization_id: str,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        metadata: Optional[Dict] = None
    ):
        """Track an API call"""
        
        # Track in quota service
        if self.quota_service:
            await self.quota_service.track_usage(
                organization_id=organization_id,
                metric_type=MetricType.API_CALLS,
                value=1,
                metadata={
                    "endpoint": endpoint,
                    "method": method,
                    "response_time_ms": response_time_ms,
                    "status_code": status_code,
                    **(metadata or {})
                }
            )
        
        # Store detailed record if needed
        if self.storage:
            await self.storage.execute_query(
                """
                INSERT INTO api_usage_logs (
                    organization_id, endpoint, method, response_time_ms,
                    status_code, metadata, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                [
                    organization_id, endpoint, method, response_time_ms,
                    status_code, metadata, datetime.utcnow()
                ]
            )
    
    async def track_query(
        self,
        organization_id: str,
        query_type: str,
        query_text: str,
        result_count: int,
        execution_time_ms: float,
        routed_to: str  # "postgres", "concepts", or "both"
    ):
        """Track a query execution"""
        
        # Track in quota service
        if self.quota_service:
            await self.quota_service.track_usage(
                organization_id=organization_id,
                metric_type=MetricType.QUERIES,
                value=1,
                metadata={
                    "query_type": query_type,
                    "result_count": result_count,
                    "execution_time_ms": execution_time_ms,
                    "routed_to": routed_to
                }
            )
        
        # Store query log
        if self.storage:
            await self.storage.execute_query(
                """
                INSERT INTO query_logs (
                    organization_id, query_type, query_text, result_count,
                    execution_time_ms, routed_to, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                [
                    organization_id, query_type, query_text[:500],  # Limit query text length
                    result_count, execution_time_ms, routed_to, datetime.utcnow()
                ]
            )
    
    async def track_concept_creation(
        self,
        organization_id: str,
        concept_name: str,
        source: str  # "manual", "extracted", "imported"
    ):
        """Track concept creation"""
        
        # Get current concept count
        current_count = 0
        if self.quota_service:
            current_count = await self.quota_service.get_current_usage(
                organization_id, MetricType.CONCEPTS
            )
        
        # Track new count
        if self.quota_service:
            await self.quota_service.track_usage(
                organization_id=organization_id,
                metric_type=MetricType.CONCEPTS,
                value=current_count + 1,  # Absolute value, not increment
                metadata={
                    "concept_name": concept_name,
                    "source": source
                }
            )
    
    async def track_storage_usage(
        self,
        organization_id: str,
        bytes_used: int
    ):
        """Track storage usage"""
        
        gb_used = bytes_used / (1024 ** 3)  # Convert to GB
        
        if self.quota_service:
            await self.quota_service.track_usage(
                organization_id=organization_id,
                metric_type=MetricType.STORAGE_GB,
                value=gb_used,  # Absolute value
                metadata={
                    "bytes": bytes_used
                }
            )
    
    async def get_usage_analytics(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get usage analytics for an organization"""
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        analytics = {
            "organization_id": organization_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "metrics": {}
        }
        
        if self.storage:
            # Get API call statistics
            api_stats = await self.storage.execute_query(
                """
                SELECT 
                    COUNT(*) as total_calls,
                    AVG(response_time_ms) as avg_response_time,
                    MAX(response_time_ms) as max_response_time,
                    MIN(response_time_ms) as min_response_time,
                    COUNT(DISTINCT endpoint) as unique_endpoints
                FROM api_usage_logs
                WHERE organization_id = $1
                AND timestamp BETWEEN $2 AND $3
                """,
                [organization_id, start_date, end_date]
            )
            
            if api_stats:
                analytics["metrics"]["api_calls"] = api_stats[0]
            
            # Get query statistics
            query_stats = await self.storage.execute_query(
                """
                SELECT 
                    COUNT(*) as total_queries,
                    AVG(execution_time_ms) as avg_execution_time,
                    AVG(result_count) as avg_results,
                    COUNT(CASE WHEN routed_to = 'concepts' THEN 1 END) as concept_queries,
                    COUNT(CASE WHEN routed_to = 'postgres' THEN 1 END) as sql_queries
                FROM query_logs
                WHERE organization_id = $1
                AND timestamp BETWEEN $2 AND $3
                """,
                [organization_id, start_date, end_date]
            )
            
            if query_stats:
                analytics["metrics"]["queries"] = query_stats[0]
            
            # Get daily usage trend
            daily_trend = await self.storage.execute_query(
                """
                SELECT 
                    DATE(timestamp) as date,
                    metric_type,
                    SUM(value) as total_value
                FROM usage_metrics
                WHERE organization_id = $1
                AND timestamp BETWEEN $2 AND $3
                GROUP BY DATE(timestamp), metric_type
                ORDER BY date DESC
                """,
                [organization_id, start_date, end_date]
            )
            
            if daily_trend:
                analytics["daily_trend"] = [
                    {
                        "date": row["date"].isoformat() if row["date"] else None,
                        "metric_type": row["metric_type"],
                        "value": float(row["total_value"])
                    }
                    for row in daily_trend
                ]
        
        # Get current usage snapshot
        if self.quota_service:
            snapshot = await self.quota_service.get_usage_snapshot(organization_id)
            analytics["current_usage"] = snapshot.dict()
        
        return analytics
    
    async def get_top_queries(
        self,
        organization_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top queries by frequency"""
        
        if self.storage:
            result = await self.storage.execute_query(
                """
                SELECT 
                    query_text,
                    COUNT(*) as frequency,
                    AVG(execution_time_ms) as avg_time,
                    AVG(result_count) as avg_results
                FROM query_logs
                WHERE organization_id = $1
                AND timestamp > NOW() - INTERVAL '30 days'
                GROUP BY query_text
                ORDER BY frequency DESC
                LIMIT $2
                """,
                [organization_id, limit]
            )
            
            if result:
                return [dict(row) for row in result]
        
        return []
    
    async def get_api_endpoint_stats(
        self,
        organization_id: str
    ) -> List[Dict[str, Any]]:
        """Get statistics by API endpoint"""
        
        if self.storage:
            result = await self.storage.execute_query(
                """
                SELECT 
                    endpoint,
                    method,
                    COUNT(*) as call_count,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count
                FROM api_usage_logs
                WHERE organization_id = $1
                AND timestamp > NOW() - INTERVAL '30 days'
                GROUP BY endpoint, method
                ORDER BY call_count DESC
                """,
                [organization_id]
            )
            
            if result:
                return [dict(row) for row in result]
        
        return []
    
    async def predict_quota_exhaustion(
        self,
        organization_id: str,
        metric_type: MetricType
    ) -> Optional[datetime]:
        """Predict when a quota will be exhausted based on current usage patterns"""
        
        if not self.storage or not self.quota_service:
            return None
        
        # Get current usage and quota
        current_usage = await self.quota_service.get_current_usage(
            organization_id, metric_type
        )
        quota = await self.quota_service.get_quota(organization_id)
        
        if not quota:
            return None
        
        # Get limit based on metric type
        limit = 0
        if metric_type == MetricType.CONCEPTS:
            limit = quota.max_concepts
        elif metric_type == MetricType.QUERIES:
            limit = quota.max_queries_per_month
        elif metric_type == MetricType.API_CALLS:
            limit = quota.max_api_calls_per_month
        elif metric_type == MetricType.STORAGE_GB:
            limit = quota.max_storage_gb
        
        if current_usage >= limit:
            return datetime.utcnow()  # Already exhausted
        
        # Calculate daily usage rate over last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        result = await self.storage.execute_query(
            """
            SELECT 
                COUNT(*) as days_with_usage,
                SUM(value) as total_value
            FROM (
                SELECT DATE(timestamp) as date, SUM(value) as value
                FROM usage_metrics
                WHERE organization_id = $1
                AND metric_type = $2
                AND timestamp >= $3
                GROUP BY DATE(timestamp)
            ) as daily_usage
            """,
            [organization_id, metric_type.value, week_ago]
        )
        
        if result and result[0]["days_with_usage"] > 0:
            days_with_usage = result[0]["days_with_usage"]
            total_value = float(result[0]["total_value"] or 0)
            
            # Calculate average daily usage
            avg_daily_usage = total_value / days_with_usage
            
            if avg_daily_usage > 0:
                # Calculate days until exhaustion
                remaining = limit - current_usage
                days_until_exhaustion = remaining / avg_daily_usage
                
                # Predict date
                exhaustion_date = datetime.utcnow() + timedelta(days=days_until_exhaustion)
                
                return exhaustion_date
        
        return None  # Cannot predict