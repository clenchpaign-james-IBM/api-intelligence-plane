
"""
Tool Registry Initialization

This module initializes and registers all backend router methods as LangChain-compatible
tools for use by AI agents in the agentic query system.

Tools are organized by functional domain:
- Gateway Management (10 tools)
- API Discovery & Inventory (5 tools)
- Metrics & Analytics (6 tools)
- Security (10 tools)
- Compliance (5 tools)
- Optimization (15 tools)
- Predictions (5 tools)

Total: 53 tools for agent use (query service tools excluded)

Each tool wraps a backend router method and provides:
- Detailed description with Args, Returns, and Example sections
- Type-safe parameter validation via Pydantic models
- Domain mapping for agent specialization
- Zero network overhead (direct Python function calls)
"""

import logging
from typing import Optional

from app.api.v1 import (
    gateways,
    apis,
    metrics,
    security,
    compliance,
    optimization,
    predictions,
    # NOTE: query module NOT imported to avoid circular dependency
    # (query.py imports initialize_tools at module level)
)
from app.tools.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

# Global tool registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def initialize_tools() -> ToolRegistry:
    """
    Initialize and register all backend router methods as LangChain tools.
    
    This function is called once at application startup to register all available
    tools with the tool registry. Each tool is mapped to one or more agent domains
    based on its functionality.
    
    Returns:
        ToolRegistry: Initialized registry with all tools registered
    """
    registry = get_tool_registry()
    
    logger.info("Initializing tool registry with backend router methods")
    
    # ============================================================================
    # Gateway Management Tools (10 tools)
    # ============================================================================
    
    registry.create_tool_from_method(
        method=gateways.create_gateway,
        name="create_gateway",
        description="""Create and register a new API Gateway in the system.
        
        Registers a gateway with initial DISCONNECTED status. Use connect_gateway
        to establish connection after registration. Supports multiple gateway vendors
        including Kong, Apigee, AWS API Gateway, Azure API Management, MuleSoft, and webMethods.
        
        Args:
            name: Human-readable gateway name
            vendor: Gateway vendor (native, kong, apigee, aws, azure, mulesoft, webmethods)
            base_url: Gateway base URL for API management endpoints
            version: Optional gateway version string
            base_url_credential_type: Authentication type (none, api_key, basic, bearer)
            base_url_api_key: API key if credential_type is "api_key"
            
        Returns:
            dict: Created gateway with:
                - id: Gateway UUID
                - name: Gateway name
                - vendor: Gateway vendor
                - status: Initial status (DISCONNECTED)
                - created_at: Creation timestamp
                
        Example:
            >>> result = await create_gateway(
            ...     name="Production Kong Gateway",
            ...     vendor="kong",
            ...     base_url="https://api.example.com:8001",
            ...     base_url_credential_type="api_key",
            ...     base_url_api_key="kong-admin-key"
            ... )
            >>> print(f"Gateway created: {result['id']}")
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=gateways.list_gateways,
        name="list_gateways",
        description="""List all registered API Gateways with pagination and filtering.
        
        Returns paginated list of gateways with optional status filtering.
        Useful for discovering available gateways and their current connection status.
        
        IMPORTANT: When user asks for "connected gateways", "active gateways", or "online gateways",
        you MUST set status_filter="connected". When they ask for "disconnected" or "offline" gateways,
        set status_filter="disconnected". When they ask for gateways with errors, set status_filter="error".
        
        Args:
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-100, default: 20)
            status_filter: Optional status filter. Valid values:
                - "connected": Only return gateways that are currently connected
                - "disconnected": Only return gateways that are disconnected
                - "error": Only return gateways with connection errors
                - None (default): Return all gateways regardless of status
            
        Returns:
            dict: Paginated gateway list with:
                - items: List of gateway objects with id, name, vendor, status, etc.
                - total: Total gateway count matching the filter
                - page: Current page number
                - page_size: Items per page
                
        Example for connected gateways:
            >>> result = await list_gateways(page=1, page_size=10, status_filter="connected")
            >>> print(f"Found {result['total']} connected gateways")
            
        Example for all gateways:
            >>> result = await list_gateways(page=1, page_size=20)
            >>> print(f"Found {result['total']} total gateways")
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=gateways.get_gateway,
        name="get_gateway",
        description="""Get detailed information about a specific API Gateway.
        
        Retrieves complete gateway configuration including connection status,
        credentials, capabilities, and metadata.
        
        Args:
            gateway_id: Gateway UUID (required)
            
        Returns:
            dict: Gateway details with:
                - id: Gateway UUID
                - name: Gateway name
                - vendor: Gateway vendor
                - status: Connection status
                - base_url: Management endpoint URL
                - capabilities: Supported features
                - api_count: Number of discovered APIs
                - last_connected_at: Last successful connection timestamp
                - last_error: Most recent error message if any
                
        Example:
            >>> gateway = await get_gateway(gateway_id="550e8400-e29b-41d4-a716-446655440000")
            >>> print(f"Gateway: {gateway['name']} ({gateway['status']})")
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=gateways.update_gateway,
        name="update_gateway",
        description="""Update API Gateway configuration settings.
        
        Allows updating gateway name, version, base URL, credentials, and other
        configuration parameters. Only provided fields are updated.
        
        Args:
            gateway_id: Gateway UUID (required)
            name: New gateway name (optional)
            version: New version string (optional)
            base_url: New base URL (optional)
            status: New status (optional, use connect/disconnect instead)
            
        Returns:
            dict: Updated gateway object
            
        Example:
            >>> result = await update_gateway(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     name="Production Kong Gateway v2",
            ...     version="2.8.0"
            ... )
            >>> print(f"Updated gateway: {result['name']}")
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=gateways.connect_gateway,
        name="connect_gateway",
        description="""Establish connection to a Gateway and validate credentials.
        
        Tests connectivity, validates credentials, and updates gateway status to CONNECTED
        on success. Required before performing API discovery or sync operations.
        
        Args:
            gateway_id: Gateway UUID (required)
            
        Returns:
            dict: Updated gateway with:
                - status: CONNECTED on success
                - last_connected_at: Connection timestamp
                - last_error: None on success
                
        Example:
            >>> result = await connect_gateway(gateway_id="550e8400-e29b-41d4-a716-446655440000")
            >>> print(f"Connection status: {result['status']}")
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=gateways.disconnect_gateway,
        name="disconnect_gateway",
        description="""Disconnect from an API Gateway.
        
        Updates gateway status to DISCONNECTED. Gateway remains registered but inactive.
        No API discovery or sync operations can be performed while disconnected.
        
        Args:
            gateway_id: Gateway UUID (required)
            
        Returns:
            dict: Updated gateway with DISCONNECTED status
            
        Example:
            >>> result = await disconnect_gateway(gateway_id="550e8400-e29b-41d4-a716-446655440000")
            >>> print(f"Gateway disconnected: {result['name']}")
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=gateways.delete_gateway,
        name="delete_gateway",
        description="""Permanently delete an API Gateway from the system.
        
        Removes gateway and all associated data. This operation cannot be undone.
        Gateway must be disconnected before deletion.
        
        Args:
            gateway_id: Gateway UUID (required)
            
        Returns:
            dict: Deletion confirmation with:
                - success: True if deleted
                - message: Confirmation message
                - gateway_id: Deleted gateway UUID
                - gateway_name: Deleted gateway name
                
        Example:
            >>> result = await delete_gateway(gateway_id="550e8400-e29b-41d4-a716-446655440000")
            >>> print(result['message'])
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=gateways.sync_gateway,
        name="sync_gateway",
        description="""Trigger API discovery and synchronization from a Gateway.
        
        Discovers APIs from the gateway, updates API inventory, detects shadow APIs,
        and synchronizes policy configurations. Can force refresh even if recently synced.
        
        Args:
            gateway_id: Gateway UUID (required)
            force_refresh: Force refresh even if recently synced (default: False)
            
        Returns:
            dict: Sync results with:
                - success: True if sync completed
                - apis_discovered: Total APIs found
                - new_apis: Newly discovered APIs
                - updated_apis: APIs with changes
                - shadow_apis_found: Undocumented APIs detected
                - timestamp: Sync completion time
                
        Example:
            >>> result = await sync_gateway(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     force_refresh=True
            ... )
            >>> print(f"Discovered {result['apis_discovered']} APIs, {result['shadow_apis_found']} shadow APIs")
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=gateways.test_gateway_connection,
        name="test_gateway_connection",
        description="""Test gateway connection without saving configuration.
        
        Tests connectivity and credential validation without creating a gateway record.
        Useful for validating configuration before registration.
        
        Args:
            name: Gateway name
            vendor: Gateway vendor
            base_url: Gateway base URL
            base_url_credential_type: Authentication type
            base_url_api_key: API key if applicable
            
        Returns:
            dict: Test results with:
                - connected: Boolean success status
                - latency_ms: Connection latency
                - message: Status message
                - error: Error details if failed
                
        Example:
            >>> result = await test_gateway_connection(
            ...     name="Test Gateway",
            ...     vendor="kong",
            ...     base_url="https://api.example.com:8001",
            ...     base_url_credential_type="api_key",
            ...     base_url_api_key="test-key"
            ... )
            >>> print(f"Connection: {result['connected']}")
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=gateways.bulk_sync_gateways,
        name="bulk_sync_gateways",
        description="""Synchronize multiple API Gateways in parallel for efficiency.
        
        Performs parallel API discovery across multiple gateways. Each gateway is synced
        independently with aggregated results. Maximum 50 gateways per request.
        
        Args:
            gateway_ids: List of gateway UUIDs (max 50)
            force_refresh: Force refresh for all gateways (default: False)
            
        Returns:
            dict: Bulk sync results with:
                - total: Number of gateways processed
                - successful: Successfully synced count
                - failed: Failed sync count
                - total_apis_discovered: Aggregate API count
                - total_new_apis: Aggregate new APIs
                - total_updated_apis: Aggregate updated APIs
                - total_shadow_apis_found: Aggregate shadow APIs
                - duration_seconds: Total execution time
                - results: Per-gateway sync results
                
        Example:
            >>> result = await bulk_sync_gateways(
            ...     gateway_ids=["550e8400-e29b-41d4-a716-446655440000", "660e8400-e29b-41d4-a716-446655440001"],
            ...     force_refresh=False
            ... )
            >>> print(f"Synced {result['successful']}/{result['total']} gateways in {result['duration_seconds']}s")
        """,
        agent_domains=["discovery"]
    )
    registry.create_tool_from_method(
        method=gateways.search_gateways,
        name="search_gateways",
        description="""Search API Gateways with flexible multi-criteria filtering.
        
        Use this tool when you need to find gateways matching multiple criteria simultaneously,
        such as name patterns combined with vendor or status filters. Prefer this over list_gateways
        when the query involves text patterns or multiple filter combinations.
        
        IMPORTANT: When to use search_gateways vs list_gateways:
        - Use search_gateways for: name patterns, vendor + status combinations, date ranges
        - Use list_gateways for: simple status-only filters, getting all gateways
        
        Args:
            name: Gateway name pattern (case-insensitive wildcard, e.g., "prod*" or "*kong*")
            vendor: Filter by gateway vendor (native, kong, apigee, aws, azure, mulesoft, webmethods)
            status: Filter by connection status (connected, disconnected, error)
            created_after: Filter gateways created after this date (ISO 8601 format)
            created_before: Filter gateways created before this date (ISO 8601 format)
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-100, default: 20)
            
        Returns:
            dict: Paginated gateway list with:
                - items: List of matching gateways
                - total: Total matching gateways
                - page: Current page number
                - page_size: Items per page
                
        Example:
            >>> # Find production Kong gateways that are connected
            >>> result = await search_gateways(
            ...     name="prod*",
            ...     vendor="kong",
            ...     status="connected"
            ... )
            >>> print(f"Found {result['total']} production Kong gateways")
            
            >>> # Find gateways created in the last week
            >>> result = await search_gateways(
            ...     created_after="2024-01-01T00:00:00Z"
            ... )
        """,
        agent_domains=["discovery"]
    )
    
    
    # ============================================================================
    # API Discovery & Inventory Tools (5 tools)
    # ============================================================================
    
    registry.create_tool_from_method(
        method=apis.list_all_apis,
        name="list_all_apis",
        description="""List all APIs across all gateways with comprehensive filtering.
        
        Aggregate endpoint returning APIs from all gateways. Supports filtering by
        gateway, status, shadow API detection, and health score thresholds.
        
        Args:
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-1000, default: 20)
            gateway_id: Optional gateway filter
            status: Optional status filter (active, inactive, deprecated, failed)
            is_shadow: Filter shadow APIs (true/false)
            health_score_min: Minimum health score (0.0-1.0)
            
        Returns:
            dict: Paginated API list with:
                - items: List of API objects
                - total: Total API count
                - page: Current page
                - page_size: Items per page
                
        Example:
            >>> result = await list_all_apis(
            ...     page=1,
            ...     page_size=50,
            ...     status="active",
            ...     health_score_min=0.8
            ... )
            >>> print(f"Found {result['total']} healthy active APIs")
        """,
        agent_domains=["discovery", "metrics"]
    )
    
    registry.create_tool_from_method(
        method=apis.list_gateway_apis,
        name="list_apis",
        description="""List APIs for a specific Gateway with filtering options.
        
        Returns APIs belonging to a single gateway with optional status, shadow API,
        and health score filtering.
        
        Args:
            gateway_id: Gateway UUID (required)
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-1000, default: 20)
            status: Optional status filter (active, inactive, deprecated, failed)
            is_shadow: Filter shadow APIs (true/false)
            health_score_min: Minimum health score (0.0-1.0)
            
        Returns:
            dict: Paginated API list for the gateway
            
        Example:
            >>> result = await list_apis(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     is_shadow=True
            ... )
            >>> print(f"Found {result['total']} shadow APIs")
        """,
        agent_domains=["discovery", "metrics"]
    )
    
    registry.create_tool_from_method(
        method=apis.search_gateway_apis,
        name="search_apis",
        description="""Search APIs within a gateway using OpenSearch full-text search.
        
        Uses multi_match query with fuzzy matching for better results. Searches across
        name, base_path, description, and tags fields with weighted relevance scoring.
        
        Args:
            gateway_id: Gateway UUID (required)
            q: Search query string
            limit: Maximum results (1-1000, default: 100)
            status: Optional status filter
            is_shadow: Optional shadow API filter
            
        Returns:
            dict: Search results with:
                - results: Matching APIs with relevance scores
                - total: Total matches
                - query: Original search query
                
        Example:
            >>> result = await search_apis(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     q="payment processing",
            ...     limit=20
            ... )
            >>> print(f"Found {result['total']} APIs matching 'payment processing'")
        """,
        agent_domains=["discovery"]
    )
    
    registry.create_tool_from_method(
        method=apis.get_gateway_api,
        name="get_api",
        description="""Get complete details of a specific API including policies and metrics.
        
        Retrieves full API configuration, policy actions, intelligence metadata,
        and current health status.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: API UUID (required)
            
        Returns:
            dict: Complete API details with:
                - id: API UUID
                - name: API name
                - base_path: API base path
                - status: Current status
                - policy_actions: Applied policies
                - intelligence_metadata: Health score, shadow API status
                - created_at: Discovery timestamp
                - updated_at: Last update timestamp
                
        Example:
            >>> api = await get_api(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     api_id="660e8400-e29b-41d4-a716-446655440001"
            ... )
            >>> print(f"API: {api['name']} (Health: {api['intelligence_metadata']['health_score']})")
        """,
        agent_domains=["discovery", "metrics", "security"]
    )
    
    registry.create_tool_from_method(
        method=apis.get_gateway_api_security_policies,
        name="get_api_security_policies",
        description="""Get security-related policy actions configured for an API.
        
        Derives security policies from API's policy_actions field, filtering for
        security-related action types like authentication, authorization, rate limiting,
        TLS, validation, etc.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: API UUID (required)
            
        Returns:
            list: Security-related PolicyAction objects with:
                - action_type: Policy action type
                - configuration: Policy configuration
                - enabled: Whether policy is active
                
        Example:
            >>> policies = await get_api_security_policies(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     api_id="660e8400-e29b-41d4-a716-446655440001"
            ... )
            >>> print(f"Found {len(policies)} security policies")
        """,
        agent_domains=["security"]
    )
    registry.create_tool_from_method(
        method=apis.search_apis,
        name="search_apis_global",
        description="""Search APIs across all gateways with flexible multi-criteria filtering.
        
        Use this tool when you need to find APIs matching multiple criteria simultaneously,
        such as name patterns combined with authentication type, health score ranges, or date filters.
        This is a global search across all gateways - prefer this over list_all_apis for complex queries.
        
        IMPORTANT: When to use search_apis_global vs list_all_apis vs search_apis:
        - Use search_apis_global for: text patterns, multi-criteria filters, date ranges (across all gateways)
        - Use list_all_apis for: simple filters like status or gateway_id only
        - Use search_apis for: gateway-scoped full-text search with fuzzy matching
        
        Args:
            name: API name pattern (case-insensitive wildcard, e.g., "payment*" or "*api*")
            description: Description pattern (case-insensitive wildcard)
            status: Filter by API status (active, inactive, deprecated, failed)
            authentication_type: Filter by auth type (none, api_key, oauth2, jwt, basic, custom)
            is_shadow: Filter shadow APIs (true/false)
            health_score_min: Minimum health score (0.0-1.0)
            health_score_max: Maximum health score (0.0-1.0)
            gateway_id: Filter by specific gateway
            created_after: Filter APIs created after this date (ISO 8601 format)
            created_before: Filter APIs created before this date (ISO 8601 format)
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-100, default: 20)
            
        Returns:
            dict: Paginated API list with:
                - items: List of matching APIs
                - total: Total matching APIs
                - page: Current page number
                - page_size: Items per page
                
        Example:
            >>> # Find payment APIs created last week with authentication
            >>> result = await search_apis_global(
            ...     name="payment*",
            ...     authentication_type="oauth2",
            ...     created_after="2024-01-01T00:00:00Z"
            ... )
            >>> print(f"Found {result['total']} payment APIs with OAuth2")
            
            >>> # Find unhealthy shadow APIs
            >>> result = await search_apis_global(
            ...     is_shadow=True,
            ...     health_score_max=0.5
            ... )
        """,
        agent_domains=["discovery", "metrics"]
    )
    
    
    # ============================================================================
    # Metrics & Analytics Tools (6 tools)
    # ============================================================================
    
    registry.create_tool_from_method(
        method=metrics.get_analytics_metrics,
        name="get_analytics_metrics",
        description="""Get time-bucketed analytics metrics across all gateways or specific gateway.
        
        Returns aggregated metrics with configurable time bucket granularity (1m, 5m, 1h, 1d).
        Useful for dashboard analytics and trend analysis.
        
        Args:
            gateway_id: Optional gateway filter
            api_id: Optional API filter
            time_bucket: Time bucket size (1m, 5m, 1h, 1d, default: 1h)
            limit: Maximum results (1-1000, default: 50)
            
        Returns:
            dict: Time-bucketed metrics with:
                - items: List of metric data points
                - total: Total data points
                - time_bucket: Bucket granularity used
                
        Example:
            >>> result = await get_analytics_metrics(
            ...     time_bucket="1h",
            ...     limit=24
            ... )
            >>> print(f"Retrieved {result['total']} hourly metrics")
        """,
        agent_domains=["metrics"]
    )
    
    registry.create_tool_from_method(
        method=metrics.get_metrics_summary,
        name="get_metrics_summary",
        description="""Get aggregated metrics summary across all gateways for last 24 hours.
        
        Returns high-level performance summary including total requests, average response
        time, and error rate. Useful for quick health checks and dashboards.
        
        Args:
            gateway_id: Optional gateway filter
            
        Returns:
            dict: Summary metrics with:
                - total_requests_24h: Total requests in last 24 hours
                - avg_response_time: Average response time (ms)
                - avg_error_rate: Average error rate (%)
                
        Example:
            >>> summary = await get_metrics_summary()
            >>> print(f"24h: {summary['total_requests_24h']} requests, {summary['avg_response_time']}ms avg")
        """,
        agent_domains=["metrics"]
    )
    
    registry.create_tool_from_method(
        method=metrics.get_gateway_api_metrics,
        name="get_api_metrics",
        description="""Get time-bucketed performance metrics for a specific API.
        
        Returns detailed metrics including response times (avg, p50, p95, p99), throughput,
        error rates, cache hit rates, and timing breakdowns.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: API UUID (required)
            start_time: Start time (ISO 8601, default: 24 hours ago)
            end_time: End time (ISO 8601, default: now)
            time_bucket: Bucket size (1m, 5m, 1h, 1d, default: 5m)
            
        Returns:
            dict: API metrics with:
                - time_series: Time-bucketed data points
                - aggregated: Overall statistics
                - cache_metrics: Cache performance
                - timing_breakdown: Request timing analysis
                - status_breakdown: HTTP status distribution
                
        Example:
            >>> metrics = await get_api_metrics(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     api_id="660e8400-e29b-41d4-a716-446655440001",
            ...     time_bucket="5m"
            ... )
            >>> print(f"P95 latency: {metrics['aggregated']['response_time_p95']}ms")
        """,
        agent_domains=["metrics"]
    )
    
    registry.create_tool_from_method(
        method=metrics.drill_down_to_logs,
        name="drill_down_to_logs",
        description="""Drill down from analytics metric to source transactional logs.
        
        Traces a specific metric back to individual transactional logs that were aggregated
        to create it. Essential for debugging performance issues or investigating anomalies.
        
        Args:
            metric_id: Metric UUID (required)
            limit: Maximum logs to return (1-1000, default: 100)
            
        Returns:
            dict: Metric context and logs with:
                - metric_summary: Original metric details
                - time_range: Metric time window
                - logs: Individual transactional logs
                - total_logs: Total log count
                
        Example:
            >>> result = await drill_down_to_logs(
            ...     metric_id="770e8400-e29b-41d4-a716-446655440002",
            ...     limit=50
            ... )
            >>> print(f"Found {result['total_logs']} logs for metric")
        """,
        agent_domains=["metrics"]
    )
    
    registry.create_tool_from_method(
        method=metrics.drill_down_to_gateway_logs,
        name="drill_down_to_gateway_logs",
        description="""Drill down from gateway metric to transactional logs within gateway scope.
        
        Similar to drill_down_to_logs but scoped to a specific gateway. Useful for
        gateway-specific performance analysis.
        
        Args:
            gateway_id: Gateway UUID (required)
            metric_id: Metric UUID (required)
            limit: Maximum logs (1-1000, default: 100)
            
        Returns:
            dict: Gateway-scoped metric context and logs
            
        Example:
            >>> result = await drill_down_to_gateway_logs(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     metric_id="770e8400-e29b-41d4-a716-446655440002",
            ...     limit=100
            ... )
            >>> print(f"Retrieved {len(result['logs'])} logs")
        """,
        agent_domains=["metrics"]
    )
    
    registry.create_tool_from_method(
        method=metrics.get_gateway_metrics_summary,
        name="get_gateway_metrics_summary",
        description="""Get aggregated metrics summary for all APIs within a gateway.
        
        Returns gateway-level performance summary including API count, total requests,
        average response time, error rate, throughput, availability, and health scores.
        
        Args:
            gateway_id: Gateway UUID (required)
            status: Optional API status filter
            start_time: Start time (ISO 8601, default: 24 hours ago)
            end_time: End time (ISO 8601, default: now)
            
        Returns:
            dict: Gateway metrics summary with:
                - total_apis: Number of APIs
                - total_requests_24h: Total requests
                - avg_response_time: Average response time (ms)
                - avg_error_rate: Average error rate (%)
                - avg_throughput: Average throughput (req/s)
                - avg_availability: Average availability (%)
                - avg_health_score: Average health score (0-1)
                
        Example:
            >>> summary = await get_gateway_metrics_summary(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> print(f"Gateway: {summary['total_apis']} APIs, {summary['avg_health_score']} health")
        """,
        agent_domains=["metrics"]
    )
    
    # ============================================================================
    # Security Tools (10 tools)
    # ============================================================================
    
    registry.create_tool_from_method(
        method=security.get_security_summary,
        name="get_security_summary",
        description="""Get security summary with vulnerability counts across all gateways.
        
        Uses efficient OpenSearch aggregations to count vulnerabilities by severity.
        Provides quick overview of security posture.
        
        Args:
            gateway_id: Optional gateway filter
            
        Returns:
            dict: Vulnerability counts with:
                - total_vulnerabilities: Total count
                - critical_vulnerabilities: Critical severity count
                - high_vulnerabilities: High severity count
                - medium_vulnerabilities: Medium severity count
                - low_vulnerabilities: Low severity count
                
        Example:
            >>> summary = await get_security_summary()
            >>> print(f"Security: {summary['critical_vulnerabilities']} critical, {summary['high_vulnerabilities']} high")
        """,
        agent_domains=["security"]
    )
    
    registry.create_tool_from_method(
        method=security.get_vulnerabilities,
        name="list_all_vulnerabilities",
        description="""List security vulnerabilities across all gateways with comprehensive filtering.
        
        Returns vulnerabilities with optional filtering by gateway, API, status, and severity.
        Supports pagination for large result sets.
        
        IMPORTANT: When user asks for "critical vulnerabilities", "severe issues", or "urgent security problems",
        you MUST set severity="critical". For "high severity" or "important vulnerabilities", set severity="high".
        For "open vulnerabilities" or "unresolved issues", set status="open". For "resolved" or "fixed", set status="remediated".
        
        Args:
            gateway_id: Optional gateway filter
            api_id: Optional API filter
            status: Status filter. Valid values:
                - "open": Unresolved vulnerabilities requiring attention
                - "remediated": Fixed vulnerabilities
                - "in_progress": Vulnerabilities being fixed
                - "verified": Remediation verified as successful
                - None (default): All statuses
            severity: Severity filter. Valid values:
                - "critical": Critical severity vulnerabilities
                - "high": High severity vulnerabilities
                - "medium": Medium severity vulnerabilities
                - "low": Low severity vulnerabilities
                - None (default): All severities
            limit: Maximum results (1-1000, default: 100)
            
        Returns:
            list: Vulnerability objects with:
                - id: Vulnerability UUID
                - api_id: Affected API
                - vulnerability_type: Type of vulnerability
                - severity: Severity level
                - status: Current status
                - description: Detailed description
                - remediation_steps: Fix recommendations
                
        Example for critical open vulnerabilities:
            >>> vulns = await list_all_vulnerabilities(
            ...     severity="critical",
            ...     status="open",
            ...     limit=50
            ... )
            >>> print(f"Found {len(vulns)} open critical vulnerabilities")
            
        Example for all vulnerabilities:
            >>> vulns = await list_all_vulnerabilities(limit=100)
            >>> print(f"Found {len(vulns)} total vulnerabilities")
        """,
        agent_domains=["security"]
    )
    
    registry.create_tool_from_method(
        method=security.get_security_posture,
        name="get_security_posture",
        description="""Get comprehensive security posture metrics and risk score.
        
        Calculates overall security posture including vulnerability distribution,
        remediation rates, and risk scoring. Essential for security dashboards.
        
        Args:
            gateway_id: Optional gateway filter
            api_id: Optional API filter
            
        Returns:
            dict: Security posture with:
                - total_vulnerabilities: Total count
                - by_severity: Breakdown by severity
                - by_status: Breakdown by status
                - by_type: Breakdown by vulnerability type
                - remediation_rate: Percentage remediated
                - risk_score: Overall risk (0-100)
                - risk_level: Risk level (low/medium/high/critical)
                
        Example:
            >>> posture = await get_security_posture()
            >>> print(f"Risk Score: {posture['risk_score']}/100 ({posture['risk_level']})")
        """,
        agent_domains=["security"]
    )
    
    registry.create_tool_from_method(
        method=security.scan_gateway_api,
        name="scan_api_security",
        description="""Scan API for security vulnerabilities using hybrid rule-based and AI analysis.
        
        Performs comprehensive security scan combining deterministic rule-based checks
        with AI-enhanced context-aware severity assessment. Identifies missing security
        policies, misconfigurations, and potential vulnerabilities.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: API UUID (required)
            
        Returns:
            dict: Scan results with:
                - scan_id: Scan identifier
                - api_id: Scanned API
                - vulnerabilities_found: Count of issues
                - severity_breakdown: Issues by severity
                - vulnerabilities: Detailed findings
                - remediation_plan: Fix recommendations
                
        Example:
            >>> result = await scan_api_security(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     api_id="660e8400-e29b-41d4-a716-446655440001"
            ... )
            >>> print(f"Scan found {result['vulnerabilities_found']} issues")
        """,
        agent_domains=["security"]
    )
    
    registry.create_tool_from_method(
        method=security.get_gateway_vulnerabilities,
        name="list_vulnerabilities",
        description="""List security vulnerabilities for a specific gateway with filtering.
        
        Returns vulnerabilities for APIs within a gateway. Supports filtering by
        API, status, and severity.
        
        IMPORTANT: When user asks for "critical vulnerabilities" or "severe issues",
        set severity="critical". For "open vulnerabilities" or "unresolved issues", set status="open".
        For "resolved" or "fixed" vulnerabilities, set status="remediated".
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: Optional API filter within gateway
            status: Status filter. Valid values:
                - "open": Unresolved vulnerabilities
                - "remediated": Fixed vulnerabilities
                - "in_progress": Being fixed
                - "verified": Remediation verified
                - None (default): All statuses
            severity: Severity filter. Valid values:
                - "critical": Critical severity
                - "high": High severity
                - "medium": Medium severity
                - "low": Low severity
                - None (default): All severities
            limit: Maximum results (1-1000, default: 100)
            
        Returns:
            list: Vulnerability objects for the gateway
            
        Example for open high-severity vulnerabilities:
            >>> vulns = await list_vulnerabilities(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     status="open",
            ...     severity="high"
            ... )
            >>> print(f"Gateway has {len(vulns)} open high-severity vulnerabilities")
            
        Example for all gateway vulnerabilities:
            >>> vulns = await list_vulnerabilities(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> print(f"Gateway has {len(vulns)} total vulnerabilities")
        """,
        agent_domains=["security"]
    )
    
    registry.create_tool_from_method(
        method=security.get_gateway_vulnerability,
        name="get_vulnerability",
        description="""Get detailed information about a specific security vulnerability.
        
        Retrieves complete vulnerability details including description, affected API,
        severity, status, evidence, and remediation recommendations.
        
        Args:
            gateway_id: Gateway UUID (required)
            vulnerability_id: Vulnerability UUID (required)
            
        Returns:
            dict: Vulnerability details with:
                - id: Vulnerability UUID
                - api_id: Affected API
                - vulnerability_type: Type
                - severity: Severity level
                - status: Current status
                - description: Detailed description
                - evidence: Supporting evidence
                - remediation_steps: Fix recommendations
                - created_at: Discovery timestamp
                
        Example:
            >>> vuln = await get_vulnerability(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     vulnerability_id="880e8400-e29b-41d4-a716-446655440003"
            ... )
            >>> print(f"Vulnerability: {vuln['vulnerability_type']} ({vuln['severity']})")
        """,
        agent_domains=["security"]
    )
    
    registry.create_tool_from_method(
        method=security.remediate_gateway_vulnerability,
        name="remediate_vulnerability",
        description="""Trigger automated remediation for a security vulnerability.
        
        Applies automated fix for the vulnerability by configuring appropriate security
        policies on the gateway. Supports multiple remediation strategies.
        
        Args:
            gateway_id: Gateway UUID (required)
            vulnerability_id: Vulnerability UUID (required)
            remediation_strategy: Optional specific strategy to use
            
        Returns:
            dict: Remediation result with:
                - vulnerability_id: Remediated vulnerability
                - status: Remediation status
                - remediation_result: Applied changes
                - verification_result: Verification outcome
                
        Example:
            >>> result = await remediate_vulnerability(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     vulnerability_id="880e8400-e29b-41d4-a716-446655440003"
            ... )
            >>> print(f"Remediation: {result['status']}")
        """,
        agent_domains=["security"]
    )
    
    registry.create_tool_from_method(
        method=security.verify_gateway_remediation,
        name="verify_remediation",
        description="""Verify that vulnerability remediation was effective.
        
        Re-scans the API to confirm the vulnerability has been properly fixed and
        no longer exists. Updates vulnerability status based on verification results.
        
        Args:
            gateway_id: Gateway UUID (required)
            vulnerability_id: Vulnerability UUID (required)
            
        Returns:
            dict: Verification result with:
                - verified: Boolean success status
                - vulnerability_id: Verified vulnerability
                - message: Verification message
                
        Example:
            >>> result = await verify_remediation(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     vulnerability_id="880e8400-e29b-41d4-a716-446655440003"
            ... )
            >>> print(f"Verification: {result['verified']}")
        """,
        agent_domains=["security"]
    )
    
    registry.create_tool_from_method(
        method=security.get_gateway_security_summary,
        name="get_gateway_security_summary",
        description="""Get security summary for a specific gateway.
        
        Returns vulnerability counts by severity for all APIs within the gateway.
        
        Args:
            gateway_id: Gateway UUID (required)
            
        Returns:
            dict: Gateway security summary with vulnerability counts
            
        Example:
            >>> summary = await get_gateway_security_summary(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> print(f"Gateway security: {summary['total_vulnerabilities']} total")
        """,
        agent_domains=["security"]
    )
    
    registry.create_tool_from_method(
        method=security.get_gateway_security_posture,
        name="get_gateway_security_posture",
        description="""Get security posture for a specific gateway.
        
        Calculates security posture metrics including vulnerability distribution,
        remediation rates, and risk scoring for the gateway.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: Optional API filter within gateway
            
        Returns:
            dict: Gateway security posture metrics
            
        Example:
            >>> posture = await get_gateway_security_posture(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> print(f"Gateway risk: {posture['risk_score']}/100")
        """,
        agent_domains=["security"]
    )
    registry.create_tool_from_method(
        method=security.search_vulnerabilities,
        name="search_vulnerabilities",
        description="""Search security vulnerabilities across all gateways with flexible multi-criteria filtering.
        
        Use this tool when you need to find vulnerabilities matching multiple criteria simultaneously,
        such as severity + date range combinations or API name patterns with specific vulnerability types.
        Prefer this over list_all_vulnerabilities for complex queries.
        
        IMPORTANT: When to use search_vulnerabilities vs list_all_vulnerabilities:
        - Use search_vulnerabilities for: severity + date combinations, API name patterns, type filters
        - Use list_all_vulnerabilities for: simple severity or status-only filters
        
        IMPORTANT: Parameter interpretation for natural language queries:
        - "critical vulnerabilities" → severity="critical"
        - "open vulnerabilities" → status="open"
        - "this month" → discovered_after=(first day of current month)
        - "last week" → discovered_after=(7 days ago), discovered_before=(now)
        
        Args:
            severity: Filter by severity (critical, high, medium, low)
            type: Filter by vulnerability type (e.g., "sql_injection", "xss", "broken_auth")
            status: Filter by status (open, in_progress, resolved, false_positive)
            api_name: API name pattern (case-insensitive wildcard, e.g., "*payment*")
            gateway_id: Filter by specific gateway
            discovered_after: Filter vulnerabilities discovered after this date (ISO 8601)
            discovered_before: Filter vulnerabilities discovered before this date (ISO 8601)
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-100, default: 20)
            
        Returns:
            dict: Paginated vulnerability list with:
                - items: List of matching vulnerabilities
                - total: Total matching vulnerabilities
                - page: Current page number
                - page_size: Items per page
                
        Example:
            >>> # Find critical open vulnerabilities from this month
            >>> result = await search_vulnerabilities(
            ...     severity="critical",
            ...     status="open",
            ...     discovered_after="2024-01-01T00:00:00Z"
            ... )
            >>> print(f"Found {result['total']} critical open vulnerabilities")
            
            >>> # Find SQL injection vulnerabilities in payment APIs
            >>> result = await search_vulnerabilities(
            ...     type="sql_injection",
            ...     api_name="*payment*"
            ... )
        """,
        agent_domains=["security"]
    )
    
    
    # ============================================================================
    # Compliance Tools (5 tools)
    # ============================================================================
    
    registry.create_tool_from_method(
        method=compliance.scan_gateway_api_compliance,
        name="scan_api_compliance",
        description="""Scan API for compliance violations across 5 regulatory standards.
        
        Performs AI-driven compliance analysis checking adherence to GDPR, HIPAA, SOC2,
        PCI-DSS, and ISO 27001. Identifies violations, collects audit evidence, and
        provides remediation guidance.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: API UUID (required)
            standards: Optional list of specific standards to check (default: all 5)
            
        Returns:
            dict: Scan results with:
                - scan_id: Scan identifier
                - violations_found: Count of violations
                - severity_breakdown: Violations by severity
                - standard_breakdown: Violations by standard
                - violations: Detailed findings
                - audit_evidence: Collected evidence
                
        Example:
            >>> result = await scan_api_compliance(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     api_id="660e8400-e29b-41d4-a716-446655440001",
            ...     standards=["GDPR", "HIPAA"]
            ... )
            >>> print(f"Found {result['violations_found']} compliance violations")
        """,
        agent_domains=["compliance"]
    )
    
    registry.create_tool_from_method(
        method=compliance.get_gateway_violations,
        name="list_compliance_violations",
        description="""List compliance violations for a gateway with filtering.
        
        Returns compliance violations for APIs within a gateway. Supports filtering
        by API, standard, severity, and status.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: Optional API filter within gateway
            standard: Standard filter (GDPR, HIPAA, SOC2, PCI_DSS, ISO_27001)
            severity: Severity filter (critical, high, medium, low)
            status: Status filter (open, in_progress, remediated)
            limit: Maximum results (1-1000, default: 100)
            
        Returns:
            list: Compliance violation objects
            
        Example:
            >>> violations = await list_compliance_violations(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     standard="GDPR",
            ...     status="open"
            ... )
            >>> print(f"Found {len(violations)} open GDPR violations")
        """,
        agent_domains=["compliance"]
    )
    
    registry.create_tool_from_method(
        method=compliance.get_gateway_compliance_posture,
        name="get_compliance_posture",
        description="""Get compliance posture metrics and scores for a gateway.
        
        Calculates compliance posture including violation distribution, remediation
        rates, compliance scores, and next audit date recommendations.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: Optional API filter within gateway
            standard: Optional standard filter
            
        Returns:
            dict: Compliance posture with:
                - total_violations: Total count
                - by_severity: Breakdown by severity
                - by_status: Breakdown by status
                - by_standard: Breakdown by standard
                - remediation_rate: Percentage remediated
                - compliance_score: Overall score (0-100)
                - next_audit_date: Recommended audit date
                
        Example:
            >>> posture = await get_compliance_posture(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> print(f"Compliance Score: {posture['compliance_score']}/100")
        """,
        agent_domains=["compliance"]
    )
    
    registry.create_tool_from_method(
        method=compliance.generate_gateway_audit_report,
        name="generate_audit_report",
        description="""Generate comprehensive audit report with evidence and recommendations.
        
        Creates detailed audit report including AI-generated executive summary,
        compliance posture analysis, violation breakdowns, remediation status,
        audit evidence, and actionable recommendations.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_ids: Optional API filters (multiple)
            standards: Optional standard filters (multiple)
            start_date: Report start date (ISO 8601, default: 90 days ago)
            end_date: Report end date (ISO 8601, default: now)
            
        Returns:
            dict: Comprehensive audit report with:
                - report_id: Report identifier
                - executive_summary: AI-generated summary
                - compliance_posture: Overall posture
                - violations_by_standard: Standard breakdown
                - violations_by_severity: Severity breakdown
                - remediation_status: Remediation tracking
                - violations_needing_audit: Priority items
                - audit_evidence: Collected evidence
                - recommendations: Actionable recommendations
                
        Example:
            >>> report = await generate_audit_report(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     standards=["GDPR", "HIPAA"]
            ... )
            >>> print(f"Report: {report['executive_summary']}")
        """,
        agent_domains=["compliance"]
    )
    
    registry.create_tool_from_method(
        method=compliance.get_gateway_violation,
        name="get_compliance_violation",
        description="""Get detailed information about a specific compliance violation.
        
        Retrieves complete violation details including description, affected API,
        standard, severity, status, evidence, and remediation guidance.
        
        Args:
            gateway_id: Gateway UUID (required)
            violation_id: Violation UUID (required)
            
        Returns:
            dict: Violation details with:
                - id: Violation UUID
                - api_id: Affected API
                - standard: Compliance standard
                - severity: Severity level
                - status: Current status
                - description: Detailed description
                - evidence: Supporting evidence
                - remediation_guidance: Fix recommendations
                
        Example:
            >>> violation = await get_compliance_violation(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     violation_id="990e8400-e29b-41d4-a716-446655440004"
            ... )
            >>> print(f"Violation: {violation['standard']} - {violation['description']}")
        """,
        agent_domains=["compliance"]
    )
    registry.create_tool_from_method(
        method=compliance.search_compliance_violations,
        name="search_compliance_violations",
        description="""Search compliance violations across all gateways with flexible multi-criteria filtering.
        
        Use this tool when you need to find compliance violations matching multiple criteria simultaneously,
        such as standard + severity combinations or API name patterns with specific violation types.
        Prefer this over list_compliance_violations for complex queries.
        
        IMPORTANT: When to use search_compliance_violations vs list_compliance_violations:
        - Use search_compliance_violations for: standard + severity combinations, violation type filters, date ranges
        - Use list_compliance_violations for: simple standard or severity-only filters
        
        IMPORTANT: Parameter interpretation for natural language queries:
        - "GDPR violations" → standard="GDPR"
        - "high severity violations" → severity="high"
        - "open violations" → status="open"
        - "last quarter" → discovered_after=(90 days ago), discovered_before=(now)
        
        Args:
            standard: Filter by compliance standard (GDPR, HIPAA, PCI_DSS, SOC2, ISO27001)
            violation_type: Filter by violation type (e.g., "missing_encryption", "inadequate_logging")
            severity: Filter by severity (critical, high, medium, low)
            status: Filter by status (open, in_progress, resolved, accepted)
            api_name: API name pattern (case-insensitive wildcard, e.g., "*user*")
            gateway_id: Filter by specific gateway
            discovered_after: Filter violations discovered after this date (ISO 8601)
            discovered_before: Filter violations discovered before this date (ISO 8601)
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-100, default: 20)
            
        Returns:
            dict: Paginated violation list with:
                - items: List of matching violations
                - total: Total matching violations
                - page: Current page number
                - page_size: Items per page
                
        Example:
            >>> # Find GDPR violations with high severity from last quarter
            >>> result = await search_compliance_violations(
            ...     standard="GDPR",
            ...     severity="high",
            ...     discovered_after="2024-01-01T00:00:00Z"
            ... )
            >>> print(f"Found {result['total']} high-severity GDPR violations")
            
            >>> # Find missing encryption violations in user APIs
            >>> result = await search_compliance_violations(
            ...     violation_type="missing_encryption",
            ...     api_name="*user*"
            ... )
        """,
        agent_domains=["compliance"]
    )
    
    
    # ============================================================================
    # Optimization Tools (12 tools)
    # ============================================================================
    
    registry.create_tool_from_method(
        method=optimization.generate_gateway_recommendations,
        name="generate_recommendations",
        description="""Generate AI-driven optimization recommendations for an API.
        
        Analyzes API performance metrics and generates intelligent recommendations
        for caching, compression, rate limiting, and other optimizations. Uses hybrid
        approach combining rule-based analysis with AI-enhanced prioritization.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: API UUID (required)
            min_impact: Minimum expected improvement % (0-100, default: 10.0)
            
        Returns:
            dict: Generation results with:
                - status: Generation status
                - message: Status message
                - result: Generated recommendations
                
        Example:
            >>> result = await generate_recommendations(
            ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
            ...     api_id="660e8400-e29b-41d4-a716-446655440001",
            ...     min_impact=15.0
            ... )
            >>> print(f"Generated {len(result['result']['recommendations'])} recommendations")
        """,
        agent_domains=["optimization"]
    )
    
    registry.create_tool_from_method(
        method=optimization.list_all_recommendations,
        name="list_all_optimization_recommendations",
        description="""List all optimization recommendations across all gateways.
        
        Returns recommendations from all gateways with optional filtering by gateway,
        API, priority, status, and type. Supports pagination.
        
        Args:
            gateway_id: Optional gateway filter
            api_id: Optional API filter
            priority: Priority filter (high, medium, low)
            status: Status filter (pending, implemented, rejected)
            recommendation_type: Type filter (caching, compression, rate_limiting)
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-100, default: 20)
            
        Returns:
            dict: Paginated recommendation list
            
        Example:
            >>> result = await list_all_optimization_recommendations(
            ...     priority="high",
            ...     status="pending"
            ... )
            >>> print(f"Found {result['total']} high-priority pending recommendations")
        """,
        agent_domains=["optimization"]
    )
    
    registry.create_tool_from_method(
        method=optimization.list_gateway_recommendations,
        name="list_optimization_recommendations",
        description="""List optimization recommendations for a gateway.
        
        Returns recommendations for APIs within a gateway with optional filtering.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: Optional API filter within gateway
            priority: Priority filter (high, medium, low)
            status: Status filter (pending, implemented, rejected)
            recommendation_type: Type filter
            page: Page number (1-based, default: 1)

            page_size: Items per page (1-100, default: 20)
            
        Returns:
            dict: Paginated list with:
                - items: List of recommendation objects
                - total: Total count
                - page: Current page
                - page_size: Items per page
                
        Example:
            >>> result = await list_optimization_recommendations(
            ...     gateway_id="gw-123",
            ...     priority="high",
            ...     status="pending"
            ... )
            >>> print(f"Found {result['total']} recommendations")
        """,
        agent_domains=["optimization", "metrics"]
    )
    
    # 7. Get Optimization Recommendation
    registry.create_tool_from_method(
        method=optimization.get_gateway_recommendation,
        name="get_optimization_recommendation",
        description="""Get detailed information about a specific optimization recommendation.
        
        Retrieves complete recommendation details including impact analysis, implementation
        steps, and validation results.
        
        Args:
            gateway_id: Gateway UUID (required)
            recommendation_id: Recommendation UUID (required)
            
        Returns:
            dict: Recommendation object with:
                - id: Recommendation UUID
                - api_id: Target API UUID
                - recommendation_type: Type of optimization
                - priority: Priority level (high, medium, low)
                - status: Current status
                - expected_improvement: Expected performance gain
                - implementation_steps: List of steps
                - validation_results: Post-implementation metrics
                
        Example:
            >>> rec = await get_optimization_recommendation(
            ...     gateway_id="gw-123",
            ...     recommendation_id="rec-456"
            ... )
            >>> print(f"Expected improvement: {rec['expected_improvement']}%")
        """,
        agent_domains=["optimization"]
    )
    
    # 8. Generate Optimization Recommendations
    registry.create_tool_from_method(
        method=optimization.generate_gateway_recommendations,
        name="generate_optimization_recommendations",
        description="""Generate AI-driven optimization recommendations for an API.
        
        Analyzes API metrics, policies, and patterns to generate actionable optimization
        recommendations using AI/ML models.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: API UUID to analyze (required)
            min_impact: Minimum expected improvement % (0-100, default: 10.0)
            
        Returns:
            dict: Generation result with:
                - recommendations_generated: Number of new recommendations
                - recommendations: List of recommendation objects
                - analysis_summary: AI analysis summary
                
        Example:
            >>> result = await generate_optimization_recommendations(
            ...     gateway_id="gw-123",
            ...     api_id="api-456",
            ...     min_impact=15.0
            ... )
            >>> print(f"Generated {result['recommendations_generated']} recommendations")
        """,
        agent_domains=["optimization"]
    )
    
    # 9. Apply Optimization Recommendation
    registry.create_tool_from_method(
        method=optimization.apply_gateway_recommendation,
        name="apply_optimization_recommendation",
        description="""Apply an optimization recommendation to the gateway.
        
        Implements the recommended optimization by configuring gateway policies
        and settings. Tracks implementation status and results.
        
        Args:
            gateway_id: Gateway UUID (required)
            recommendation_id: Recommendation UUID to apply (required)
            
        Returns:
            dict: Application result with:
                - success: Whether application succeeded
                - policy_id: ID of created/updated policy
                - message: Status message
                - rollback_available: Whether rollback is possible
                
        Example:
            >>> result = await apply_optimization_recommendation(
            ...     gateway_id="gw-123",
            ...     recommendation_id="rec-456"
            ... )
            >>> if result['success']:
            ...     print(f"Applied policy: {result['policy_id']}")
        """,
        agent_domains=["optimization"]
    )
    
    # 10. Remove Optimization Policy
    registry.create_tool_from_method(
        method=optimization.remove_gateway_recommendation_policy,
        name="remove_optimization_policy",
        description="""Remove an applied optimization policy from the gateway.
        
        Rolls back a previously applied optimization recommendation by removing
        the associated gateway policy.
        
        Args:
            gateway_id: Gateway UUID (required)
            recommendation_id: Recommendation UUID (required)
            
        Returns:
            dict: Removal result with:
                - success: Whether removal succeeded
                - message: Status message
                
        Example:
            >>> result = await remove_optimization_policy(
            ...     gateway_id="gw-123",
            ...     recommendation_id="rec-456"
            ... )
            >>> print(f"Rollback: {result['message']}")
        """,
        agent_domains=["optimization"]
    )
    
    # 11. Validate Optimization Recommendation
    registry.create_tool_from_method(
        method=optimization.validate_gateway_recommendation,
        name="validate_optimization_recommendation",
        description="""Validate the impact of an implemented optimization recommendation.
        
        Analyzes metrics after implementation to verify expected improvements
        were achieved.
        
        Args:
            gateway_id: Gateway UUID (required)
            recommendation_id: Recommendation UUID (required)
            validation_window_hours: Hours of metrics to analyze (default: 24)
            
        Returns:
            dict: Validation result with:
                - validated: Whether validation succeeded
                - actual_improvement: Measured improvement percentage
                - expected_improvement: Original expected improvement
                - metrics_comparison: Before/after metrics
                - recommendation: Continue, rollback, or adjust
                
        Example:
            >>> result = await validate_optimization_recommendation(
            ...     gateway_id="gw-123",
            ...     recommendation_id="rec-456",
            ...     validation_window_hours=48
            ... )
            >>> print(f"Actual improvement: {result['actual_improvement']}%")
        """,
        agent_domains=["optimization", "metrics"]
    )
    
    # 12. Get Optimization Summary
    registry.create_tool_from_method(
        method=optimization.get_gateway_optimization_summary,
        name="get_optimization_summary",
        description="""Get optimization summary for a gateway.
        
        Provides aggregate statistics on optimization recommendations and their
        impact across all APIs in the gateway.
        
        Args:
            gateway_id: Gateway UUID (required)
            
        Returns:
            dict: Summary with:
                - total_recommendations: Total count
                - by_priority: Breakdown by priority level
                - by_status: Breakdown by status
                - total_expected_improvement: Sum of expected gains
                - total_actual_improvement: Sum of measured gains
                - implementation_rate: % of recommendations implemented
                
        Example:
            >>> summary = await get_optimization_summary(gateway_id="gw-123")
            >>> print(f"Implementation rate: {summary['implementation_rate']}%")
        """,
        agent_domains=["optimization", "metrics"]
    )
    
    # 13. Get Recommendation Stats
    registry.create_tool_from_method(
        method=optimization.get_gateway_recommendation_stats,
        name="get_recommendation_stats",
        description="""Get statistics about optimization recommendations for a gateway.
        
        Provides aggregate statistics on recommendation generation, implementation,
        and effectiveness over a specified time period.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: Optional API filter within gateway
            days: Number of days to analyze (1-365, default: 30)
            
        Returns:
            dict: Statistics with:
                - total_recommendations: Total count
                - by_priority: Breakdown by priority
                - by_status: Breakdown by status
                - implementation_rate: % implemented
                - average_impact: Mean improvement percentage
                - top_recommendation_types: Most common types
                
        Example:
            >>> stats = await get_recommendation_stats(
            ...     gateway_id="gw-123",
            ...     days=60
            ... )
            >>> print(f"Implementation rate: {stats['implementation_rate']:.1%}")
        """,
        agent_domains=["optimization", "metrics"]
    )
    
    # 14. Get Recommendation Insights
    registry.create_tool_from_method(
        method=optimization.get_gateway_recommendation_insights,
        name="get_recommendation_insights",
        description="""Get AI-generated insights for an optimization recommendation.
        
        Provides detailed AI analysis explaining the recommendation's rationale,
        expected impact, and implementation considerations.
        
        Args:
            gateway_id: Gateway UUID (required)
            recommendation_id: Recommendation UUID (required)
            
        Returns:
            dict: Insights with:
                - recommendation_id: Recommendation UUID
                - insights: AI-generated analysis
                - impact_factors: Key factors affecting impact
                - implementation_considerations: Important notes
                - risk_assessment: Potential risks
                
        Example:
            >>> insights = await get_recommendation_insights(
            ...     gateway_id="gw-123",
            ...     recommendation_id="rec-456"
            ... )
            >>> print(f"Insights: {insights['insights']}")
        """,
        agent_domains=["optimization"]
    )
    
    # 15. Get Recommendation Actions
    registry.create_tool_from_method(
        method=optimization.get_recommendation_actions,
        name="get_recommendation_actions",
        description="""Get action history for an optimization recommendation.
        
        Returns the complete history of actions taken on a recommendation including
        generation, application, validation, and any rollbacks.
        
        Args:
            gateway_id: Gateway UUID (required)
            recommendation_id: Recommendation UUID (required)
            
        Returns:
            dict: Action history with:
                - recommendation_id: Recommendation UUID
                - actions: List of action objects with:
                    - action_type: Type of action
                    - timestamp: When action occurred
                    - user: Who performed action
                    - result: Action outcome
                    - details: Additional information
                
        Example:
            >>> history = await get_recommendation_actions(
            ...     gateway_id="gw-123",
            ...     recommendation_id="rec-456"
            ... )
            >>> print(f"Total actions: {len(history['actions'])}")
        """,
        agent_domains=["optimization"]
    )
    registry.create_tool_from_method(
        method=optimization.search_recommendations,
        name="search_recommendations",
        description="""Search optimization recommendations across all gateways with flexible multi-criteria filtering.
        
        Use this tool when you need to find recommendations matching multiple criteria simultaneously,
        such as type + priority combinations or impact ranges with specific statuses.
        Prefer this over list_recommendations for complex queries.
        
        IMPORTANT: When to use search_recommendations vs list_recommendations:
        - Use search_recommendations for: type + priority combinations, impact ranges, date filters
        - Use list_recommendations for: simple status or priority-only filters
        
        IMPORTANT: Parameter interpretation for natural language queries:
        - "caching recommendations" → type="caching"
        - "high priority recommendations" → priority="high"
        - "pending recommendations" → status="pending"
        - "high impact recommendations" → impact_min=20 (or higher threshold)
        
        Args:
            type: Filter by recommendation type (caching, rate_limiting, connection_pooling, compression, etc.)
            priority: Filter by priority (high, medium, low)
            status: Filter by status (pending, in_progress, implemented, rejected)
            impact_min: Minimum expected impact percentage (0-100)
            impact_max: Maximum expected impact percentage (0-100)
            api_name: API name pattern (case-insensitive wildcard, e.g., "*checkout*")
            gateway_id: Filter by specific gateway
            created_after: Filter recommendations created after this date (ISO 8601)
            created_before: Filter recommendations created before this date (ISO 8601)
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-100, default: 20)
            
        Returns:
            dict: Paginated recommendation list with:
                - recommendations: List of matching recommendations
                - total: Total matching recommendations
                - page: Current page number
                - page_size: Items per page
                
        Example:
            >>> # Find high-priority caching recommendations with >20% impact
            >>> result = await search_recommendations(
            ...     type="caching",
            ...     priority="high",
            ...     impact_min=20
            ... )
            >>> print(f"Found {result['total']} high-impact caching recommendations")
            
            >>> # Find pending recommendations for checkout APIs
            >>> result = await search_recommendations(
            ...     status="pending",
            ...     api_name="*checkout*"
            ... )
        """,
        agent_domains=["optimization"]
    )
    
    
    logger.info("Registered 15 optimization tools")
    
    # ============================================================================
    # PREDICTIONS (5 tools)
    # ============================================================================
    
    # 1. List Predictions
    registry.create_tool_from_method(
        method=predictions.list_gateway_predictions,
        name="list_predictions",
        description="""List failure predictions for a gateway.
        
        Returns AI-generated predictions of potential API failures based on
        pattern analysis and anomaly detection.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: Optional API filter
            severity: Severity filter (critical, high, medium, low)
            status: Status filter (active, resolved, false_positive, expired)
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-100, default: 20)
            
        Returns:
            dict: Paginated list with:
                - items: List of prediction objects
                - total: Total count
                - page: Current page
                - page_size: Items per page
                
        Example:
            >>> result = await list_predictions(
            ...     gateway_id="gw-123",
            ...     severity="critical",
            ...     status="active"
            ... )
            >>> print(f"Found {result['total']} critical predictions")
        """,
        agent_domains=["prediction", "metrics"]
    )
    
    # 2. Get Prediction
    registry.create_tool_from_method(
        method=predictions.get_gateway_prediction,
        name="get_prediction",
        description="""Get detailed information about a specific failure prediction.
        
        Retrieves complete prediction details including AI analysis, confidence
        score, and recommended actions.
        
        Args:
            gateway_id: Gateway UUID (required)
            prediction_id: Prediction UUID (required)
            
        Returns:
            dict: Prediction object with:
                - id: Prediction UUID
                - api_id: Affected API UUID
                - prediction_type: Type of predicted failure
                - severity: Severity level
                - confidence_score: AI confidence (0.0-1.0)
                - predicted_time: When failure is expected
                - indicators: List of warning indicators
                - recommended_actions: List of preventive actions
                
        Example:
            >>> pred = await get_prediction(
            ...     gateway_id="gw-123",
            ...     prediction_id="pred-456"
            ... )
            >>> print(f"Confidence: {pred['confidence_score']:.2%}")
        """,
        agent_domains=["prediction"]
    )
    
    # 3. Get Prediction Explanation
    registry.create_tool_from_method(
        method=predictions.get_gateway_prediction_explanation,
        name="get_prediction_explanation",
        description="""Get AI-generated explanation for a failure prediction.
        
        Provides detailed natural language explanation of why the prediction
        was made and what factors contributed to it.
        
        Args:
            gateway_id: Gateway UUID (required)
            prediction_id: Prediction UUID (required)
            
        Returns:
            dict: Explanation with:
                - explanation: Natural language explanation
                - contributing_factors: List of key factors
                - historical_patterns: Similar past incidents
                - confidence_breakdown: Confidence score components
                
        Example:
            >>> exp = await get_prediction_explanation(
            ...     gateway_id="gw-123",
            ...     prediction_id="pred-456"
            ... )
            >>> print(f"Explanation: {exp['explanation']}")
        """,
        agent_domains=["prediction"]
    )
    
    # 4. Get Prediction Accuracy Stats
    registry.create_tool_from_method(
        method=predictions.get_gateway_prediction_accuracy_stats,
        name="get_prediction_accuracy_stats",
        description="""Get prediction accuracy statistics for a gateway.
        
        Analyzes historical prediction accuracy to assess model performance
        and reliability.
        
        Args:
            gateway_id: Gateway UUID (required)
            api_id: Optional API filter
            days: Number of days to analyze (1-90, default: 30)
            
        Returns:
            dict: Statistics with:
                - total_predictions: Total count
                - true_positives: Correct predictions
                - false_positives: Incorrect predictions
                - accuracy_rate: Overall accuracy percentage
                - precision: Precision score
                - recall: Recall score
                - by_severity: Accuracy breakdown by severity
                
        Example:
            >>> stats = await get_prediction_accuracy_stats(
            ...     gateway_id="gw-123",
            ...     days=60
            ... )
            >>> print(f"Accuracy: {stats['accuracy_rate']:.1%}")
        """,
        agent_domains=["prediction", "metrics"]
    )
    
    # 5. List All Predictions (Global)
    registry.create_tool_from_method(
        method=predictions.list_all_predictions,
        name="list_all_predictions",
        description="""Get global predictions summary across all gateways.
        
        Provides aggregate prediction statistics across the entire platform
        or filtered to a specific gateway.
        
        Args:
            gateway_id: Optional gateway filter
            
        Returns:
            dict: Summary with:
                - total_predictions: Total count
                - by_severity: Breakdown by severity
                - by_status: Breakdown by status
                - average_confidence: Mean confidence score
                - accuracy_rate: Overall accuracy
                - top_predicted_issues: Most common prediction types
                
        Example:
            >>> summary = await get_global_predictions_summary()
            >>> print(f"Platform accuracy: {summary['accuracy_rate']:.1%}")
        """,
        agent_domains=["prediction", "metrics"]
    )
    registry.create_tool_from_method(
        method=predictions.search_predictions,
        name="search_predictions",
        description="""Search failure predictions across all gateways with flexible multi-criteria filtering.
        
        Use this tool when you need to find predictions matching multiple criteria simultaneously,
        such as confidence ranges combined with severity or prediction type filters.
        Prefer this over list_all_predictions for complex queries.
        
        IMPORTANT: When to use search_predictions vs list_all_predictions:
        - Use search_predictions for: confidence ranges, prediction type filters, date ranges
        - Use list_all_predictions for: simple severity or status-only filters
        
        IMPORTANT: Parameter interpretation for natural language queries:
        - "high confidence predictions" → confidence_min=0.8
        - "failure predictions" → prediction_type="failure"
        - "critical predictions" → severity="critical"
        - "next hour" → predicted_after=(now), predicted_before=(now + 1 hour)
        
        Args:
            prediction_type: Filter by prediction type (failure, degradation, capacity, security)
            confidence_min: Minimum confidence score (0.0-1.0)
            confidence_max: Maximum confidence score (0.0-1.0)
            severity: Filter by severity (critical, high, medium, low)
            status: Filter by status (pending, confirmed, false_positive, resolved)
            predicted_after: Filter predictions made after this date (ISO 8601)
            predicted_before: Filter predictions made before this date (ISO 8601)
            api_name: API name pattern (case-insensitive wildcard, e.g., "*api*")
            gateway_id: Filter by specific gateway
            page: Page number (1-based, default: 1)
            page_size: Items per page (1-100, default: 20)
            
        Returns:
            dict: Paginated prediction list with:
                - predictions: List of matching predictions
                - total: Total matching predictions
                - page: Current page number
                - page_size: Items per page
                
        Example:
            >>> # Find high-confidence failure predictions with critical severity
            >>> result = await search_predictions(
            ...     prediction_type="failure",
            ...     confidence_min=0.8,
            ...     severity="critical"
            ... )
            >>> print(f"Found {result['total']} high-confidence critical failures")
            
            >>> # Find predictions for production gateway from last week
            >>> result = await search_predictions(
            ...     gateway_id="gw-prod-123",
            ...     predicted_after="2024-01-01T00:00:00Z"
            ... )
        """,
        agent_domains=["prediction"]
    )
    
    
    logger.info("Registered 5 prediction tools")
    
    # ============================================================================
    # NATURAL LANGUAGE QUERIES (7 tools)
    # ============================================================================
    
    # NOTE: Query tools are NOT registered for agents since they're for the query service itself
    # Agents use domain-specific tools (discovery, metrics, security, etc.) to answer queries
    
    logger.info("Skipped 7 query service tools (not for agent use)")
    
    
    # ============================================================================
    # FINALIZATION
    # ============================================================================
    
    total_tools = len(registry.get_all_tools())
    logger.info(f"Tool registration complete: {total_tools} tools registered")
    
    return registry
