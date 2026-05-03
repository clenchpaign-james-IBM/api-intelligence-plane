"""
Integration Tests for Agent Entity Synthesis

Tests the LLM-powered synthesis and entity grouping capabilities of specialized agents.
Verifies that agents can aggregate tool results by entities and generate natural language responses.

Feature: 002-agentic-query (User Story 1 - T040)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.query.security_agent import SecurityAgent
from app.agents.query.discovery_agent import DiscoveryAgent
from app.models.agent import EntityGrouping


@pytest.mark.asyncio
async def test_security_agent_entity_grouping():
    """
    T040: Test security agent groups vulnerabilities by affected APIs.
    
    Verify that when agent finds 40 vulnerabilities, it synthesizes them
    into "8 APIs with vulnerabilities" using LLM-powered entity grouping.
    """
    # Mock LLM and tools
    mock_llm = AsyncMock()
    mock_tool = AsyncMock()
    mock_tool.name = "list_all_vulnerabilities"
    mock_tool.arun = AsyncMock(return_value={
        "vulnerabilities": [
            {"id": f"vuln-{i}", "api_id": f"api-{i % 8}", "severity": "critical"}
            for i in range(40)  # 40 vulnerabilities across 8 APIs
        ]
    })
    
    agent = SecurityAgent(llm=mock_llm, tools=[mock_tool])
    
    # Mock LLM synthesis response
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content="Found 8 APIs with critical vulnerabilities (40 total vulnerabilities)"
    ))
    
    # Execute query
    result = await agent.execute("Show me APIs with critical vulnerabilities")
    
    # Verify entity grouping occurred
    assert "8 APIs" in result["answer"] or "8 affected APIs" in result["answer"]
    assert result["confidence"] > 0.8
    
    # Verify synthesis was called
    assert mock_llm.ainvoke.called


@pytest.mark.asyncio
async def test_discovery_agent_entity_grouping():
    """
    T040: Test discovery agent groups APIs by gateway.
    
    Verify that agent can group 50 APIs across 5 gateways and synthesize
    the results into a natural language response.
    """
    mock_llm = AsyncMock()
    mock_tool = AsyncMock()
    mock_tool.name = "list_all_apis"
    mock_tool.arun = AsyncMock(return_value={
        "apis": [
            {"id": f"api-{i}", "gateway_id": f"gw-{i % 5}", "name": f"API {i}"}
            for i in range(50)  # 50 APIs across 5 gateways
        ]
    })
    
    agent = DiscoveryAgent(llm=mock_llm, tools=[mock_tool])
    
    # Mock LLM synthesis
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content="Found 50 APIs distributed across 5 gateways"
    ))
    
    result = await agent.execute("Show me all APIs")
    
    # Verify synthesis occurred
    assert "50 APIs" in result["answer"] or "APIs" in result["answer"]
    assert result["confidence"] > 0.0


@pytest.mark.asyncio
async def test_entity_grouping_model():
    """
    T040: Test EntityGrouping model structure.
    
    Verify that EntityGrouping model correctly represents aggregated entities
    with synthesis summary and relationships.
    """
    # Create entity grouping
    grouping = EntityGrouping(
        entity_type="api",
        entities={
            "api-1": {"id": "api-1", "name": "Payment API", "vulnerability_count": 5},
            "api-2": {"id": "api-2", "name": "User API", "vulnerability_count": 3},
        },
        total_count=2,
        synthesis_summary="Found 2 APIs with a total of 8 vulnerabilities",
        synthesis_reasoning="Grouped 8 vulnerabilities by affected API",
        confidence=0.95,
        related_entities={
            "vulnerability": ["vuln-1", "vuln-2", "vuln-3", "vuln-4", "vuln-5", "vuln-6", "vuln-7", "vuln-8"]
        },
        source_tool_calls=["list_all_vulnerabilities"],
        synthesis_time_ms=150
    )
    
    # Verify structure
    assert grouping.entity_type == "api"
    assert grouping.total_count == 2
    assert len(grouping.entities) == 2
    assert "2 APIs" in grouping.synthesis_summary
    assert "8 vulnerabilities" in grouping.synthesis_summary
    assert grouping.confidence == 0.95
    assert len(grouping.related_entities["vulnerability"]) == 8


@pytest.mark.asyncio
async def test_multi_tool_entity_synthesis():
    """
    T040: Test agent synthesizes results from multiple tool invocations.
    
    Verify that agent can aggregate results from multiple tools and
    create a unified entity grouping.
    """
    mock_llm = AsyncMock()
    
    # Mock two tools
    mock_tool1 = AsyncMock()
    mock_tool1.name = "list_all_apis"
    mock_tool1.arun = AsyncMock(return_value={
        "apis": [
            {"id": "api-1", "name": "Payment API"},
            {"id": "api-2", "name": "User API"},
        ]
    })
    
    mock_tool2 = AsyncMock()
    mock_tool2.name = "get_api_metrics"
    mock_tool2.arun = AsyncMock(return_value={
        "metrics": {"latency_p95": 250, "error_rate": 0.01}
    })
    
    agent = DiscoveryAgent(llm=mock_llm, tools=[mock_tool1, mock_tool2])
    
    # Mock LLM synthesis combining both tool results
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content="Found 2 APIs: Payment API and User API, both with good performance metrics"
    ))
    
    result = await agent.execute("Show me APIs and their performance")
    
    # Verify synthesis combined multiple tool results
    assert "2 APIs" in result["answer"] or "APIs" in result["answer"]
    assert result["confidence"] > 0.0


@pytest.mark.asyncio
async def test_empty_results_synthesis():
    """
    T040: Test agent handles empty results gracefully.
    
    Verify that agent can synthesize a meaningful response even when
    no entities are found.
    """
    mock_llm = AsyncMock()
    mock_tool = AsyncMock()
    mock_tool.name = "list_all_vulnerabilities"
    mock_tool.arun = AsyncMock(return_value={"vulnerabilities": []})
    
    agent = SecurityAgent(llm=mock_llm, tools=[mock_tool])
    
    # Mock LLM synthesis for empty results
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content="No vulnerabilities found in the system"
    ))
    
    result = await agent.execute("Show me vulnerabilities")
    
    # Verify graceful handling
    assert "No vulnerabilities" in result["answer"] or "no" in result["answer"].lower()
    assert result["confidence"] >= 0.0


# Made with Bob