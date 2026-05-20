"""
Redis async client for caching and session management.
"""
import logging
import json
from typing import Optional, Any
import redis.asyncio as redis
from redis.asyncio import Redis

from config.settings import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """Initialize Redis client."""
    global _redis_client
    
    try:
        _redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await _redis_client.ping()
        logger.info("Redis client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise


async def close_redis() -> None:
    """Close Redis client."""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis client closed")


def get_redis_client() -> Redis:
    """Get Redis client instance."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_client


class CacheService:
    """Cache operations service."""
    
    TTL_SHORT = 5 * 60  # 5 minutes
    TTL_MEDIUM = 30 * 60  # 30 minutes
    TTL_LONG = 24 * 60 * 60  # 24 hours
    
    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            client = get_redis_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None
    
    @staticmethod
    async def set(key: str, value: Any, ttl: int = TTL_MEDIUM) -> bool:
        """Set value in cache with TTL."""
        try:
            client = get_redis_client()
            await client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    @staticmethod
    async def delete(key: str) -> bool:
        """Delete key from cache."""
        try:
            client = get_redis_client()
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    @staticmethod
    async def exists(key: str) -> bool:
        """Check if key exists in cache."""
        try:
            client = get_redis_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False
    
    @staticmethod
    async def increment(key: str, amount: int = 1) -> int:
        """Increment counter in cache."""
        try:
            client = get_redis_client()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Cache increment error for key {key}: {e}")
            return 0
    
    @staticmethod
    async def set_with_expiry(key: str, value: Any, ttl: int) -> bool:
        """Set value with specific TTL."""
        return await CacheService.set(key, value, ttl)
    
    @staticmethod
    async def get_or_set(
        key: str,
        factory,
        ttl: int = TTL_MEDIUM,
    ) -> Any:
        """Get from cache or call factory and cache result."""
        # Try to get from cache
        cached = await CacheService.get(key)
        if cached is not None:
            return cached
        
        # Call factory function
        if callable(factory):
            result = await factory() if hasattr(factory, '__await__') else factory()
        else:
            result = factory
        
        # Cache result
        await CacheService.set(key, result, ttl)
        return result


class RateLimitService:
    """Rate limiting service using Redis."""
    
    @staticmethod
    async def check_rate_limit(
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.
        Returns (allowed, remaining_requests).
        """
        try:
            client = get_redis_client()
            current = await client.incr(key)
            
            if current == 1:
                await client.expire(key, window_seconds)
            
            allowed = current <= max_requests
            remaining = max(0, max_requests - current)
            
            return allowed, remaining
        except Exception as e:
            logger.warning(f"Rate limit check error for key {key}: {e}")
            return True, max_requests  # Allow on error
    
    @staticmethod
    async def get_remaining(key: str, max_requests: int) -> int:
        """Get remaining requests for a key."""
        try:
            client = get_redis_client()
            current = await client.get(key)
            current = int(current) if current else 0
            return max(0, max_requests - current)
        except Exception as e:
            logger.warning(f"Get remaining error for key {key}: {e}")
            return max_requests


async def redis_health_check() -> bool:
    """Check Redis connection health."""
    try:
        client = get_redis_client()
        await client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False
