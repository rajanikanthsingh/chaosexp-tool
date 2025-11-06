"""Redis caching utilities for ChaosMonkey web app."""

from __future__ import annotations

import json
import os
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional

import redis
from redis.exceptions import RedisError


class CacheManager:
    """Manage Redis caching for API responses."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache manager with Redis connection."""
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL", 
            "redis://localhost:6379/0"
        )
        self._client: Optional[redis.Redis] = None
        self._enabled = True
        
        try:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self._client.ping()
            print(f"✅ Redis cache connected: {self.redis_url}")
        except (RedisError, ConnectionError) as e:
            print(f"⚠️  Redis unavailable, caching disabled: {e}")
            self._enabled = False
            self._client = None
    
    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enabled and self._client is not None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None
        
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            print(f"Cache get error for {key}: {e}")
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL (seconds)."""
        if not self.enabled:
            return False
        
        try:
            serialized = json.dumps(value)
            if ttl:
                self._client.setex(key, ttl, serialized)
            else:
                self._client.set(key, serialized)
            return True
        except (RedisError, TypeError) as e:
            print(f"Cache set error for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.enabled:
            return False
        
        try:
            self._client.delete(key)
            return True
        except RedisError as e:
            print(f"Cache delete error for {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.enabled:
            return 0
        
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except RedisError as e:
            print(f"Cache clear error for pattern {pattern}: {e}")
            return 0
    
    def get_hash(self, key: str, field: str) -> Optional[Any]:
        """Get field from hash."""
        if not self.enabled:
            return None
        
        try:
            value = self._client.hget(key, field)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            print(f"Cache hget error for {key}:{field}: {e}")
            return None
    
    def set_hash(
        self, 
        key: str, 
        field: str, 
        value: Any
    ) -> bool:
        """Set field in hash."""
        if not self.enabled:
            return False
        
        try:
            serialized = json.dumps(value)
            self._client.hset(key, field, serialized)
            return True
        except (RedisError, TypeError) as e:
            print(f"Cache hset error for {key}:{field}: {e}")
            return False
    
    def get_all_hash(self, key: str) -> Dict[str, Any]:
        """Get all fields from hash."""
        if not self.enabled:
            return {}
        
        try:
            data = self._client.hgetall(key)
            return {
                field: json.loads(value)
                for field, value in data.items()
            }
        except (RedisError, json.JSONDecodeError) as e:
            print(f"Cache hgetall error for {key}: {e}")
            return {}
    
    def delete_hash_field(self, key: str, field: str) -> bool:
        """Delete field from hash."""
        if not self.enabled:
            return False
        
        try:
            self._client.hdel(key, field)
            return True
        except RedisError as e:
            print(f"Cache hdel error for {key}:{field}: {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        if not self.enabled:
            return False
        
        try:
            self._client.expire(key, ttl)
            return True
        except RedisError as e:
            print(f"Cache expire error for {key}: {e}")
            return False


# Global cache instance
cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get or create global cache manager."""
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager()
    return cache_manager


def cached(
    key_prefix: str,
    ttl: int = 300,
    use_hash: bool = False
):
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds (default 5 minutes)
        use_hash: Whether to use Redis hash for storing individual items
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key from function args
            key_parts = [key_prefix]
            if args:
                key_parts.extend(str(arg) for arg in args)
            if kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            if cache.enabled:
                cached_value = cache.get(cache_key)
                if cached_value is not None:
                    print(f"✅ Cache HIT: {cache_key}")
                    return cached_value
                print(f"❌ Cache MISS: {cache_key}")
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            if cache.enabled and result is not None:
                cache.set(cache_key, result, ttl)
                print(f"💾 Cached: {cache_key} (TTL: {ttl}s)")
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str = "*") -> int:
    """Invalidate cache entries matching pattern."""
    cache = get_cache()
    if cache.enabled:
        count = cache.clear_pattern(pattern)
        print(f"🗑️  Invalidated {count} cache entries matching: {pattern}")
        return count
    return 0
