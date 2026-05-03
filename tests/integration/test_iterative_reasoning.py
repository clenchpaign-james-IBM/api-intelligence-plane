"""
Integration Tests for Iterative Coordinator Reasoning

Tests the coordinator's ability to iterate through multi-step queries,
evaluating after each tool invocation and dynamically deciding next steps.

Feature: 002-agentic-query (User Story 6)
Tasks: T021-T026
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.agents.query.coordinator_agent import CoordinatorAgent
from app.models.agent import AgentType, CoordinatorState
from app.models.query import QueryContext


@pytest.mark.asyncio
async def test_single_iteration_workflow():
    """
    T021: Test single iteration workflow
    
    Verify coordinator can complete a simple query in one iteration.
    """
    # Mock LLM and agents
    mock_llm = AsyncMock()
    mock_discovery_agent = AsyncMock()
    mock_discovery_agent.execute = AsyncMock(return_value={
        "success": True,
        "results": {"apis": [{"id": "api-1", "name": "Test API"}]},
        "confidence": 0.95
    })
    
    agents = {
        AgentType.DISCOVERY: mock_discovery_agent
    }
    
    coordinator = CoordinatorAgent(llm=mock_llm, agents=agents)
    
    # Mock LLM responses for single iteration
    mock_llm.ainvoke = AsyncMock(side_effect=[
        # Agent selection
        MagicMock(content='{"selected_agent": "discovery", "confidence": 0.95, "reasoning": "Simple API query"}'),
        # Completion evaluation
        MagicMock(content='{"is_complete": true, "confidence": 0.95, "reasoning": "Query answered"}')
    ])
    
    # Execute query
    result = await coordinator.execute_iterative_workflow("Show me all APIs")
    
    # Verify single iteration
    assert result["iterations"] == 1
    assert result["is_complete"] is True
    assert len(result["completed_steps"]) == 1
    assert mock_discovery_agent.execute.call_count == 1


@pytest.mark.asyncio
async def test_multi_step_gateway_to_apis():
    """
    T022: Test multi-step query (gateway name → APIs)
    
    Verify coordinator iterates: (1) resolve gateway name to ID, (2) fetch APIs for that gateway ID
    """
    mock_llm = AsyncMock()
    mock_discovery_agent = AsyncMock()
    
    # First call: resolve gateway name
    # Second call: fetch APIs for gateway
    mock_discovery_agent.execute = AsyncMock(side_effect=[
        {
            "success": True,
            "results": {"gateway": {"id": "gw-123", "name": "local"}},
            "confidence": 0.95
        },
        {
            "success": True,
            "results": {"apis": [{"id": "api-1"}, {"id": "api-2"}]},
            "confidence": 0.95
        }
    ])
    
    agents = {AgentType.DISCOVERY: mock_discovery_agent}
    coordinator = CoordinatorAgent(llm=mock_llm, agents=agents)
    
    # Mock LLM responses for two iterations
    mock_llm.ainvoke = AsyncMock(side_effect=[
        # Iteration 1: Agent selection
        MagicMock(content='{"selected_agent": "discovery", "confidence": 0.95, "reasoning": "Need to resolve gateway name"}'),
        # Iteration 1: Completion evaluation (not complete)
        MagicMock(content='{"is_complete": false, "confidence": 0.5, "reasoning": "Need to fetch APIs for gateway"}'),
        # Iteration 2: Agent selection
        MagicMock(content='{"selected_agent": "discovery", "confidence": 0.95, "reasoning": "Fetch APIs for gateway"}'),
        # Iteration 2: Completion evaluation (complete)
        MagicMock(content='{"is_complete": true, "confidence": 0.95, "reasoning": "Query fully answered"}')
    ])
    
    result = await coordinator.execute_iterative_workflow("Show APIs managed by gateway 'local'")
    
    # Verify two iterations
    assert result["iterations"] == 2
    assert result["is_complete"] is True
    assert len(result["completed_steps"]) == 2
    assert "Resolved gateway 'local'" in str(result["completed_steps"])
    assert "Fetched APIs" in str(result["completed_steps"])
    assert len(result["results"]["apis"]) == 2


@pytest.mark.asyncio
async def test_multi_step_gateway_vulnerabilities_apis():
    """
    T023: Test multi-step query (gateway → vulnerabilities → APIs)
    
    Verify coordinator iterates through three steps to answer complex query.
    """
    mock_llm = AsyncMock()
    mock_discovery_agent = AsyncMock()
    mock_security_agent = AsyncMock()
    
    # Step 1: Resolve gateway
    # Step 2: Fetch vulnerabilities
    # Step 3: Group by APIs
    mock_discovery_agent.execute = AsyncMock(return_value={
        "success": True,
        "results": {"gateway": {"id": "gw-123", "name": "local"}},
        "confidence": 0.95
    })
    
    mock_security_agent.execute = AsyncMock(side_effect=[
        {
            "success": True,
            "results": {
                "vulnerabilities": [
                    {"id": "vuln-1", "api_id": "api-1"},
                    {"id": "vuln-2", "api_id": "api-2"}
                ]
            },
            "confidence": 0.92
        },
        {
            "success": True,
            "results": {
                "apis": [
                    {"id": "api-1", "vulnerability_count": 1},
                    {"id": "api-2", "vulnerability_count": 1}
                ]
            },
            "confidence": 0.95
        }
    ])
    
    agents = {
        AgentType.DISCOVERY: mock_discovery_agent,
        AgentType.SECURITY: mock_security_agent
    }
    coordinator = CoordinatorAgent(llm=mock_llm, agents=agents)
    
    # Mock LLM for 3 iterations
    mock_llm.ainvoke = AsyncMock(side_effect=[
        # Iteration 1
        MagicMock(content='{"selected_agent": "discovery", "confidence": 0.95, "reasoning": "Resolve gateway"}'),
        MagicMock(content='{"is_complete": false, "confidence": 0.3, "reasoning": "Need vulnerabilities"}'),
        # Iteration 2
        MagicMock(content='{"selected_agent": "security", "confidence": 0.92, "reasoning": "Fetch vulnerabilities"}'),
        MagicMock(content='{"is_complete": false, "confidence": 0.6, "reasoning": "Need to group by APIs"}'),
        # Iteration 3
        MagicMock(content='{"selected_agent": "security", "confidence": 0.95, "reasoning": "Group by APIs"}'),
        MagicMock(content='{"is_complete": true, "confidence": 0.95, "reasoning": "Complete"}')
    ])
    
    result = await coordinator.execute_iterative_workflow(
        "Show insecure APIs managed by gateway 'local'"
    )
    
    assert result["iterations"] == 3
    assert result["is_complete"] is True
    assert len(result["completed_steps"]) == 3


@pytest.mark.asyncio
async def test_loop_prevention_max_iterations():
    """
    T024: Test loop prevention (max 10 iterations)
    
    Verify coordinator stops after max iterations to prevent infinite loops.
    """
    mock_llm = AsyncMock()
    mock_discovery_agent = AsyncMock()
    mock_discovery_agent.execute = AsyncMock(return_value={
        "success": True,
        "results": {"data": "some data"},
        "confidence": 0.7
    })
    
    agents = {AgentType.DISCOVERY: mock_discovery_agent}
    coordinator = CoordinatorAgent(llm=mock_llm, agents=agents)
    
    # Mock LLM to always say "not complete" to trigger max iterations
    mock_llm.ainvoke = AsyncMock(side_effect=[
        # Repeat for 10 iterations
        *[MagicMock(content='{"selected_agent": "discovery", "confidence": 0.7, "reasoning": "Try again"}') for _ in range(10)],
        *[MagicMock(content='{"is_complete": false, "confidence": 0.5, "reasoning": "Still not complete"}') for _ in range(10)]
    ])
    
    result = await coordinator.execute_iterative_workflow("Complex ambiguous query")
    
    # Should stop at max iterations
    assert result["iterations"] == 10
    assert result["is_complete"] is False
    assert "max_iterations_reached" in result.get("termination_reason", "")


@pytest.mark.asyncio
async def test_llm_based_completion_decision():
    """
    T025: Test LLM-based completion decision
    
    Verify LLM evaluates completion after each iteration.
    """
    mock_llm = AsyncMock()
    mock_discovery_agent = AsyncMock()
    mock_discovery_agent.execute = AsyncMock(return_value={
        "success": True,
        "results": {"apis": [{"id": "api-1"}]},
        "confidence": 0.95
    })
    
    agents = {AgentType.DISCOVERY: mock_discovery_agent}
    coordinator = CoordinatorAgent(llm=mock_llm, agents=agents)
    
    # Track LLM calls
    llm_calls = []
    
    async def track_llm_call(messages):
        call_content = messages[-1].content if messages else ""
        llm_calls.append(call_content)
        
        # First call: agent selection
        if "select" in call_content.lower() or len(llm_calls) == 1:
            return MagicMock(content='{"selected_agent": "discovery", "confidence": 0.95, "reasoning": "Get APIs"}')
        # Second call: completion evaluation
        else:
            return MagicMock(content='{"is_complete": true, "confidence": 0.95, "reasoning": "Query answered"}')
    
    mock_llm.ainvoke = track_llm_call
    
    result = await coordinator.execute_iterative_workflow("Show me all APIs")
    
    # Verify LLM was called for both agent selection AND completion evaluation
    assert len(llm_calls) >= 2
    assert result["is_complete"] is True
    assert result["completion_confidence"] > 0.9


@pytest.mark.asyncio
async def test_no_progress_detection():
    """
    T026: Test no-progress detection
    
    Verify coordinator stops if no new information is gathered.
    """
    mock_llm = AsyncMock()
    mock_discovery_agent = AsyncMock()
    
    # Return same results twice (no progress)
    mock_discovery_agent.execute = AsyncMock(return_value={
        "success": True,
        "results": {"apis": [{"id": "api-1"}]},
        "confidence": 0.7
    })
    
    agents = {AgentType.DISCOVERY: mock_discovery_agent}
    coordinator = CoordinatorAgent(llm=mock_llm, agents=agents)
    
    # Mock LLM to say "not complete" but agent returns same data
    mock_llm.ainvoke = AsyncMock(side_effect=[
        # Iteration 1
        MagicMock(content='{"selected_agent": "discovery", "confidence": 0.7, "reasoning": "Get APIs"}'),
        MagicMock(content='{"is_complete": false, "confidence": 0.5, "reasoning": "Need more"}'),
        # Iteration 2 (same results)
        MagicMock(content='{"selected_agent": "discovery", "confidence": 0.7, "reasoning": "Try again"}'),
        MagicMock(content='{"is_complete": false, "confidence": 0.5, "reasoning": "Still need more"}')
    ])
    
    result = await coordinator.execute_iterative_workflow("Show APIs")
    
    # Should detect no progress and stop
    assert result["iterations"] <= 3  # Should stop early
    assert "no_progress" in result.get("termination_reason", "").lower() or result["is_complete"]


# Made with Bob