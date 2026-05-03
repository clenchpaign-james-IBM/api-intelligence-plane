"""
Router Tool Abstraction Layer - Tool Registry

This module provides auto-discovery and registration of router tools.
The registry maintains a catalog of all available tools and their metadata.

Feature: 001-agentic-query
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Type

from fastapi.params import Query as FastAPIQuery
from pydantic import BaseModel, create_model
from pydantic_core import PydanticUndefined

from app.tools.base_tool import RouterTool, ToolMetadata, ToolParameter
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """
    Registry for auto-discovering and registering router tools.
    
    The registry provides:
    - Auto-discovery of router methods marked as tools
    - Tool metadata cataloging
    - Tool lookup by name or domain
    - Dynamic tool schema generation
    
    Usage:
        registry = ToolRegistry()
        registry.register_tool(my_tool)
        tool = registry.get_tool("tool_name")
    """

    def __init__(self):
        """Initialize the tool registry."""
        self.tools: Dict[str, RouterTool] = {}
        self.metadata: Dict[str, ToolMetadata] = {}
        
        # T036: Tool usage metrics for search API adoption tracking
        self.tool_invocation_count: Dict[str, int] = {}
        self.search_tool_invocations: int = 0
        self.list_tool_invocations: int = 0
        
        logger.info("Tool registry initialized")

    def register_tool(
        self,
        tool: RouterTool,
        metadata: Optional[ToolMetadata] = None
    ) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: The RouterTool instance to register
            metadata: Optional metadata for the tool
        """
        if tool.name in self.tools:
            logger.warning(
                f"Tool {tool.name} already registered, overwriting",
                extra={"tool_name": tool.name}
            )
        
        self.tools[tool.name] = tool
        
        if metadata:
            self.metadata[tool.name] = metadata
        
        logger.info(
            f"Tool {tool.name} registered",
            extra={
                "tool_name": tool.name,
                "description": tool.description,
            }
        )

    def get_tool(self, name: str) -> Optional[RouterTool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            RouterTool instance or None if not found
        """
        return self.tools.get(name)

    def get_tools_by_domain(self, domain: str) -> List[RouterTool]:
        """
        Get all tools for a specific agent domain.
        
        Args:
            domain: Agent domain (e.g., "security", "metrics")
            
        Returns:
            List of RouterTool instances for the domain
        """
        tools = []
        for tool_name, tool_metadata in self.metadata.items():
            if domain in tool_metadata.agent_domains:
                tool = self.tools.get(tool_name)
                if tool:
                    tools.append(tool)
        return tools

    def get_all_tools(self) -> List[RouterTool]:
        """
        Get all registered tools.
        
        Returns:
            List of all RouterTool instances
        """
        return list(self.tools.values())

    def get_tool_names(self) -> List[str]:
        """
        Get names of all registered tools.
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())

    def get_tool_metadata(self, name: str) -> Optional[ToolMetadata]:
        """
        Get metadata for a tool.
        
        Args:
            name: Tool name
            
        Returns:
            ToolMetadata or None if not found
        """
        return self.metadata.get(name)

    def create_tool_from_method(
        self,
        method: Callable,
        name: str,
        description: str,
        agent_domains: Optional[List[str]] = None
    ) -> RouterTool:
        """
        Create a RouterTool from a router method using type hints.
        
        This method inspects the router method's signature and generates
        a Pydantic schema for parameter validation.
        
        Args:
            method: The router method to wrap
            name: Tool name
            description: Tool description
            agent_domains: List of agent domains that can use this tool
            
        Returns:
            RouterTool instance
        """
        sig = inspect.signature(method)
        
        # Generate Pydantic schema from type hints
        fields = {}
        parameters = []
        
        for param_name, param in sig.parameters.items():
            # Skip 'self' and 'request' parameters
            if param_name in ['self', 'request']:
                continue
            
            # Skip FastAPI Depends() parameters (dependency injection)
            if param.default != inspect.Parameter.empty:
                # Check if default is a Depends() call
                default_str = str(param.default)
                if 'Depends' in default_str or 'depends' in default_str:
                    continue
            
            # Get parameter type annotation
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                param_type = Any
            
            # Extract actual default value from FastAPI Query/Path/Body objects
            actual_default = param.default
            if param.default != inspect.Parameter.empty:
                # Check if it's a FastAPI Query/Path/Body/etc parameter
                if isinstance(param.default, FastAPIQuery):
                    # Extract the actual default value from the Query object
                    actual_default = param.default.default
                    # If the Query has no default (PydanticUndefined or Ellipsis), mark as required
                    if actual_default is PydanticUndefined or actual_default is ...:
                        actual_default = inspect.Parameter.empty
                elif hasattr(param.default, 'default'):
                    # Handle other FastAPI parameter types (Path, Body, etc.)
                    actual_default = param.default.default
                    if actual_default is PydanticUndefined or actual_default is ...:
                        actual_default = inspect.Parameter.empty
            
            # Determine if parameter is required
            required = actual_default == inspect.Parameter.empty
            
            # Add to Pydantic fields
            if required:
                fields[param_name] = (param_type, ...)
            else:
                fields[param_name] = (param_type, actual_default)
            
            # Add to parameter metadata
            parameters.append(
                ToolParameter(
                    name=param_name,
                    type=str(param_type),
                    required=required,
                    description=f"Parameter {param_name}",
                    default=None if required else actual_default
                )
            )
        
        # Create Pydantic input schema
        InputSchema = create_model(
            f"{name}Input",
            **fields
        )
        
        # Create tool metadata
        metadata = ToolMetadata(
            name=name,
            description=description,
            router_method=f"{method.__module__}.{method.__name__}",
            agent_domains=agent_domains or [],
            parameters=parameters
        )
        
        # Create RouterTool subclass dynamically
        class DynamicRouterTool(RouterTool):
            pass
        
        # Create tool instance
        tool = DynamicRouterTool(
            name=name,
            description=description,
            router_method=method,
            args_schema=InputSchema
        )
        
        # Register tool with metadata
        self.register_tool(tool, metadata)
        
        return tool

    def register_from_module(
        self,
        module: Any,
        tool_prefix: str = "tool_"
    ) -> int:
        """
        Auto-discover and register tools from a module.
        
        Looks for functions with a specific prefix or decorator.
        
        Args:
            module: Python module to scan
            tool_prefix: Prefix for tool functions
            
        Returns:
            Number of tools registered
        """
        count = 0
        
        for name, obj in inspect.getmembers(module):
            # Check if it's a function with the tool prefix
            if inspect.isfunction(obj) and name.startswith(tool_prefix):
                tool_name = name[len(tool_prefix):]
                description = obj.__doc__ or f"Tool: {tool_name}"
                
                try:
                    self.create_tool_from_method(
                        method=obj,
                        name=tool_name,
                        description=description
                    )
                    count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to register tool {tool_name}",
                        extra={"error": str(e)},
                        exc_info=True
                    )
        
        logger.info(
            f"Registered {count} tools from module {module.__name__}",
            extra={"module": module.__name__, "count": count}
        )
        
        return count

    def clear(self) -> None:
        """Clear all registered tools."""
        self.tools.clear()
        self.metadata.clear()
        logger.info("Tool registry cleared")

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self.tools)

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self.tools


