"""
Integration Tests for Multi-Agent Collaboration (User Story 2)

Tests the coordinator's ability to orchestrate multiple specialized agents
for complex cross-domain queries.

Feature: 002-agentic-query
Tasks: T052-T055
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from app.agents.query.coordinator_agent import CoordinatorAgent
from app.models.agent import AgentType


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = AsyncMock()
    return llm


@pytest.fixture
def mock_agents():
    """Mock specialized agents."""
    agents = {}
    
    for agent_type in [AgentType.DISCOVERY, AgentType.METRICS, AgentType.SECURITY]:
        agent = AsyncMock()
        agent.execute = AsyncMock(return_value={
            "success": True,
            "confidence": 0.9,
            "answer": f"Results from {agent_type.value} agent",
            "data": {
                "apis": [
                    {
                        "id": "api-1",
                        "name": f"API from {agent_type.value}",
                        "status": "active",
                    }
                ]
            },
            "tool_calls": [f"{agent_type.value}_tool"],
            "execution_time_ms": 100,
        })
        agents[agent_type] = agent
    
    return agents


@pytest.fixture
def coordinator(mock_llm, mock_agents):
    """Create coordinator with mocked dependencies."""
    return CoordinatorAgent(
        llm=mock_llm,
        agents=mock_agents,
        verbose=True,
    )


class TestParallelAgentExecution:
    """T052: Test parallel agent execution."""
    
    @pytest.mark.asyncio
    async def test_parallel_execution_success(self, coordinator, mock_agents):
        """Test successful parallel execution of multiple agents."""
        # Arrange
        sub_queries = {
            AgentType.METRICS: "Find APIs with high latency",
            AgentType.SECURITY: "Find APIs with vulnerabilities",
        }
        
        # Act
        results = await coordinator.execute_parallel_agents(
            sub_queries=sub_queries,
            context={},
            timeout=10.0,
        )
        
        # Assert
        assert len(results) == 2
        assert AgentType.METRICS in results
        assert AgentType.SECURITY in results
        assert results[AgentType.METRICS]["success"] is True
        assert results[AgentType.SECURITY]["success"] is True
        
        # Verify both agents were called
        mock_agents[AgentType.METRICS].execute.assert_called_once()
        mock_agents[AgentType.SECURITY].execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parallel_execution_with_timeout(self, coordinator, mock_agents):
        """Test parallel execution handles timeout correctly."""
        # Arrange
        sub_queries = {
            AgentType.METRICS: "Find APIs with high latency",
        }
        
        # Make agent execution slow
        async def slow_execute(*args, **kwargs):
            import asyncio
            await asyncio.sleep(2)
            return {"success": True}
        
        mock_agents[AgentType.METRICS].execute = slow_execute
        
        # Act
        results = await coordinator.execute_parallel_agents(
            sub_queries=sub_queries,
            context={},
            timeout=0.5,  # Short timeout
        )
        
        # Assert - should return timeout error
        assert AgentType.METRICS in results
        assert results[AgentType.METRICS]["success"] is False
        assert "timed out" in results[AgentType.METRICS]["error"].lower()
    
    @pytest.mark.asyncio
    async def test_parallel_execution_with_agent_failure(self, coordinator, mock_agents):
        """Test parallel execution handles individual agent failures."""
        # Arrange
        sub_queries = {
            AgentType.METRICS: "Find APIs with high latency",
            AgentType.SECURITY: "Find APIs with vulnerabilities",
        }
        
        # Make one agent fail
        mock_agents[AgentType.METRICS].execute = AsyncMock(
            side_effect=Exception("Agent execution failed")
        )
        
        # Act
        results = await coordinator.execute_parallel_agents(
            sub_queries=sub_queries,
            context={},
            timeout=10.0,
        )
        
        # Assert
        assert len(results) == 2
        assert results[AgentType.METRICS]["success"] is False
        assert "Agent execution failed" in results[AgentType.METRICS]["error"]
        assert results[AgentType.SECURITY]["success"] is True


class TestSequentialAgentExecution:
    """T053: Test sequential agent execution."""
    
    @pytest.mark.asyncio
    async def test_sequential_execution_with_dependencies(self, coordinator, mock_agents):
        """Test sequential execution respects dependencies."""
        # Arrange
        sub_queries = {
            AgentType.DISCOVERY: "Find all APIs",
            AgentType.METRICS: "Get metrics for discovered APIs",
        }
        dependencies = {
            AgentType.METRICS: [AgentType.DISCOVERY],  # Metrics depends on discovery
        }
        
        # Act
        results = await coordinator.execute_sequential_agents(
            sub_queries=sub_queries,
            dependencies=dependencies,
            context={},
        )
        
        # Assert
        assert len(results) == 2
        assert AgentType.DISCOVERY in results
        assert AgentType.METRICS in results
        
        # Verify execution order (discovery called before metrics)
        discovery_call = mock_agents[AgentType.DISCOVERY].execute.call_args
        metrics_call = mock_agents[AgentType.METRICS].execute.call_args
        
        # Metrics should have discovery results in context
        metrics_context = metrics_call[1]["context"]
        assert "discovery_results" in metrics_context
    
    @pytest.mark.asyncio
    async def test_sequential_execution_context_enrichment(self, coordinator, mock_agents):
        """Test that sequential execution enriches context with previous results."""
        # Arrange
        sub_queries = {
            AgentType.DISCOVERY: "Find all APIs",
            AgentType.SECURITY: "Check security for discovered APIs",
        }
        dependencies = {
            AgentType.SECURITY: [AgentType.DISCOVERY],
        }
        
        # Act
        results = await coordinator.execute_sequential_agents(
            sub_queries=sub_queries,
            dependencies=dependencies,
            context={"initial": "context"},
        )
        
        # Assert
        security_call = mock_agents[AgentType.SECURITY].execute.call_args
        security_context = security_call[1]["context"]
        
        # Should have initial context
        assert security_context["initial"] == "context"
        
        # Should have discovery results
        assert "discovery_results" in security_context
        assert security_context["discovery_results"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_sequential_execution_handles_failure(self, coordinator, mock_agents):
        """Test sequential execution continues after agent failure."""
        # Arrange
        sub_queries = {
            AgentType.DISCOVERY: "Find all APIs",
            AgentType.METRICS: "Get metrics",
        }
        dependencies = {}
        
        # Make first agent fail
        mock_agents[AgentType.DISCOVERY].execute = AsyncMock(
            side_effect=Exception("Discovery failed")
        )
        
        # Act
        results = await coordinator.execute_sequential_agents(
            sub_queries=sub_queries,
            dependencies=dependencies,
            context={},
        )
        
        # Assert
        assert len(results) == 2
        assert results[AgentType.DISCOVERY]["success"] is False
        assert results[AgentType.METRICS]["success"] is True


class TestEntityCorrelation:
    """T054: Test entity correlation across agents."""
    
    def test_correlate_results_by_entity_id(self, coordinator):
        """Test correlation of results by entity ID."""
        # Arrange
        agent_results = {
            AgentType.METRICS: {
                "success": True,
                "data": {
                    "apis": [
                        {"id": "api-1", "name": "API 1", "latency": 500},
                        {"id": "api-2", "name": "API 2", "latency": 200},
                    ]
                },
            },
            AgentType.SECURITY: {
                "success": True,
                "data": {
                    "vulnerabilities": [
                        {"id": "vuln-1", "api_id": "api-1", "severity": "high"},
                    ]
                },
            },
        }
        
        # Act
        correlated = coordinator.correlate_results_by_entity(agent_results)
        
        # Assert
        assert "api-1" in correlated
        assert "api-2" in correlated
        assert "vuln-1" in correlated
        
        # API-1 should have data from both agents
        api1 = correlated["api-1"]
        assert "metrics" in api1["agent_data"]
        assert api1["agent_data"]["metrics"]["latency"] == 500
    
    def test_correlate_handles_missing_entities(self, coordinator):
        """Test correlation handles entities without IDs."""
        # Arrange
        agent_results = {
            AgentType.METRICS: {
                "success": True,
                "data": {
                    "apis": [
                        {"name": "API without ID"},  # No ID
                    ]
                },
            },
        }
        
        # Act
        correlated = coordinator.correlate_results_by_entity(agent_results)
        
        # Assert - should not crash, just skip entities without IDs
        assert isinstance(correlated, dict)
    
    def test_correlate_handles_failed_agents(self, coordinator):
        """Test correlation skips failed agent results."""
        # Arrange
        agent_results = {
            AgentType.METRICS: {
                "success": False,
                "error": "Agent failed",
            },
            AgentType.SECURITY: {
                "success": True,
                "data": {
                    "vulnerabilities": [
                        {"id": "vuln-1", "severity": "high"},
                    ]
                },
            },
        }
        
        # Act
        correlated = coordinator.correlate_results_by_entity(agent_results)
        
        # Assert - should only have security results
        assert "vuln-1" in correlated
        assert len(correlated) == 1


class TestConflictResolution:
    """T055: Test conflict resolution in multi-agent results."""
    
    def test_resolve_conflicts_with_inconsistent_status(self, coordinator):
        """Test conflict resolution when agents report different statuses."""
        # Arrange
        agent_results = {
            AgentType.DISCOVERY: {
                "success": True,
                "data": {
                    "apis": [
                        {"id": "api-1", "name": "API 1", "status": "active"},
                    ]
                },
            },
            AgentType.METRICS: {
                "success": True,
                "data": {
                    "apis": [
                        {"id": "api-1", "name": "API 1", "status": "degraded"},
                    ]
                },
            },
        }
        
        # Act
        resolved = coordinator.resolve_conflicts(agent_results)
        
        # Assert
        assert "conflicts" in resolved
        assert len(resolved["conflicts"]) > 0
        
        # Should detect status conflict
        conflict = resolved["conflicts"][0]
        assert conflict["entity_id"] == "api-1"
        assert conflict["field"] == "status"
        assert "active" in conflict["values"].values()
        assert "degraded" in conflict["values"].values()
    
    def test_resolve_conflicts_merges_consistent_data(self, coordinator):
        """Test that consistent data is merged without conflicts."""
        # Arrange
        agent_results = {
            AgentType.DISCOVERY: {
                "success": True,
                "data": {
                    "apis": [
                        {"id": "api-1", "name": "API 1", "status": "active"},
                    ]
                },
            },
            AgentType.METRICS: {
                "success": True,
                "data": {
                    "apis": [
                        {"id": "api-1", "latency": 500},
                    ]
                },
            },
        }
        
        # Act
        resolved = coordinator.resolve_conflicts(agent_results)
        
        # Assert
        assert "resolved_entities" in resolved
        assert "api-1" in resolved["resolved_entities"]
        
        # Should merge data from both agents
        api1 = resolved["resolved_entities"]["api-1"]
        assert "name" in api1
        assert "latency" in api1
        
        # No conflicts expected
        assert resolved["conflict_count"] == 0
    
    def test_resolve_conflicts_handles_single_agent(self, coordinator):
        """Test conflict resolution with single agent (no conflicts possible)."""
        # Arrange
        agent_results = {
            AgentType.DISCOVERY: {
                "success": True,
                "data": {
                    "apis": [
                        {"id": "api-1", "name": "API 1", "status": "active"},
                    ]
                },
            },
        }
        
        # Act
        resolved = coordinator.resolve_conflicts(agent_results)
        
        # Assert
        assert resolved["conflict_count"] == 0
        assert "api-1" in resolved["resolved_entities"]


# Made with Bob