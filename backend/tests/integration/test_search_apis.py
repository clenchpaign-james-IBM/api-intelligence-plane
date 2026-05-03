"""
Integration tests for search API tools (User Story 5).

Tests that search tools are properly registered and can be invoked by agents.

Feature: 002-agentic-query
"""

import pytest
from uuid import uuid4

from app.tools.tool_registry import get_tool_registry
from app.models.agent import AgentType


@pytest.fixture
def tool_registry():
    """Get the global tool registry."""
    return get_tool_registry()


@pytest.mark.asyncio
async def test_search_apis_tool_registered(tool_registry):
    """
    Test that search_apis_global tool is registered and accessible.
    
    Task: T087
    """
    # Verify tool is registered
    tools = tool_registry.get_tools_for_agent(AgentType.DISCOVERY)
    tool_names = [tool.name for tool in tools]
    
    assert "search_apis_global" in tool_names, "search_apis_global tool should be registered"
    
    # Get the tool
    search_tool = next((t for t in tools if t.name == "search_apis_global"), None)
    assert search_tool is not None
    
    # Verify tool has proper description
    assert "search" in search_tool.description.lower()
    assert "api" in search_tool.description.lower()
    
    # Verify tool has args_schema
    assert search_tool.args_schema is not None


@pytest.mark.asyncio
async def test_search_gateways_tool_registered(tool_registry):
    """
    Test that search_gateways tool is registered and accessible.
    
    Task: T088
    """
    # Verify tool is registered
    tools = tool_registry.get_tools_for_agent(AgentType.DISCOVERY)
    tool_names = [tool.name for tool in tools]
    
    assert "search_gateways" in tool_names, "search_gateways tool should be registered"
    
    # Get the tool
    search_tool = next((t for t in tools if t.name == "search_gateways"), None)
    assert search_tool is not None
    
    # Verify tool has proper description
    assert "search" in search_tool.description.lower()
    assert "gateway" in search_tool.description.lower()


@pytest.mark.asyncio
async def test_search_vulnerabilities_tool_registered(tool_registry):
    """
    Test that search_vulnerabilities tool is registered and accessible.
    
    Task: T089
    """
    # Verify tool is registered
    tools = tool_registry.get_tools_for_agent(AgentType.SECURITY)
    tool_names = [tool.name for tool in tools]
    
    assert "search_vulnerabilities" in tool_names, "search_vulnerabilities tool should be registered"
    
    # Get the tool
    search_tool = next((t for t in tools if t.name == "search_vulnerabilities"), None)
    assert search_tool is not None
    
    # Verify tool has proper description
    assert "search" in search_tool.description.lower()
    assert "vulnerabilit" in search_tool.description.lower()


@pytest.mark.asyncio
async def test_search_compliance_violations_tool_registered(tool_registry):
    """Test that search_compliance_violations tool is registered."""
    tools = tool_registry.get_tools_for_agent(AgentType.COMPLIANCE)
    tool_names = [tool.name for tool in tools]
    
    assert "search_compliance_violations" in tool_names


@pytest.mark.asyncio
async def test_search_recommendations_tool_registered(tool_registry):
    """Test that search_recommendations tool is registered."""
    tools = tool_registry.get_tools_for_agent(AgentType.OPTIMIZATION)
    tool_names = [tool.name for tool in tools]
    
    assert "search_recommendations" in tool_names


@pytest.mark.asyncio
async def test_search_predictions_tool_registered(tool_registry):
    """Test that search_predictions tool is registered."""
    tools = tool_registry.get_tools_for_agent(AgentType.PREDICTION)
    tool_names = [tool.name for tool in tools]
    
    assert "search_predictions" in tool_names


@pytest.mark.asyncio
async def test_agent_prefers_search_over_list_for_complex_queries(tool_registry):
    """
    Test that agents have access to both search and list tools,
    allowing LLM to choose the most appropriate one.
    
    Task: T090
    """
    # Discovery agent should have both list and search tools
    discovery_tools = tool_registry.get_tools_for_agent(AgentType.DISCOVERY)
    tool_names = [tool.name for tool in discovery_tools]
    
    # Should have list tools
    assert "list_gateways" in tool_names
    assert "list_all_apis" in tool_names
    
    # Should also have search tools
    assert "search_gateways" in tool_names
    assert "search_apis_global" in tool_names
    
    # Security agent should have both list and search tools
    security_tools = tool_registry.get_tools_for_agent(AgentType.SECURITY)
    tool_names = [tool.name for tool in security_tools]
    
    # Should have list tools
    assert "list_all_vulnerabilities" in tool_names
    
    # Should also have search tools
    assert "search_vulnerabilities" in tool_names


