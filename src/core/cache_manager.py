"""
Cache Manager
Redis-based caching with fallback to in-memory cache
Phase 1-2: Performance optimization through intelligent caching
"""

import json
import hashlib
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import pickle
from functools import wraps
import asyncio
from collections import OrderedDict

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logging.warning("Redis not available, using in-memory cache")

logger = logging.getLogger(__name__)


class CacheStrategy:
    """Cache strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used  
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on usage patterns


class InMemoryCache:
    """Fallback in-memory cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.frequency: Dict[str, int] = {}
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            self.hits += 1
            self.frequency[key] = self.frequency.get(key, 0) + 1
            # Move to end (LRU)
            self.cache.move_to_end(key)
            value, expiry = self.cache[key]
            if expiry and datetime.utcnow() > expiry:
                del self.cache[key]
                self.misses += 1
                return None
            return value
        self.misses += 1
        return None
        
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        expiry = None
        if ttl:
            expiry = datetime.utcnow() + timedelta(seconds=ttl)
            
        # Check cache size
        if len(self.cache) >= self.max_size:
            # Remove least recently used
            self.cache.popitem(last=False)
            
        self.cache[key] = (value, expiry)
        self.frequency[key] = 1
        return True
        
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self.cache:
            del self.cache[key]
            if key in self.frequency:
                del self.frequency[key]
            return True
        return False
        
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if key in self.cache:
            _, expiry = self.cache[key]
            if expiry and datetime.utcnow() > expiry:
                del self.cache[key]
                return False
            return True
        return False
        
    async def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        self.frequency.clear()
        self.hits = 0
        self.misses = 0
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'most_frequent': sorted(
                self.frequency.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }


class CacheManager:
    """Manages caching with Redis or in-memory fallback"""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_memory_size: int = 1000,
        default_ttl: int = 3600,
        strategy: str = CacheStrategy.LRU
    ):
        """
        Initialize cache manager
        
        Args:
            redis_url: Redis connection URL
            max_memory_size: Max size for in-memory cache
            default_ttl: Default TTL in seconds
            strategy: Caching strategy
        """
        self.redis_url = redis_url
        self.max_memory_size = max_memory_size
        self.default_ttl = default_ttl
        self.strategy = strategy
        
        # Initialize cache backend
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache = InMemoryCache(max_memory_size)
        self.use_redis = False
        
        # Cache zones for different data types
        self.zones = {
            'queries': 'q:',
            'concepts': 'c:',
            'vectors': 'v:',
            'metadata': 'm:',
            'results': 'r:'
        }
        
        # Cache statistics
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_response_time': 0
        }
        
    async def connect(self):
        """Connect to cache backend"""
        if HAS_REDIS and self.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=False
                )
                await self.redis_client.ping()
                self.use_redis = True
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using in-memory cache")
                self.use_redis = False
        else:
            self.use_redis = False
            logger.info("Using in-memory cache")
            
    async def disconnect(self):
        """Disconnect from cache backend"""
        if self.redis_client:
            await self.redis_client.close()
            
    def _generate_key(self, zone: str, identifier: str) -> str:
        """Generate cache key with zone prefix"""
        prefix = self.zones.get(zone, '')
        return f"{prefix}{identifier}"
        
    def _hash_key(self, data: Union[str, Dict, list]) -> str:
        """Generate hash key from data"""
        if isinstance(data, (dict, list)):
            data = json.dumps(data, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()
        
    async def get(
        self, 
        key: str, 
        zone: str = 'queries'
    ) -> Optional[Any]:
        """Get value from cache"""
        self.stats['total_requests'] += 1
        full_key = self._generate_key(zone, key)
        
        try:
            if self.use_redis and self.redis_client:
                value = await self.redis_client.get(full_key)
                if value:
                    self.stats['cache_hits'] += 1
                    return pickle.loads(value)
            else:
                value = await self.memory_cache.get(full_key)
                if value:
                    self.stats['cache_hits'] += 1
                    return value
                    
            self.stats['cache_misses'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
            
    async def set(
        self,
        key: str,
        value: Any,
        zone: str = 'queries',
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        full_key = self._generate_key(zone, key)
        ttl = ttl or self.default_ttl
        
        try:
            if self.use_redis and self.redis_client:
                serialized = pickle.dumps(value)
                return await self.redis_client.set(
                    full_key, 
                    serialized, 
                    ex=ttl
                )
            else:
                return await self.memory_cache.set(full_key, value, ttl)
                
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
            
    async def delete(self, key: str, zone: str = 'queries') -> bool:
        """Delete key from cache"""
        full_key = self._generate_key(zone, key)
        
        try:
            if self.use_redis and self.redis_client:
                return bool(await self.redis_client.delete(full_key))
            else:
                return await self.memory_cache.delete(full_key)
                
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
            
    async def clear_zone(self, zone: str) -> int:
        """Clear all keys in a zone"""
        prefix = self.zones.get(zone, '')
        count = 0
        
        try:
            if self.use_redis and self.redis_client:
                # Use SCAN to find keys with prefix
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor, 
                        match=f"{prefix}*"
                    )
                    if keys:
                        await self.redis_client.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            else:
                # Clear memory cache keys with prefix
                keys_to_delete = [
                    k for k in self.memory_cache.cache.keys() 
                    if k.startswith(prefix)
                ]
                for key in keys_to_delete:
                    await self.memory_cache.delete(key)
                    count += 1
                    
            return count
            
        except Exception as e:
            logger.error(f"Clear zone error: {e}")
            return 0
            
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""
        count = 0
        
        try:
            if self.use_redis and self.redis_client:
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor, 
                        match=pattern
                    )
                    if keys:
                        await self.redis_client.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            else:
                # Pattern matching for memory cache
                import re
                regex = re.compile(pattern.replace('*', '.*'))
                keys_to_delete = [
                    k for k in self.memory_cache.cache.keys() 
                    if regex.match(k)
                ]
                for key in keys_to_delete:
                    await self.memory_cache.delete(key)
                    count += 1
                    
            return count
            
        except Exception as e:
            logger.error(f"Invalidate pattern error: {e}")
            return 0
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = (
            self.stats['cache_hits'] / self.stats['total_requests']
            if self.stats['total_requests'] > 0 else 0
        )
        
        stats = {
            'backend': 'redis' if self.use_redis else 'memory',
            'total_requests': self.stats['total_requests'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'hit_rate': hit_rate,
            'strategy': self.strategy
        }
        
        if not self.use_redis:
            stats.update(self.memory_cache.get_stats())
            
        return stats
        
    def cache_decorator(
        self,
        zone: str = 'queries',
        ttl: Optional[int] = None,
        key_generator: Optional[callable] = None
    ):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_generator:
                    cache_key = key_generator(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = self._hash_key(':'.join(key_parts))
                    
                # Try to get from cache
                cached = await self.get(cache_key, zone)
                if cached is not None:
                    return cached
                    
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await self.set(cache_key, result, zone, ttl)
                
                return result
                
            return wrapper
        return decorator
        
    async def warmup_cache(self, queries: list) -> int:
        """Warm up cache with common queries"""
        count = 0
        
        for query in queries:
            key = self._hash_key(query)
            # Check if already cached
            if not await self.get(key, 'queries'):
                # Would execute query and cache result
                # For now, just count
                count += 1
                
        logger.info(f"Cache warmup: {count} queries prepared")
        return count