"""
Router Tool Abstraction Layer - Gateway Management Tools

This module provides tool wrappers for gateway management operations.
Tools wrap backend router methods for direct invocation by agents.

Feature: 001-agentic-query
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.tools.base_tool import RouterTool, RouterToolInput


# Tool input schemas will be defined based on tool-schemas.yaml
# For now, creating placeholder structure

class ListGatewaysInput(RouterToolInput):
    """Input schema for list_gateways tool."""
    page: Optional[int] = Field(default=1, description="Page number")
    page_size: Optional[int] = Field(default=20, description="Items per page")
    status: Optional[str] = Field(default=None, description="Filter by status")


# Gateway tools will be registered dynamically by the tool registry
# based on the tool-schemas.yaml configuration file

# Placeholder for future implementation:
# - create_gateway
# - list_gateways  
# - get_gateway
# - update_gateway
# - delete_gateway
# - test_gateway_connection
# - sync_gateway_apis
# - get_gateway_health
# - get_gateway_metrics
# - configure_gateway_policies

# Made with Bob