# Global tool registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Returns:
        ToolRegistry singleton instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


    def record_tool_invocation(self, tool_name: str) -> None:
        """
        T036: Record a tool invocation for metrics tracking.
        
        This method tracks which tools are being used most frequently,
        with special attention to search vs list tool adoption.
        
        Args:
            tool_name: Name of the tool that was invoked
        """
        # Increment total invocation count for this tool
        self.tool_invocation_count[tool_name] = (
            self.tool_invocation_count.get(tool_name, 0) + 1
        )
        
        # Track search vs list tool usage
        if "search" in tool_name.lower():
            self.search_tool_invocations += 1
        elif "list" in tool_name.lower():
            self.list_tool_invocations += 1
        
        logger.debug(
            f"Tool invocation recorded: {tool_name}",
            extra={
                "tool_name": tool_name,
                "total_invocations": self.tool_invocation_count[tool_name],
            }
        )
    
    def get_tool_usage_statistics(self) -> Dict[str, Any]:
        """
        T036: Get tool usage statistics for monitoring search API adoption.
        
        Returns statistics about which tools are used most frequently,
        with focus on search vs list tool adoption rates.
        
        Returns:
            Dictionary containing:
            - tool_invocations: Per-tool invocation counts
            - search_tool_invocations: Total search tool invocations
            - list_tool_invocations: Total list tool invocations
            - search_adoption_rate: Percentage of search vs list+search
            - top_tools: Top 10 most-used tools
            - search_tools_ranking: Ranking of search tools by usage
        """
        total_search_and_list = self.search_tool_invocations + self.list_tool_invocations
        search_adoption_rate = (
            (self.search_tool_invocations / total_search_and_list * 100)
            if total_search_and_list > 0
            else 0.0
        )
        
        # Get top 10 most-used tools
        sorted_tools = sorted(
            self.tool_invocation_count.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_tools = dict(sorted_tools[:10])
        
        # Get search tools ranking
        search_tools = {
            name: count
            for name, count in self.tool_invocation_count.items()
            if "search" in name.lower()
        }
        search_tools_ranking = dict(
            sorted(search_tools.items(), key=lambda x: x[1], reverse=True)
        )
        
        return {
            "tool_invocations": self.tool_invocation_count.copy(),
            "search_tool_invocations": self.search_tool_invocations,
            "list_tool_invocations": self.list_tool_invocations,
            "total_search_and_list": total_search_and_list,
            "search_adoption_rate": round(search_adoption_rate, 2),
            "top_tools": top_tools,
            "search_tools_ranking": search_tools_ranking,
        }
    
    def get_search_tool_adoption_metrics(self) -> Dict[str, Any]:
        """
        T036: Get specific metrics for search API adoption tracking.
        
        This method provides focused metrics on search API usage to measure
        the impact of User Story 5 (Enhanced Search APIs).
        
        Returns:
            Dictionary containing:
            - search_gateways_count: Invocations of search_gateways
            - search_apis_count: Invocations of search_apis_global
            - search_vulnerabilities_count: Invocations of search_vulnerabilities
            - search_compliance_violations_count: Invocations of search_compliance_violations
            - search_recommendations_count: Invocations of search_recommendations
            - search_predictions_count: Invocations of search_predictions
            - total_search_invocations: Sum of all search tool invocations
            - search_vs_list_ratio: Ratio of search to list tool usage
        """
        search_tools_map = {
            "search_gateways": self.tool_invocation_count.get("search_gateways", 0),
            "search_apis_global": self.tool_invocation_count.get("search_apis_global", 0),
            "search_vulnerabilities": self.tool_invocation_count.get("search_vulnerabilities", 0),
            "search_compliance_violations": self.tool_invocation_count.get("search_compliance_violations", 0),
            "search_recommendations": self.tool_invocation_count.get("search_recommendations", 0),
            "search_predictions": self.tool_invocation_count.get("search_predictions", 0),
        }
        
        total_search = sum(search_tools_map.values())
        search_vs_list_ratio = (
            (self.search_tool_invocations / self.list_tool_invocations)
            if self.list_tool_invocations > 0
            else float('inf') if self.search_tool_invocations > 0 else 0.0
        )
        
        return {
            **search_tools_map,
            "total_search_invocations": total_search,
            "total_list_invocations": self.list_tool_invocations,
            "search_vs_list_ratio": round(search_vs_list_ratio, 2),
        }
# Made with Bob
