"""
Agentic Query Service - Context Manager

Manages conversational state for query sessions, enabling context-aware
follow-up queries and reference resolution.

Feature: 001-agentic-query
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from app.models.agent import QueryContext
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ContextManager:
    """
    Manages query contexts across sessions.
    
    Provides in-memory storage of conversational context with automatic
    TTL-based cleanup. Each session maintains its own isolated context.
    
    Attributes:
        contexts: Dictionary mapping session_id to QueryContext
        ttl: Time-to-live for contexts (default: 1 hour)
        cleanup_task: Background task for periodic cleanup
    """

    def __init__(self, ttl_hours: int = 1):
        """
        Initialize the context manager.
        
        Args:
            ttl_hours: Time-to-live for contexts in hours
        """
        self.contexts: Dict[UUID, QueryContext] = {}
        self.ttl = timedelta(hours=ttl_hours)
        self.cleanup_task: Optional[asyncio.Task] = None
        logger.info(
            f"Context manager initialized with TTL={ttl_hours}h",
            extra={"ttl_hours": ttl_hours}
        )

    def get_or_create(self, session_id: UUID) -> QueryContext:
        """
        Get existing context or create new one for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            QueryContext for the session
        """
        # Cleanup expired contexts before retrieving
        self._cleanup_expired()
        
        if session_id not in self.contexts:
            logger.info(
                f"Creating new context for session {session_id}",
                extra={"session_id": str(session_id)}
            )
            self.contexts[session_id] = QueryContext(session_id=session_id)
        else:
            logger.debug(
                f"Retrieved existing context for session {session_id}",
                extra={"session_id": str(session_id)}
            )
        
        return self.contexts[session_id]

    def get(self, session_id: UUID) -> Optional[QueryContext]:
        """
        Get context for a session without creating if missing.
        
        Args:
            session_id: Session identifier
            
        Returns:
            QueryContext or None if not found
        """
        return self.contexts.get(session_id)

    def update(self, session_id: UUID, context: QueryContext) -> None:
        """
        Update context for a session.
        
        Args:
            session_id: Session identifier
            context: Updated QueryContext
        """
        context.last_updated = datetime.utcnow()
        self.contexts[session_id] = context
        logger.debug(
            f"Updated context for session {session_id}",
            extra={"session_id": str(session_id)}
        )

    def delete(self, session_id: UUID) -> bool:
        """
        Delete context for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if context was deleted, False if not found
        """
        if session_id in self.contexts:
            del self.contexts[session_id]
            logger.info(
                f"Deleted context for session {session_id}",
                extra={"session_id": str(session_id)}
            )
            return True
        return False

    def _cleanup_expired(self) -> int:
        """
        Remove expired contexts based on TTL.
        
        Returns:
            Number of contexts removed
        """
        now = datetime.utcnow()
        expired = [
            sid for sid, ctx in self.contexts.items()
            if now - ctx.last_updated > self.ttl
        ]
        
        for sid in expired:
            del self.contexts[sid]
        
        if expired:
            logger.info(
                f"Cleaned up {len(expired)} expired contexts",
                extra={"count": len(expired)}
            )
        
        return len(expired)

    async def start_cleanup_task(self, interval_minutes: int = 5) -> None:
        """
        Start background task for periodic context cleanup.
        
        Args:
            interval_minutes: Cleanup interval in minutes
        """
        if self.cleanup_task is not None:
            logger.warning("Cleanup task already running")
            return
        
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval_minutes * 60)
                    self._cleanup_expired()
                except asyncio.CancelledError:
                    logger.info("Cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(
                        f"Error in cleanup task: {e}",
                        exc_info=True
                    )
        
        self.cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(
            f"Started cleanup task with interval={interval_minutes}min",
            extra={"interval_minutes": interval_minutes}
        )

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self.cleanup_task is not None:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            logger.info("Stopped cleanup task")

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about managed contexts.
        
        Returns:
            Dictionary with context statistics
        """
        now = datetime.utcnow()
        active = sum(
            1 for ctx in self.contexts.values()
            if now - ctx.last_updated <= self.ttl
        )
        
        return {
            "total_contexts": len(self.contexts),
            "active_contexts": active,
            "expired_contexts": len(self.contexts) - active
        }

    def clear_all(self) -> int:
        """
        Clear all contexts (for testing/maintenance).
        
        Returns:
            Number of contexts cleared
        """
        count = len(self.contexts)
        self.contexts.clear()
        logger.warning(
            f"Cleared all {count} contexts",
            extra={"count": count}
        )
        return count

    def track_entity(
        self,
        session_id: UUID,
        entity_type: str,
        entity_id: str
    ) -> None:
        """
        Track an entity mention in the session context (T074).
        
        Args:
            session_id: Session identifier
            entity_type: Type of entity (e.g., "api", "gateway", "vulnerability")
            entity_id: Unique identifier for the entity
        """
        context = self.get_or_create(session_id)
        context.add_entity_mention(entity_type, entity_id)
        self.update(session_id, context)
        logger.debug(
            f"Tracked entity {entity_type}:{entity_id} in session {session_id}",
            extra={
                "session_id": str(session_id),
                "entity_type": entity_type,
                "entity_id": entity_id
            }
        )

    def get_entities_by_type(
        self,
        session_id: UUID,
        entity_type: str
    ) -> list[str]:
        """
        Get all entities of a specific type mentioned in the session (T074).
        
        Args:
            session_id: Session identifier
            entity_type: Type of entity to retrieve
            
        Returns:
            List of entity IDs of the specified type
        """
        context = self.get(session_id)
        if not context:
            return []
        return context.entity_mentions.get(entity_type, [])

    def get_all_entities(self, session_id: UUID) -> Dict[str, list[str]]:
        """
        Get all entities mentioned in the session (T074).
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary mapping entity types to lists of entity IDs
        """
        context = self.get(session_id)
        if not context:
            return {}
        return context.entity_mentions.copy()

    def add_query_to_history(
        self,
        session_id: UUID,
        query_text: str
    ) -> None:
        """
        Add a query to the session history (T077).
        
        Maintains a maximum of 10 queries per session.
        
        Args:
            session_id: Session identifier
            query_text: Query text to add
        """
        context = self.get_or_create(session_id)
        context.add_query(query_text)
        self.update(session_id, context)
        logger.debug(
            f"Added query to history for session {session_id}",
            extra={
                "session_id": str(session_id),
                "query_count": len(context.query_history)
            }
        )

    def get_query_history(self, session_id: UUID) -> list[str]:
        """
        Get query history for a session (T077).
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of previous queries (max 10)
        """
        context = self.get(session_id)
        if not context:
            return []
        return context.query_history.copy()

    def cache_query_results(
        self,
        session_id: UUID,
        results: Dict[str, Any]
    ) -> None:
        """
        Cache results from the last query (T078).
        
        Args:
            session_id: Session identifier
            results: Query results to cache
        """
        context = self.get_or_create(session_id)
        context.update_results(results)
        self.update(session_id, context)
        logger.debug(
            f"Cached query results for session {session_id}",
            extra={"session_id": str(session_id)}
        )

    def get_cached_results(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get cached results from the last query (T078).
        
        Args:
            session_id: Session identifier
            
        Returns:
            Cached results or None if not available
        """
        context = self.get(session_id)
        if not context:
            return None
        return context.last_query_results


# Global context manager instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """
    Get the global context manager instance.
    
    Returns:
        ContextManager singleton instance
    """
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager

# Made with Bob
