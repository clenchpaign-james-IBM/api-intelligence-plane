"""
E2E tests for conversational context awareness (User Story 4).

Tests multi-turn conversations with reference resolution and entity tracking.

Feature: 002-agentic-query
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.context_manager import ContextManager, get_context_manager
from app.models.agent import QueryContext


@pytest.fixture
def context_manager():
    """Create a fresh context manager for each test."""
    manager = ContextManager(ttl_hours=1)
    yield manager
    # Cleanup
    manager.clear_all()


@pytest.mark.asyncio
async def test_multi_turn_conversation(context_manager):
    """
    Test multi-turn conversation maintains context across queries.
    
    Task: T074
    """
    session_id = uuid4()
    
    # First query: "Show me all APIs"
    context_manager.add_query_to_history(session_id, "Show me all APIs")
    context_manager.track_entity(session_id, "api", "api-1")
    context_manager.track_entity(session_id, "api", "api-2")
    context_manager.cache_query_results(session_id, {
        "apis": [
            {"id": "api-1", "name": "Payment API"},
            {"id": "api-2", "name": "User API"}
        ]
    })
    
    # Verify first query context
    context = context_manager.get(session_id)
    assert context is not None
    assert len(context.query_history) == 1
    assert context.query_history[0] == "Show me all APIs"
    assert "api" in context.entity_mentions
    assert len(context.entity_mentions["api"]) == 2
    
    # Second query: "Which of those have vulnerabilities?"
    context_manager.add_query_to_history(session_id, "Which of those have vulnerabilities?")
    context_manager.track_entity(session_id, "vulnerability", "vuln-1")
    context_manager.track_entity(session_id, "vulnerability", "vuln-2")
    
    # Verify second query context
    context = context_manager.get(session_id)
    assert len(context.query_history) == 2
    assert context.query_history[1] == "Which of those have vulnerabilities?"
    assert "vulnerability" in context.entity_mentions
    assert len(context.entity_mentions["vulnerability"]) == 2
    
    # Third query: "Show me more details about the vulnerable ones"
    context_manager.add_query_to_history(session_id, "Show me more details about the vulnerable ones")
    
    # Verify third query context
    context = context_manager.get(session_id)
    assert len(context.query_history) == 3
    # Should still have access to all previous entities
    assert len(context.entity_mentions["api"]) == 2
    assert len(context.entity_mentions["vulnerability"]) == 2


@pytest.mark.asyncio
async def test_reference_resolution(context_manager):
    """
    Test reference resolution for pronouns like "those", "them", "it".
    
    Task: T075
    """
    session_id = uuid4()
    
    # First query establishes entities
    context_manager.add_query_to_history(session_id, "Show me critical vulnerabilities")
    context_manager.track_entity(session_id, "vulnerability", "vuln-1")
    context_manager.track_entity(session_id, "vulnerability", "vuln-2")
    context_manager.track_entity(session_id, "vulnerability", "vuln-3")
    
    # Cache results for reference resolution
    context_manager.cache_query_results(session_id, {
        "vulnerabilities": [
            {"id": "vuln-1", "severity": "critical"},
            {"id": "vuln-2", "severity": "critical"},
            {"id": "vuln-3", "severity": "critical"}
        ]
    })
    
    # Second query uses reference "those"
    context_manager.add_query_to_history(session_id, "Which APIs are affected by those?")
    
    # Verify context has the referenced entities
    context = context_manager.get(session_id)
    vulnerabilities = context_manager.get_entities_by_type(session_id, "vulnerability")
    assert len(vulnerabilities) == 3
    assert "vuln-1" in vulnerabilities
    assert "vuln-2" in vulnerabilities
    assert "vuln-3" in vulnerabilities
    
    # Cached results should be available for reference resolution
    cached_results = context_manager.get_cached_results(session_id)
    assert cached_results is not None
    assert "vulnerabilities" in cached_results
    assert len(cached_results["vulnerabilities"]) == 3


@pytest.mark.asyncio
async def test_entity_tracking_across_queries(context_manager):
    """
    Test entity tracking across multiple queries in a session.
    
    Task: T076
    """
    session_id = uuid4()
    
    # Query 1: Track gateways
    context_manager.add_query_to_history(session_id, "Show me all gateways")
    context_manager.track_entity(session_id, "gateway", "gw-1")
    context_manager.track_entity(session_id, "gateway", "gw-2")
    
    # Query 2: Track APIs
    context_manager.add_query_to_history(session_id, "Show me APIs in gateway gw-1")
    context_manager.track_entity(session_id, "api", "api-1")
    context_manager.track_entity(session_id, "api", "api-2")
    context_manager.track_entity(session_id, "api", "api-3")
    
    # Query 3: Track vulnerabilities
    context_manager.add_query_to_history(session_id, "Show me vulnerabilities in those APIs")
    context_manager.track_entity(session_id, "vulnerability", "vuln-1")
    context_manager.track_entity(session_id, "vulnerability", "vuln-2")
    
    # Verify all entities are tracked
    all_entities = context_manager.get_all_entities(session_id)
    assert "gateway" in all_entities
    assert len(all_entities["gateway"]) == 2
    assert "api" in all_entities
    assert len(all_entities["api"]) == 3
    assert "vulnerability" in all_entities
    assert len(all_entities["vulnerability"]) == 2
    
    # Verify entity retrieval by type
    gateways = context_manager.get_entities_by_type(session_id, "gateway")
    assert len(gateways) == 2
    assert "gw-1" in gateways
    assert "gw-2" in gateways
    
    apis = context_manager.get_entities_by_type(session_id, "api")
    assert len(apis) == 3
    
    vulnerabilities = context_manager.get_entities_by_type(session_id, "vulnerability")
    assert len(vulnerabilities) == 2


@pytest.mark.asyncio
async def test_context_expiration(context_manager):
    """
    Test context expiration after 1-hour TTL.
    
    Task: T077
    """
    session_id = uuid4()
    
    # Create context
    context_manager.add_query_to_history(session_id, "Show me all APIs")
    context_manager.track_entity(session_id, "api", "api-1")
    
    # Verify context exists
    context = context_manager.get(session_id)
    assert context is not None
    assert len(context.query_history) == 1
    
    # Manually set last_updated to simulate expiration
    context.last_updated = datetime.utcnow() - timedelta(hours=2)
    context_manager.update(session_id, context)
    
    # Trigger cleanup
    expired_count = context_manager._cleanup_expired()
    assert expired_count == 1
    
    # Verify context is removed
    context = context_manager.get(session_id)
    assert context is None


@pytest.mark.asyncio
async def test_query_history_max_limit(context_manager):
    """Test that query history maintains max 10 entries."""
    session_id = uuid4()
    
    # Add 15 queries
    for i in range(15):
        context_manager.add_query_to_history(session_id, f"Query {i+1}")
    
    # Verify only last 10 are kept
    history = context_manager.get_query_history(session_id)
    assert len(history) == 10
    assert history[0] == "Query 6"  # First 5 should be dropped
    assert history[-1] == "Query 15"


@pytest.mark.asyncio
async def test_context_stats(context_manager):
    """Test context manager statistics."""
    # Create multiple sessions
    session1 = uuid4()
    session2 = uuid4()
    session3 = uuid4()
    
    context_manager.add_query_to_history(session1, "Query 1")
    context_manager.add_query_to_history(session2, "Query 2")
    context_manager.add_query_to_history(session3, "Query 3")
    
    # Get stats
    stats = context_manager.get_stats()
    assert stats["total_contexts"] == 3
    assert stats["active_contexts"] == 3
    assert stats["expired_contexts"] == 0
    
    # Expire one context
    context = context_manager.get(session1)
    context.last_updated = datetime.utcnow() - timedelta(hours=2)
    context_manager.update(session1, context)
    
    # Check stats again
    stats = context_manager.get_stats()
    assert stats["total_contexts"] == 3
    assert stats["active_contexts"] == 2
    assert stats["expired_contexts"] == 1


@pytest.mark.asyncio
async def test_context_cleanup_task(context_manager):
    """Test background cleanup task."""
    # Start cleanup task
    await context_manager.start_cleanup_task(interval_minutes=1)
    assert context_manager.cleanup_task is not None
    
    # Stop cleanup task
    await context_manager.stop_cleanup_task()
    assert context_manager.cleanup_task is None


@pytest.mark.asyncio
async def test_duplicate_entity_tracking(context_manager):
    """Test that duplicate entities are not added multiple times."""
    session_id = uuid4()
    
    # Track same entity multiple times
    context_manager.track_entity(session_id, "api", "api-1")
    context_manager.track_entity(session_id, "api", "api-1")
    context_manager.track_entity(session_id, "api", "api-1")
    
    # Verify only one instance
    apis = context_manager.get_entities_by_type(session_id, "api")
    assert len(apis) == 1
    assert apis[0] == "api-1"


@pytest.mark.asyncio
async def test_context_clear_all(context_manager):
    """Test clearing all contexts."""
    # Create multiple sessions
    for i in range(5):
        session_id = uuid4()
        context_manager.add_query_to_history(session_id, f"Query {i+1}")
    
    # Verify contexts exist
    stats = context_manager.get_stats()
    assert stats["total_contexts"] == 5
    
    # Clear all
    cleared_count = context_manager.clear_all()
    assert cleared_count == 5
    
    # Verify all cleared
    stats = context_manager.get_stats()
    assert stats["total_contexts"] == 0


@pytest.mark.asyncio
async def test_global_context_manager():
    """Test global context manager singleton."""
    manager1 = get_context_manager()
    manager2 = get_context_manager()
    
    # Should be same instance
    assert manager1 is manager2
    
    # Test functionality
    session_id = uuid4()
    manager1.add_query_to_history(session_id, "Test query")
    
    # Should be accessible from manager2
    history = manager2.get_query_history(session_id)
    assert len(history) == 1
    assert history[0] == "Test query"
    
    # Cleanup
    manager1.clear_all()

# Made with Bob
