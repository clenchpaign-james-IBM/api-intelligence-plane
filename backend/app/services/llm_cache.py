"""
LLM Response Caching Service

Implements caching for LLM responses to improve performance and reduce costs.
Caches common query patterns with TTL-based expiration.

Feature: 001-agentic-query
Task: T085
"""

import hashlib
import time
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta

from app.utils.logging import get_logger

logger = get_logger(__name__)


class LLMResponseCache:
    """
    Cache for LLM responses with TTL-based expiration.
    
    Caches LLM responses based on query hash and context to avoid
    redundant LLM calls for similar queries.
    
    Attributes:
        cache: Dictionary storing cached responses
        max_size: Maximum number of cached entries
        default_ttl_seconds: Default TTL for cache entries
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl_seconds: int = 300,  # 5 minutes
    ):
        """
        Initialize LLM response cache.
        
        Args:
            max_size: Maximum number of cached entries
            default_ttl_seconds: Default TTL in seconds
        """
        self.cache: Dict[str, Tuple[Any, float, datetime]] = {}
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        
        logger.info(
            f"Initialized LLM cache with max_size={max_size}, ttl={default_ttl_seconds}s"
        )
    
    def _generate_cache_key(
        self,
        query: str,
        context_hash: str,
        model: Optional[str] = None,
    ) -> str:
        """
        Generate cache key from query and context.
        
        Args:
            query: Query text
            context_hash: Hash of context data
            model: Optional model name
            
        Returns:
            Cache key string
        """
        # Normalize query (lowercase, strip whitespace)
        normalized_query = query.lower().strip()
        
        # Create composite key
        key_parts = [normalized_query, context_hash]
        if model:
            key_parts.append(model)
        
        # Hash the key for consistent length
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(
        self,
        query: str,
        context_hash: str,
        model: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Get cached response if available and not expired.
        
        Args:
            query: Query text
            context_hash: Hash of context data
            model: Optional model name
            
        Returns:
            Cached response or None if not found/expired
        """
        key = self._generate_cache_key(query, context_hash, model)
        
        if key not in self.cache:
            logger.debug(f"Cache miss for query: {query[:50]}...")
            return None
        
        response, timestamp, created_at = self.cache[key]
        
        # Check if expired
        age_seconds = time.time() - timestamp
        if age_seconds > self.default_ttl_seconds:
            logger.debug(
                f"Cache expired for query: {query[:50]}... (age: {age_seconds:.1f}s)"
            )
            del self.cache[key]
            return None
        
        logger.info(
            f"Cache hit for query: {query[:50]}... (age: {age_seconds:.1f}s)",
            extra={
                "cache_key": key,
                "age_seconds": age_seconds,
                "created_at": created_at.isoformat(),
            }
        )
        
        return response
    
    def set(
        self,
        query: str,
        context_hash: str,
        response: Any,
        model: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Cache a response with TTL.
        
        Args:
            query: Query text
            context_hash: Hash of context data
            response: Response to cache
            model: Optional model name
            ttl_seconds: Optional custom TTL (uses default if None)
        """
        # Check if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        key = self._generate_cache_key(query, context_hash, model)
        timestamp = time.time()
        created_at = datetime.utcnow()
        
        self.cache[key] = (response, timestamp, created_at)
        
        logger.debug(
            f"Cached response for query: {query[:50]}...",
            extra={
                "cache_key": key,
                "cache_size": len(self.cache),
                "ttl_seconds": ttl_seconds or self.default_ttl_seconds,
            }
        )
    
    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry."""
        if not self.cache:
            return
        
        # Find oldest entry by timestamp
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
        del self.cache[oldest_key]
        
        logger.debug(
            f"Evicted oldest cache entry",
            extra={"cache_size": len(self.cache)}
        )
    
    def clear(self) -> None:
        """Clear all cached entries."""
        count = len(self.cache)
        self.cache.clear()
        
        logger.info(f"Cleared {count} cache entries")
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp, _) in self.cache.items()
            if current_time - timestamp > self.default_ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(
                f"Cleaned up {len(expired_keys)} expired cache entries",
                extra={"remaining_entries": len(self.cache)}
            )
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.cache:
            return {
                "size": 0,
                "max_size": self.max_size,
                "utilization": 0.0,
                "oldest_entry_age_seconds": 0,
                "newest_entry_age_seconds": 0,
            }
        
        current_time = time.time()
        timestamps = [timestamp for _, timestamp, _ in self.cache.values()]
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "utilization": len(self.cache) / self.max_size,
            "oldest_entry_age_seconds": current_time - min(timestamps),
            "newest_entry_age_seconds": current_time - max(timestamps),
            "default_ttl_seconds": self.default_ttl_seconds,
        }


def hash_context(context: Dict[str, Any]) -> str:
    """
    Generate hash for context dictionary.
    
    Args:
        context: Context dictionary
        
    Returns:
        Hash string
    """
    # Sort keys for consistent hashing
    import json
    context_str = json.dumps(context, sort_keys=True)
    return hashlib.sha256(context_str.encode()).hexdigest()


# Global cache instance
_cache_instance: Optional[LLMResponseCache] = None


def get_llm_cache() -> LLMResponseCache:
    """
    Get global LLM cache instance.
    
    Returns:
        LLMResponseCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMResponseCache()
    return _cache_instance


# Made with Bob