@pytest.mark.asyncio
async def test_search_tool_descriptions_guide_llm(tool_registry):
    """
    Test that search tool descriptions clearly indicate when to use them
    vs list tools.
    """
    # Get search_apis_global tool
    discovery_tools = tool_registry.get_tools_for_agent(AgentType.DISCOVERY)
    search_apis_tool = next((t for t in discovery_tools if t.name == "search_apis_global"), None)
    
    assert search_apis_tool is not None
    description = search_apis_tool.description.lower()
    
    # Description should mention when to use search vs list
    assert "when to use" in description or "important" in description
    
    # Should mention search capabilities
    assert "pattern" in description or "filter" in description or "search" in description


@pytest.mark.asyncio
async def test_search_tools_have_proper_parameters(tool_registry):
    """Test that search tools have appropriate parameters for filtering."""
    # Test search_apis_global parameters
    discovery_tools = tool_registry.get_tools_for_agent(AgentType.DISCOVERY)
    search_apis_tool = next((t for t in discovery_tools if t.name == "search_apis_global"), None)
    
    assert search_apis_tool is not None
    assert search_apis_tool.args_schema is not None
    
    # Should have name pattern parameter
    schema_fields = search_apis_tool.args_schema.model_fields
    assert "name" in schema_fields or "query" in schema_fields or "pattern" in schema_fields


@pytest.mark.asyncio
async def test_search_tool_usage_tracking(tool_registry):
    """Test that search tool invocations are tracked."""
    # Get initial stats
    initial_stats = tool_registry.get_search_tool_stats()
    
    # Stats should include search tool counters
    assert "search_gateways" in initial_stats or "search_gateways_count" in str(initial_stats)
    assert "search_apis_global" in initial_stats or "search_apis_count" in str(initial_stats)
    assert "search_vulnerabilities" in initial_stats or "search_vulnerabilities_count" in str(initial_stats)


@pytest.mark.asyncio
async def test_all_agent_types_have_search_tools(tool_registry):
    """Test that all relevant agent types have search tools available."""
    agent_search_tools = {
        AgentType.DISCOVERY: ["search_gateways", "search_apis_global"],
        AgentType.SECURITY: ["search_vulnerabilities"],
        AgentType.COMPLIANCE: ["search_compliance_violations"],
        AgentType.OPTIMIZATION: ["search_recommendations"],
        AgentType.PREDICTION: ["search_predictions"],
    }
    
    for agent_type, expected_tools in agent_search_tools.items():
        tools = tool_registry.get_tools_for_agent(agent_type)
        tool_names = [tool.name for tool in tools]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, \
                f"{agent_type.value} agent should have {expected_tool} tool"


@pytest.mark.asyncio
async def test_search_tools_support_wildcards(tool_registry):
    """Test that search tool descriptions mention wildcard support."""
    discovery_tools = tool_registry.get_tools_for_agent(AgentType.DISCOVERY)
    search_gateways_tool = next((t for t in discovery_tools if t.name == "search_gateways"), None)
    
    assert search_gateways_tool is not None
    description = search_gateways_tool.description.lower()
    
    # Should mention pattern matching or wildcards
    assert "pattern" in description or "wildcard" in description or "*" in description


@pytest.mark.asyncio
async def test_search_tools_support_date_filters(tool_registry):
    """Test that search tools support date range filtering."""
    discovery_tools = tool_registry.get_tools_for_agent(AgentType.DISCOVERY)
    search_apis_tool = next((t for t in discovery_tools if t.name == "search_apis_global"), None)
    
    assert search_apis_tool is not None
    
    # Check if args_schema has date-related fields
    if search_apis_tool.args_schema:
        schema_fields = search_apis_tool.args_schema.model_fields
        date_fields = [f for f in schema_fields.keys() if "date" in f.lower() or "created" in f.lower() or "updated" in f.lower()]
        
        # Should have at least one date-related field
        assert len(date_fields) > 0, "Search tool should support date filtering"


@pytest.mark.asyncio
async def test_search_tools_support_severity_filters(tool_registry):
    """Test that security search tools support severity filtering."""
    security_tools = tool_registry.get_tools_for_agent(AgentType.SECURITY)
    search_vuln_tool = next((t for t in security_tools if t.name == "search_vulnerabilities"), None)
    
    assert search_vuln_tool is not None
    
    # Check if args_schema has severity field
    if search_vuln_tool.args_schema:
        schema_fields = search_vuln_tool.args_schema.model_fields
        assert "severity" in schema_fields, "Vulnerability search should support severity filtering"

# Made with Bob
