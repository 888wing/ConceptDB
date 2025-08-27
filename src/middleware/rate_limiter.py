"""
Rate Limiter Middleware
Implements rate limiting for API endpoints
Phase 1-2: Protection against abuse and resource management
"""

import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
from functools import wraps

from fastapi import Request, HTTPException
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RateLimitStrategy:
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimiter:
    """Base rate limiter implementation"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
        strategy: str = RateLimitStrategy.SLIDING_WINDOW
    ):
        """
        Initialize rate limiter
        
        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            burst_size: Max burst requests
            strategy: Rate limiting strategy
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        self.strategy = strategy
        
        # Storage for different strategies
        self.fixed_windows: Dict[str, Dict[str, int]] = defaultdict(lambda: {})
        self.sliding_windows: Dict[str, deque] = defaultdict(lambda: deque())
        self.token_buckets: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            'tokens': burst_size,
            'last_refill': time.time()
        })
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'rate_limited_requests': 0,
            'unique_clients': set()
        }
        
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        # Try to get from headers (API key, user ID)
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return f"api:{api_key}"
            
        # Try to get from auth
        auth_header = request.headers.get('Authorization')
        if auth_header:
            return f"auth:{auth_header[:20]}"
            
        # Fall back to IP address
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            client_ip = forwarded.split(',')[0].strip()
        else:
            client_ip = request.client.host if request.client else 'unknown'
            
        return f"ip:{client_ip}"
        
    async def is_allowed(self, request: Request) -> Tuple[bool, Optional[Dict[str, str]]]:
        """
        Check if request is allowed
        
        Returns:
            Tuple of (allowed, rate_limit_headers)
        """
        client_id = self._get_client_id(request)
        self.stats['unique_clients'].add(client_id)
        self.stats['total_requests'] += 1
        
        if self.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._check_fixed_window(client_id)
        elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(client_id)
        elif self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._check_token_bucket(client_id)
        else:
            return True, None
            
    async def _check_fixed_window(
        self, 
        client_id: str
    ) -> Tuple[bool, Optional[Dict[str, str]]]:
        """Fixed window rate limiting"""
        current_minute = int(time.time() / 60)
        current_hour = int(time.time() / 3600)
        
        # Initialize windows if needed
        if client_id not in self.fixed_windows:
            self.fixed_windows[client_id] = {
                'minute': current_minute,
                'minute_count': 0,
                'hour': current_hour,
                'hour_count': 0
            }
            
        window = self.fixed_windows[client_id]
        
        # Reset counters if window has passed
        if window['minute'] != current_minute:
            window['minute'] = current_minute
            window['minute_count'] = 0
            
        if window['hour'] != current_hour:
            window['hour'] = current_hour
            window['hour_count'] = 0
            
        # Check limits
        if window['minute_count'] >= self.requests_per_minute:
            self.stats['rate_limited_requests'] += 1
            headers = {
                'X-RateLimit-Limit': str(self.requests_per_minute),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str((current_minute + 1) * 60)
            }
            return False, headers
            
        if window['hour_count'] >= self.requests_per_hour:
            self.stats['rate_limited_requests'] += 1
            headers = {
                'X-RateLimit-Limit': str(self.requests_per_hour),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str((current_hour + 1) * 3600)
            }
            return False, headers
            
        # Increment counters
        window['minute_count'] += 1
        window['hour_count'] += 1
        
        headers = {
            'X-RateLimit-Limit': str(self.requests_per_minute),
            'X-RateLimit-Remaining': str(self.requests_per_minute - window['minute_count']),
            'X-RateLimit-Reset': str((current_minute + 1) * 60)
        }
        
        return True, headers
        
    async def _check_sliding_window(
        self, 
        client_id: str
    ) -> Tuple[bool, Optional[Dict[str, str]]]:
        """Sliding window rate limiting"""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # Get or create window
        window = self.sliding_windows[client_id]
        
        # Remove old entries
        while window and window[0] < hour_ago:
            window.popleft()
            
        # Count requests in time windows
        minute_count = sum(1 for t in window if t > minute_ago)
        hour_count = len(window)
        
        # Check limits
        if minute_count >= self.requests_per_minute:
            self.stats['rate_limited_requests'] += 1
            headers = {
                'X-RateLimit-Limit': str(self.requests_per_minute),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int(window[0] + 60))
            }
            return False, headers
            
        if hour_count >= self.requests_per_hour:
            self.stats['rate_limited_requests'] += 1
            headers = {
                'X-RateLimit-Limit': str(self.requests_per_hour),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int(window[0] + 3600))
            }
            return False, headers
            
        # Add current request
        window.append(now)
        
        headers = {
            'X-RateLimit-Limit': str(self.requests_per_minute),
            'X-RateLimit-Remaining': str(self.requests_per_minute - minute_count - 1),
            'X-RateLimit-Reset': str(int(now + 60))
        }
        
        return True, headers
        
    async def _check_token_bucket(
        self, 
        client_id: str
    ) -> Tuple[bool, Optional[Dict[str, str]]]:
        """Token bucket rate limiting"""
        now = time.time()
        bucket = self.token_buckets[client_id]
        
        # Refill tokens based on time elapsed
        time_elapsed = now - bucket['last_refill']
        refill_rate = self.requests_per_minute / 60.0  # Tokens per second
        tokens_to_add = time_elapsed * refill_rate
        
        bucket['tokens'] = min(
            self.burst_size,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_refill'] = now
        
        # Check if tokens available
        if bucket['tokens'] < 1:
            self.stats['rate_limited_requests'] += 1
            headers = {
                'X-RateLimit-Limit': str(self.burst_size),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int(now + (1 / refill_rate)))
            }
            return False, headers
            
        # Consume token
        bucket['tokens'] -= 1
        
        headers = {
            'X-RateLimit-Limit': str(self.burst_size),
            'X-RateLimit-Remaining': str(int(bucket['tokens'])),
            'X-RateLimit-Reset': str(int(now + 60))
        }
        
        return True, headers
        
    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        return {
            'total_requests': self.stats['total_requests'],
            'rate_limited_requests': self.stats['rate_limited_requests'],
            'unique_clients': len(self.stats['unique_clients']),
            'rejection_rate': (
                self.stats['rate_limited_requests'] / self.stats['total_requests']
                if self.stats['total_requests'] > 0 else 0
            ),
            'strategy': self.strategy
        }
        
    def reset_client(self, client_id: str) -> None:
        """Reset rate limit for specific client"""
        if client_id in self.fixed_windows:
            del self.fixed_windows[client_id]
        if client_id in self.sliding_windows:
            del self.sliding_windows[client_id]
        if client_id in self.token_buckets:
            self.token_buckets[client_id] = {
                'tokens': self.burst_size,
                'last_refill': time.time()
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: RateLimiter,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.exclude_paths = exclude_paths or ['/health', '/docs', '/openapi.json']
        
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
            
        # Check rate limit
        allowed, headers = await self.rate_limiter.is_allowed(request)
        
        if not allowed:
            # Return 429 Too Many Requests
            response = Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers=headers
            )
            return response
            
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        if headers:
            for key, value in headers.items():
                response.headers[key] = value
                
        return response


def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000
):
    """
    Decorator for rate limiting specific endpoints
    
    Usage:
        @app.get("/api/endpoint")
        @rate_limit(requests_per_minute=30)
        async def endpoint():
            return {"message": "Hello"}
    """
    limiter = RateLimiter(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour
    )
    
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            allowed, headers = await limiter.is_allowed(request)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers=headers
                )
                
            # Add headers to response
            result = await func(request, *args, **kwargs)
            if isinstance(result, Response) and headers:
                for key, value in headers.items():
                    result.headers[key] = value
                    
            return result
            
        return wrapper
    return decorator