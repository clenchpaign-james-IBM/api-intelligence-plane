"""Unified MCP Server for API Intelligence Plane.

This MCP server provides a comprehensive interface exposing ALL backend REST API
endpoints as MCP tools. It acts as a single unified interface for external agentic
workflows to interact with the entire API Intelligence Plane system.

This server consolidates functionality from:
- Gateway Management (create, list, update, delete, connect, disconnect, sync)
- API Discovery & Inventory (list, search, get details)
- Metrics Collection & Analysis (get metrics, timeseries, drill-down)
- Security Scanning & Remediation (scan, list vulnerabilities, remediate)
- Compliance Monitoring (scan, audit reports, posture)
- Performance Optimization (generate recommendations, apply)
- Rate Limiting (create policies, analyze effectiveness)
- Failure Predictions (list, get details, explanations)

Port: 8007 (external) -> 8000 (internal)
Transport: Streamable HTTP
Architecture: Thin wrapper delegating to backend REST API at http://backend:8000/api/v1
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.backend_client import BackendClient
from common.health import HealthChecker
from common.mcp_base import BaseMCPServer

logger = logging.getLogger(__name__)


class UnifiedMCPServer(BaseMCPServer):
    """Unified MCP Server exposing all API Intelligence Plane functionality.
    
    This server provides a comprehensive set of tools covering all backend endpoints.
    All tools delegate to the backend REST API following the thin wrapper pattern.
    """

    def __init__(self):
        """Initialize Unified MCP server."""
        super().__init__(name="unified-server", version="1.0.0")
        self.backend_client = BackendClient()
        self.health_checker = HealthChecker(self.name, self.version)
        self._register_tools()
        logger.info("Unified MCP server initialized (comprehensive backend API wrapper)")

    def _register_tools(self) -> None:
        """Register all MCP tools for this server."""
        
        # ============================================================================
        # HEALTH & SERVER INFO (2 tools)
        # ============================================================================
        
        @self.tool(description="Check Unified server health and backend connectivity status")
        async def health() -> Dict[str, Any]:
            """Check server health including backend connectivity.
            
            Verifies that the unified MCP server is operational and can communicate
            with the backend REST API. Essential for monitoring and diagnostics.
            
            Returns:
                dict: Health status including:
                    - status: "healthy" or "degraded"
                    - server: Server name
                    - version: Server version
                    - backend_status: "connected" or "disconnected"
                    - timestamp: Current timestamp (ISO 8601)
            
            Example:
                >>> health_status = await health()
                >>> print(f"Server status: {health_status['status']}")
                >>> print(f"Backend: {health_status['backend_status']}")
            """
            try:
                response = await self.backend_client.client.get("/gateways", params={"page": 1, "page_size": 1})
                response.raise_for_status()
                backend_status = "connected"
            except Exception as e:
                logger.error(f"Backend health check failed: {e}")
                backend_status = "disconnected"
            return {
                "status": "healthy" if backend_status == "connected" else "degraded",
                "server": self.name,
                "version": self.version,
                "backend_status": backend_status,
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        @self.tool(description="Get comprehensive server information and capabilities")
        def server_info() -> Dict[str, Any]:
            """Get comprehensive server information and capabilities.
            
            Provides metadata about the unified MCP server including supported
            capabilities, port configuration, and backend connection details.
            
            Returns:
                dict: Server information including:
                    - name: Server name
                    - version: Server version
                    - port: External port (8007)
                    - transport: Transport protocol
                    - backend_url: Backend API URL
                    - capabilities: List of supported capability categories
            
            Example:
                >>> info = server_info()
                >>> print(f"Capabilities: {', '.join(info['capabilities'])}")
            """
            info = self.get_server_info()
            info.update({
                "port": 8007,
                "internal_port": 8000,
                "transport": "streamable-http",
                "backend_url": self.backend_client.base_url,
                "capabilities": [
                    "gateway_management",
                    "api_discovery",
                    "metrics_analytics",
                    "security_scanning",
                    "compliance_monitoring",
                    "performance_optimization",
                    "rate_limiting",
                    "failure_predictions",
                ],
            })
            return info
        
        # ============================================================================
        # GATEWAY MANAGEMENT (10 tools)
        # ============================================================================
        
        @self.tool(description="Create and register a new API Gateway in the system")
        async def create_gateway(
            name: str,
            vendor: str,
            base_url: str,
            version: Optional[str] = None,
            base_url_credential_type: str = "none",
            base_url_api_key: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create and register a new API Gateway.
            
            Registers a new API Gateway in the system with the specified configuration.
            The gateway starts in DISCONNECTED status and must be explicitly connected
            using connect_gateway before API discovery can begin.
            
            Args:
                name: Human-readable gateway name
                vendor: Gateway vendor (native, kong, apigee, aws, azure, mulesoft, webmethods)
                base_url: Gateway base URL for API management endpoints
                version: Optional gateway version string
                base_url_credential_type: Authentication type (none, api_key, basic, bearer)
                base_url_api_key: API key if credential_type is "api_key"
            
            Returns:
                dict: Created gateway object with:
                    - id: Gateway UUID
                    - name: Gateway name
                    - vendor: Gateway vendor
                    - status: Initial status (DISCONNECTED)
                    - base_url: Gateway URL
                    - created_at: Creation timestamp
            
            Example:
                >>> gateway = await create_gateway(
                ...     name="Production Kong Gateway",
                ...     vendor="kong",
                ...     base_url="https://api.example.com:8001",
                ...     base_url_credential_type="api_key",
                ...     base_url_api_key="your-api-key-here"
                ... )
                >>> print(f"Created gateway: {gateway['id']}")
            """
            payload = {
                "name": name,
                "vendor": vendor,
                "base_url": base_url,
                "connection_type": "rest_api",
                "base_url_credential_type": base_url_credential_type
            }
            if version:
                payload["version"] = version
            if base_url_api_key:
                payload["base_url_api_key"] = base_url_api_key
            return await self.backend_client._request("POST", "/gateways", json=payload)
        
        @self.tool(description="List all registered API Gateways with pagination and filtering")
        async def list_gateways(
            page: int = 1,
            page_size: int = 20,
            status: Optional[str] = None
        ) -> Dict[str, Any]:
            """List all registered API Gateways with pagination.
            
            Retrieves a paginated list of all gateways registered in the system.
            Supports filtering by connection status.
            
            Args:
                page: Page number (1-based, default: 1)
                page_size: Items per page (1-100, default: 20)
                status: Optional status filter (connected, disconnected, error)
            
            Returns:
                dict: Paginated gateway list with:
                    - items: List of gateway objects
                    - total: Total number of gateways
                    - page: Current page number
                    - page_size: Items per page
            
            Example:
                >>> gateways = await list_gateways(page=1, page_size=10, status="connected")
                >>> print(f"Found {gateways['total']} gateways")
                >>> for gw in gateways['items']:
                ...     print(f"  - {gw['name']} ({gw['vendor']})")
            """
            params: Dict[str, Any] = {"page": page, "page_size": page_size}
            if status:
                params["status"] = status
            return await self.backend_client._request("GET", "/gateways", params=params)
        
        @self.tool(description="Get detailed information about a specific API Gateway")
        async def get_gateway(gateway_id: str) -> Dict[str, Any]:
            """Get complete details of a specific Gateway.
            
            Retrieves comprehensive information about a gateway including configuration,
            connection status, API count, and metadata.
            
            Args:
                gateway_id: Gateway UUID
            
            Returns:
                dict: Complete gateway object with all fields
            
            Example:
                >>> gateway = await get_gateway("550e8400-e29b-41d4-a716-446655440000")
                >>> print(f"Gateway: {gateway['name']}")
                >>> print(f"Status: {gateway['status']}")
                >>> print(f"APIs: {gateway['api_count']}")
            """
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}")
        
        @self.tool(description="Update API Gateway configuration settings")
        async def update_gateway(
            gateway_id: str,
            name: Optional[str] = None,
            version: Optional[str] = None,
            base_url: Optional[str] = None,
            status: Optional[str] = None
        ) -> Dict[str, Any]:
            """Update gateway configuration.
            
            Updates one or more configuration fields for an existing gateway.
            Only provided fields will be updated; others remain unchanged.
            
            Args:
                gateway_id: Gateway UUID
                name: New gateway name (optional)
                version: New version string (optional)
                base_url: New base URL (optional)
                status: New status (optional, use connect/disconnect instead)
            
            Returns:
                dict: Updated gateway object
            
            Example:
                >>> updated = await update_gateway(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     name="Production Kong Gateway v2",
                ...     version="3.0.0"
                ... )
            """
            payload = {}
            if name:
                payload["name"] = name
            if version:
                payload["version"] = version
            if base_url:
                payload["base_url"] = base_url
            if status:
                payload["status"] = status
            return await self.backend_client._request("PUT", f"/gateways/{gateway_id}", json=payload)
        
        @self.tool(description="Establish connection to a Gateway and validate credentials")
        async def connect_gateway(gateway_id: str) -> Dict[str, Any]:
            """Connect to a gateway and validate credentials.
            
            Establishes connection to the gateway, validates credentials, and updates
            status to CONNECTED on success. Required before API discovery can begin.
            
            Args:
                gateway_id: Gateway UUID
            
            Returns:
                dict: Updated gateway object with CONNECTED status
            
            Raises:
                Error if gateway not found or connection fails
            
            Example:
                >>> result = await connect_gateway("550e8400-e29b-41d4-a716-446655440000")
                >>> print(f"Connected: {result['status'] == 'connected'}")
            """
            return await self.backend_client._request("POST", f"/gateways/{gateway_id}/connect")
        
        @self.tool(description="Disconnect from an API Gateway")
        async def disconnect_gateway(gateway_id: str) -> Dict[str, Any]:
            """Disconnect from a gateway.
            
            Disconnects from the gateway and updates status to DISCONNECTED.
            Gateway remains registered but inactive.
            
            Args:
                gateway_id: Gateway UUID
            
            Returns:
                dict: Updated gateway object with DISCONNECTED status
            
            Example:
                >>> result = await disconnect_gateway("550e8400-e29b-41d4-a716-446655440000")
            """
            return await self.backend_client._request("POST", f"/gateways/{gateway_id}/disconnect")
        
        @self.tool(description="Permanently delete an API Gateway from the system")
        async def delete_gateway(gateway_id: str) -> Dict[str, Any]:
            """Delete a gateway from the system.
            
            Permanently removes a gateway and all associated data from the system.
            This operation cannot be undone.
            
            Args:
                gateway_id: Gateway UUID
            
            Returns:
                dict: Deletion confirmation with success status
            
            Example:
                >>> result = await delete_gateway("550e8400-e29b-41d4-a716-446655440000")
                >>> print(f"Deleted: {result['success']}")
            """
            return await self.backend_client._request("DELETE", f"/gateways/{gateway_id}")
        
        @self.tool(description="Trigger API discovery and synchronization from a Gateway")
        async def sync_gateway(gateway_id: str, force_refresh: bool = False) -> Dict[str, Any]:
            """Trigger API discovery/sync from a gateway.
            
            Initiates API discovery process to fetch and synchronize APIs from the gateway.
            Discovers new APIs, updates existing ones, and detects shadow APIs.
            
            Args:
                gateway_id: Gateway UUID
                force_refresh: Force immediate sync even if recently synced (default: False)
            
            Returns:
                dict: Sync results with:
                    - apis_discovered: Total APIs found
                    - new_apis: Newly discovered APIs
                    - updated_apis: Updated existing APIs
                    - shadow_apis_found: Shadow APIs detected
                    - timestamp: Sync completion time
            
            Example:
                >>> result = await sync_gateway(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     force_refresh=True
                ... )
                >>> print(f"Discovered {result['apis_discovered']} APIs")
                >>> print(f"Shadow APIs: {result['shadow_apis_found']}")
            """
            params = {"force_refresh": force_refresh}
            return await self.backend_client._request("POST", f"/gateways/{gateway_id}/sync", params=params)
        
        @self.tool(description="Test Gateway connection without saving configuration")
        async def test_gateway_connection(
            name: str,
            vendor: str,
            base_url: str,
            base_url_credential_type: str = "none",
            base_url_api_key: Optional[str] = None
        ) -> Dict[str, Any]:
            """Test gateway connection without saving.
            
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
            """
            payload = {
                "name": name,
                "vendor": vendor,
                "base_url": base_url,
                "connection_type": "rest_api",
                "base_url_credential_type": base_url_credential_type
            }
            if base_url_api_key:
                payload["base_url_api_key"] = base_url_api_key
            return await self.backend_client._request("POST", "/gateways/test-connection", json=payload)
        
        @self.tool(description="Synchronize multiple API Gateways in parallel for efficiency")
        async def bulk_sync_gateways(
            gateway_ids: List[str],
            force_refresh: bool = False
        ) -> Dict[str, Any]:
            """Sync multiple gateways in parallel.
            
            Efficiently synchronizes multiple gateways concurrently. Each gateway
            is synced independently with aggregated results.
            
            Args:
                gateway_ids: List of gateway UUIDs (max 50)
                force_refresh: Force refresh for all gateways
            
            Returns:
                dict: Bulk sync results with:
                    - total: Total gateways synced
                    - successful: Number of successful syncs
                    - failed: Number of failed syncs
                    - total_apis_discovered: Total APIs across all gateways
                    - results: Per-gateway sync results
                    - duration_seconds: Total execution time
            
            Example:
                >>> result = await bulk_sync_gateways(
                ...     gateway_ids=[
                ...         "550e8400-e29b-41d4-a716-446655440000",
                ...         "660e8400-e29b-41d4-a716-446655440001"
                ...     ],
                ...     force_refresh=True
                ... )
                >>> print(f"Synced {result['successful']}/{result['total']} gateways")
            """
            payload = {"gatewayIds": gateway_ids}
            params = {"force_refresh": force_refresh}
            return await self.backend_client._request("POST", "/gateways/bulk-sync", json=payload, params=params)
        
        # ============================================================================
        # API DISCOVERY & INVENTORY (7 tools - includes 2 search tools)
        # ============================================================================
        
        @self.tool(description="List all APIs across all gateways with comprehensive filtering")
        async def list_all_apis(
            page: int = 1,
            page_size: int = 20,
            gateway_id: Optional[str] = None,
            status: Optional[str] = None,
            is_shadow: Optional[bool] = None,
            health_score_min: Optional[float] = None
        ) -> Dict[str, Any]:
            """List all APIs across all gateways.
            
            Aggregate endpoint returning APIs from all gateways with powerful filtering
            options including status, shadow detection, and health score.
            
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
                    - total: Total matching APIs
                    - page: Current page
                    - page_size: Items per page
            
            Example:
                >>> apis = await list_all_apis(
                ...     page=1,
                ...     page_size=50,
                ...     is_shadow=True,
                ...     health_score_min=0.7
                ... )
                >>> print(f"Found {apis['total']} shadow APIs with health >= 0.7")
            """
            params: Dict[str, Any] = {"page": page, "page_size": page_size}
            if gateway_id:
                params["gateway_id"] = gateway_id
            if status:
                params["status"] = status
            if is_shadow is not None:
                params["is_shadow"] = is_shadow
            if health_score_min is not None:
                params["health_score_min"] = health_score_min
            return await self.backend_client._request("GET", "/apis", params=params)
        
        @self.tool(description="List APIs for a specific Gateway with filtering options")
        async def list_apis(
            gateway_id: str,
            page: int = 1,
            page_size: int = 20,
            status: Optional[str] = None,
            is_shadow: Optional[bool] = None,
            health_score_min: Optional[float] = None
        ) -> Dict[str, Any]:
            """List APIs for a specific gateway.
            
            Retrieves paginated list of APIs belonging to a specific gateway with
            optional filtering by status, shadow detection, and health score.
            
            Args:
                gateway_id: Gateway UUID (required)
                page: Page number (1-based)
                page_size: Items per page (1-1000)
                status: Status filter (active, inactive, deprecated, failed)
                is_shadow: Shadow API filter
                health_score_min: Minimum health score (0.0-1.0)
            
            Returns:
                dict: Paginated API list for the gateway
            
            Example:
                >>> apis = await list_apis(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     status="active",
                ...     page_size=100
                ... )
            """
            return await self.backend_client.list_apis(
                gateway_id=gateway_id,
                page=page,
                page_size=page_size,
                status=status,
                is_shadow=is_shadow,
                health_score_min=health_score_min
            )
        
        @self.tool(description="Search APIs using OpenSearch full-text search with fuzzy matching")
        async def search_apis(
            gateway_id: str,
            query: str,
            limit: int = 100,
            status: Optional[str] = None,
            is_shadow: Optional[bool] = None
        ) -> Dict[str, Any]:
            """Search APIs using full-text search.
            
            Performs OpenSearch full-text search across API name, base_path, description,
            and tags with fuzzy matching for typo tolerance. Results are relevance-ranked.
            
            Args:
                gateway_id: Gateway UUID (required)
                query: Search query string
                limit: Maximum results (1-1000, default: 100)
                status: Optional status filter
                is_shadow: Optional shadow API filter
            
            Returns:
                dict: Search results with:
                    - results: List of matching APIs (relevance-ranked)
                    - total: Total matches
                    - query: Original query string
            
            Example:
                >>> results = await search_apis(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     query="payment api",
                ...     limit=20
                ... )
                >>> print(f"Found {results['total']} matching APIs")
            """
            return await self.backend_client.search_apis(
                gateway_id=gateway_id,
                query=query,
                limit=limit,
                status=status,
                is_shadow=is_shadow
            )
        
        @self.tool(description="Get complete details of a specific API including policies and metrics")
        async def get_api(gateway_id: str, api_id: str) -> Dict[str, Any]:
            """Get complete details of a specific API.
            
            Retrieves comprehensive API information including configuration, policies,
            current metrics, intelligence metadata, and health score.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: API UUID (required)
            
            Returns:
                dict: Complete API object with all fields including:
                    - id, name, base_path, version
                    - status, is_shadow
                    - policy_actions: Applied policies
                    - current_metrics: Latest performance metrics
                    - intelligence_metadata: AI-derived insights
                    - health_score: Overall health (0.0-1.0)
            
            Example:
                >>> api = await get_api(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     api_id="660e8400-e29b-41d4-a716-446655440001"
                ... )
                >>> print(f"API: {api['name']}")
                >>> print(f"Health: {api['intelligence_metadata']['health_score']}")
            """
            return await self.backend_client.get_api(gateway_id=gateway_id, api_id=api_id)
        
        @self.tool(description="Get security-related policy actions configured for an API")
        async def get_api_security_policies(gateway_id: str, api_id: str) -> Dict[str, Any]:
            """Get security policies for an API.
            
            Retrieves security-related policy actions including authentication,
            authorization, rate limiting, TLS, validation, and security headers.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: API UUID (required)
            
            Returns:
                list: Security-related PolicyAction objects
            
            Example:
                >>> policies = await get_api_security_policies(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     api_id="660e8400-e29b-41d4-a716-446655440001"
                ... )
                >>> for policy in policies:
                ...     print(f"  - {policy['action_type']}: {policy['enabled']}")
            """
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/apis/{api_id}/security-policies")
        
        @self.tool(description="Search gateways using flexible multi-criteria filtering")
        async def search_gateways(
            name: Optional[str] = None,
            vendor: Optional[str] = None,
            status: Optional[str] = None,
            created_after: Optional[str] = None,
            created_before: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
        ) -> Dict[str, Any]:
            """Search gateways using flexible multi-criteria filtering.
            
            Use this tool when the user's query requires combining multiple filters
            that go beyond simple list operations.
            
            IMPORTANT: Prefer this tool over list_gateways when the query includes:
            - Text pattern matching (name contains)
            - Multiple filter combinations (status AND vendor)
            - Date range filtering (created between dates)
            
            Args:
                name: Gateway name pattern (case-insensitive partial match)
                vendor: Gateway vendor filter (native, kong, apigee, aws, azure, mulesoft, webmethods)
                status: Status filter (connected, disconnected, error)
                created_after: Created after date (ISO 8601 format)
                created_before: Created before date (ISO 8601 format)
                page: Page number (1-based, default: 1)
                page_size: Items per page (1-100, default: 20)
            
            Returns:
                dict: Search results with:
                    - items: List of gateway objects
                    - total: Total matching count
                    - page: Current page number
                    - page_size: Items per page
            
            Example:
                >>> result = await search_gateways(
                ...     name="prod",
                ...     vendor="kong",
                ...     status="connected"
                ... )
                >>> print(f"Found {result['total']} matching gateways")
            """
            params: Dict[str, Any] = {"page": page, "page_size": page_size}
            if name:
                params["name"] = name
            if vendor:
                params["vendor"] = vendor
            if status:
                params["status"] = status
            if created_after:
                params["created_after"] = created_after
            if created_before:
                params["created_before"] = created_before
            return await self.backend_client._request("GET", "/gateways/search", params=params)
        
        @self.tool(description="Search APIs across all gateways using flexible multi-criteria filtering")
        async def search_all_apis(
            name: Optional[str] = None,
            description: Optional[str] = None,
            status: Optional[str] = None,
            authentication_type: Optional[str] = None,
            is_shadow: Optional[bool] = None,
            health_score_min: Optional[float] = None,
            health_score_max: Optional[float] = None,
            gateway_id: Optional[str] = None,
            created_after: Optional[str] = None,
            created_before: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
        ) -> Dict[str, Any]:
            """Search APIs across all gateways using flexible multi-criteria filtering.
            
            Use this tool when the user's query requires combining multiple filters
            that go beyond simple list operations.
            
            IMPORTANT: Prefer this tool over list_all_apis when the query includes:
            - Text pattern matching (name/description contains)
            - Multiple filter combinations (status AND authentication_type AND is_shadow)
            - Date range filtering (created between dates)
            - Numeric range filtering (health score thresholds)
            
            Args:
                name: API name pattern (case-insensitive partial match)
                description: Description pattern (case-insensitive partial match)
                status: Status filter (active, inactive, deprecated, failed)
                authentication_type: Authentication type filter
                is_shadow: Filter shadow APIs (true/false)
                health_score_min: Minimum health score (0.0-1.0)
                health_score_max: Maximum health score (0.0-1.0)
                gateway_id: Optional gateway filter
                created_after: Created after date (ISO 8601 format)
                created_before: Created before date (ISO 8601 format)
                page: Page number (1-based, default: 1)
                page_size: Items per page (1-100, default: 20)
            
            Returns:
                dict: Search results with:
                    - items: List of API objects
                    - total: Total matching count
                    - page: Current page number
                    - page_size: Items per page
            
            Example:
                >>> result = await search_all_apis(
                ...     name="payment",
                ...     status="active",
                ...     health_score_min=0.7,
                ...     is_shadow=False
                ... )
                >>> print(f"Found {result['total']} matching APIs")
            """
            params: Dict[str, Any] = {"page": page, "page_size": page_size}
            if name:
                params["name"] = name
            if description:
                params["description"] = description
            if status:
                params["status"] = status
            if authentication_type:
                params["authentication_type"] = authentication_type
            if is_shadow is not None:
                params["is_shadow"] = is_shadow
            if health_score_min is not None:
                params["health_score_min"] = health_score_min
            if health_score_max is not None:
                params["health_score_max"] = health_score_max
            if gateway_id:
                params["gateway_id"] = gateway_id
            if created_after:
                params["created_after"] = created_after
            if created_before:
                params["created_before"] = created_before
            return await self.backend_client._request("GET", "/apis/search", params=params)
        
        # ============================================================================
        # METRICS & ANALYTICS (6 tools)
        # ============================================================================
        
        @self.tool(description="Get time-bucketed analytics metrics across all gateways or specific gateway")
        async def get_analytics_metrics(
            gateway_id: Optional[str] = None,
            api_id: Optional[str] = None,
            time_bucket: str = "1h",
            limit: int = 50
        ) -> Dict[str, Any]:
            """Get analytics metrics across gateways.
            
            Retrieves time-bucketed metrics for analytics dashboard. Supports filtering
            by gateway and API with configurable time bucket granularity.
            
            Args:
                gateway_id: Optional gateway filter
                api_id: Optional API filter
                time_bucket: Time bucket size (1m, 5m, 1h, 1d, default: 1h)
                limit: Maximum results (1-1000, default: 50)
            
            Returns:
                dict: Analytics metrics with:
                    - items: List of time-bucketed metric objects
                    - total: Total data points
                    - time_bucket: Bucket size used
            
            Example:
                >>> metrics = await get_analytics_metrics(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     time_bucket="1h",
                ...     limit=24
                ... )
                >>> print(f"Retrieved {len(metrics['items'])} hourly data points")
            """
            params: Dict[str, Any] = {"time_bucket": time_bucket, "limit": limit}
            if gateway_id:
                params["gateway_id"] = gateway_id
            if api_id:
                params["api_id"] = api_id
            return await self.backend_client._request("GET", "/analytics/metrics", params=params)
        
        @self.tool(description="Get aggregated metrics summary across all gateways for last 24 hours")
        async def get_metrics_summary(gateway_id: Optional[str] = None) -> Dict[str, Any]:
            """Get metrics summary across gateways.
            
            Provides aggregated summary statistics for the last 24 hours including
            total requests, average response time, and error rate.
            
            Args:
                gateway_id: Optional gateway filter
            
            Returns:
                dict: Summary metrics with:
                    - total_requests_24h: Total requests
                    - avg_response_time: Average response time (ms)
                    - avg_error_rate: Average error rate (%)
            
            Example:
                >>> summary = await get_metrics_summary()
                >>> print(f"Requests: {summary['total_requests_24h']}")
                >>> print(f"Avg Response Time: {summary['avg_response_time']}ms")
                >>> print(f"Error Rate: {summary['avg_error_rate']}%")
            """
            params = {"gateway_id": gateway_id} if gateway_id else {}
            return await self.backend_client._request("GET", "/metrics/summary", params=params)
        
        @self.tool(description="Get time-bucketed performance metrics for a specific API")
        async def get_api_metrics(
            gateway_id: str,
            api_id: str,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            time_bucket: str = "5m"
        ) -> Dict[str, Any]:
            """Get time-bucketed metrics for an API.
            
            Retrieves detailed performance metrics with time-series data, cache metrics,
            timing breakdown, and status breakdown for a specific API.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: API UUID (required)
                start_time: Start time (ISO 8601, default: 24 hours ago)
                end_time: End time (ISO 8601, default: now)
                time_bucket: Bucket size (1m, 5m, 1h, 1d, default: 5m)
            
            Returns:
                dict: Comprehensive metrics with:
                    - time_series: Time-bucketed data points
                    - aggregated: Overall aggregated metrics
                    - cache_metrics: Cache hit rates
                    - timing_breakdown: Response time percentiles
                    - status_breakdown: HTTP status distribution
            
            Example:
                >>> metrics = await get_api_metrics(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     api_id="660e8400-e29b-41d4-a716-446655440001",
                ...     time_bucket="1h"
                ... )
                >>> print(f"Avg response time: {metrics['aggregated']['avg_response_time']}ms")
            """
            return await self.backend_client.get_api_metrics(
                gateway_id=gateway_id,
                api_id=api_id,
                start_time=start_time,
                end_time=end_time,
                interval=time_bucket
            )
        
        @self.tool(description="Drill down from analytics metric to source transactional logs")
        async def drill_down_to_logs(metric_id: str, limit: int = 100) -> Dict[str, Any]:
            """Drill down from metric to transactional logs.
            
            Traces a specific metric back to individual transactional logs that were
            aggregated to create it. Useful for debugging performance issues.
            
            Args:
                metric_id: Metric UUID
                limit: Maximum logs to return (1-1000, default: 100)
            
            Returns:
                dict: Drill-down results with:
                    - items: List of transactional log entries
                    - total: Total logs in time range
                    - metric_summary: Original metric context
                    - time_range: Time period covered
            
            Example:
                >>> logs = await drill_down_to_logs(
                ...     metric_id="770e8400-e29b-41d4-a716-446655440002",
                ...     limit=50
                ... )
                >>> print(f"Found {logs['total']} logs for this metric")
            """
            params = {"limit": limit}
            return await self.backend_client._request("GET", f"/analytics/metrics/{metric_id}/logs", params=params)
        
        @self.tool(description="Drill down from gateway metric to transactional logs within gateway scope")
        async def drill_down_to_gateway_logs(
            gateway_id: str,
            metric_id: str,
            limit: int = 100
        ) -> Dict[str, Any]:
            """Drill down from gateway metric to logs.
            
            Gateway-scoped version of drill-down functionality. Traces metric to
            transactional logs within a specific gateway context.
            
            Args:
                gateway_id: Gateway UUID (required)
                metric_id: Metric UUID
                limit: Maximum logs (1-1000, default: 100)
            
            Returns:
                dict: Drill-down results with logs and metric context
            
            Example:
                >>> logs = await drill_down_to_gateway_logs(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     metric_id="770e8400-e29b-41d4-a716-446655440002",
                ...     limit=100
                ... )
            """
            params = {"limit": limit}
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/metrics/{metric_id}/logs", params=params)
        
        @self.tool(description="Get aggregated metrics summary for all APIs within a gateway")
        async def get_gateway_metrics_summary(
            gateway_id: str,
            status: Optional[str] = None,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None
        ) -> Dict[str, Any]:
            """Get metrics summary for gateway APIs.
            
            Provides aggregated metrics across all APIs in a gateway including
            total APIs, requests, response times, error rates, and health scores.
            
            Args:
                gateway_id: Gateway UUID (required)
                status: Optional API status filter
                start_time: Start time (ISO 8601, default: 24 hours ago)
                end_time: End time (ISO 8601, default: now)
            
            Returns:
                dict: Gateway-wide metrics summary with:
                    - total_apis: Number of APIs
                    - total_requests_24h: Total requests
                    - avg_response_time: Average response time
                    - avg_error_rate: Average error rate
                    - avg_throughput: Average throughput
                    - avg_health_score: Average health score
            
            Example:
                >>> summary = await get_gateway_metrics_summary(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     status="active"
                ... )
                >>> print(f"Gateway has {summary['total_apis']} active APIs")
            """
            params: Dict[str, Any] = {}
            if status:
                params["status"] = status
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/metrics/summary", params=params)
        
        # ============================================================================
        # SECURITY (11 tools - includes 1 search tool)
        # ============================================================================
        
        @self.tool(description="Get security summary with vulnerability counts across all gateways")
        async def get_security_summary(gateway_id: Optional[str] = None) -> Dict[str, Any]:
            """Get security summary across gateways.
            
            Provides aggregated security metrics including total vulnerabilities
            broken down by severity level (critical, high, medium, low).
            
            Args:
                gateway_id: Optional gateway filter
            
            Returns:
                dict: Security summary with:
                    - total_vulnerabilities: Total count
                    - critical_vulnerabilities: Critical count
                    - high_vulnerabilities: High count
                    - medium_vulnerabilities: Medium count
                    - low_vulnerabilities: Low count
            
            Example:
                >>> summary = await get_security_summary()
                >>> print(f"Total vulnerabilities: {summary['total_vulnerabilities']}")
                >>> print(f"Critical: {summary['critical_vulnerabilities']}")
            """
            params = {"gateway_id": gateway_id} if gateway_id else {}
            return await self.backend_client._request("GET", "/security/summary", params=params)
        
        @self.tool(description="List security vulnerabilities across all gateways with comprehensive filtering")
        async def list_all_vulnerabilities(
            gateway_id: Optional[str] = None,
            api_id: Optional[str] = None,
            status: Optional[str] = None,
            severity: Optional[str] = None,
            limit: int = 100
        ) -> Dict[str, Any]:
            """List vulnerabilities across gateways.
            
            Retrieves vulnerabilities with optional filtering by gateway, API,
            status, and severity. Supports cross-gateway queries.
            
            Args:
                gateway_id: Optional gateway filter
                api_id: Optional API filter
                status: Status filter (open, remediated, in_progress, verified)
                severity: Severity filter (critical, high, medium, low)
                limit: Maximum results (1-1000, default: 100)
            
            Returns:
                list: Vulnerability objects
            
            Example:
                >>> vulns = await list_all_vulnerabilities(
                ...     severity="critical",
                ...     status="open",
                ...     limit=50
                ... )
                >>> print(f"Found {len(vulns)} critical open vulnerabilities")
            """
            params: Dict[str, Any] = {"limit": limit}
            if gateway_id:
                params["gateway_id"] = gateway_id
            if api_id:
                params["api_id"] = api_id
            if status:
                params["status"] = status
            if severity:
                params["severity"] = severity
            return await self.backend_client._request("GET", "/security/vulnerabilities", params=params)
        
        @self.tool(description="Get comprehensive security posture metrics and risk score")
        async def get_security_posture(
            gateway_id: Optional[str] = None,
            api_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """Get security posture metrics.
            
            Provides comprehensive security health metrics including vulnerability
            breakdown, remediation rate, risk score, and average remediation time.
            
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
                    - risk_level: Risk classification
                    - avg_remediation_time_ms: Average time to fix
            
            Example:
                >>> posture = await get_security_posture()
                >>> print(f"Risk Score: {posture['risk_score']}/100")
                >>> print(f"Risk Level: {posture['risk_level']}")
                >>> print(f"Remediation Rate: {posture['remediation_rate']}%")
            """
            params: Dict[str, Any] = {}
            if gateway_id:
                params["gateway_id"] = gateway_id
            if api_id:
                params["api_id"] = api_id
            return await self.backend_client._request("GET", "/security/posture", params=params)
        
        @self.tool(description="Scan API for security vulnerabilities using hybrid rule-based and AI analysis")
        async def scan_api_security(gateway_id: str, api_id: str) -> Dict[str, Any]:
            """Scan API for security vulnerabilities.
            
            Performs comprehensive security analysis using hybrid approach combining
            rule-based checks with AI-enhanced severity assessment. Analyzes API
            metadata, policies, metrics, and traffic patterns.
            
            Security checks include:
            - Authentication policy coverage
            - Authorization policy coverage
            - Rate limiting configuration
            - TLS/SSL configuration
            - CORS policy review
            - Input validation checks
            - Security header analysis
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: API UUID (required)
            
            Returns:
                dict: Scan results with:
                    - scan_id: Unique scan identifier
                    - api_id: API identifier
                    - api_name: API name
                    - scan_completed_at: Completion timestamp
                    - vulnerabilities_found: Number of vulnerabilities
                    - severity_breakdown: By severity level
                    - vulnerabilities: Detailed vulnerability list
                    - remediation_plan: Automated remediation plan
            
            Example:
                >>> result = await scan_api_security(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     api_id="660e8400-e29b-41d4-a716-446655440001"
                ... )
                >>> print(f"Found {result['vulnerabilities_found']} vulnerabilities")
            """
            payload = {"gateway_id": gateway_id, "api_id": api_id}
            return await self.backend_client._request("POST", f"/gateways/{gateway_id}/security/scan", json=payload)
        
        @self.tool(description="List security vulnerabilities for a specific gateway with filtering")
        async def list_vulnerabilities(
            gateway_id: str,
            api_id: Optional[str] = None,
            status: Optional[str] = None,
            severity: Optional[str] = None,
            limit: int = 100
        ) -> Dict[str, Any]:
            """List vulnerabilities for a gateway.
            
            Retrieves vulnerabilities within a specific gateway with optional
            filtering by API, status, and severity.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
                status: Status filter (open, remediated, in_progress, verified)
                severity: Severity filter (critical, high, medium, low)
                limit: Maximum results (1-1000, default: 100)
            
            Returns:
                list: Vulnerability objects for the gateway
            
            Example:
                >>> vulns = await list_vulnerabilities(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     severity="high",
                ...     status="open"
                ... )
            """
            params: Dict[str, Any] = {"limit": limit}
            if api_id:
                params["api_id"] = api_id
            if status:
                params["status"] = status
            if severity:
                params["severity"] = severity
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/security/vulnerabilities", params=params)
        
        @self.tool(description="Get detailed information about a specific security vulnerability")
        async def get_vulnerability(gateway_id: str, vulnerability_id: str) -> Dict[str, Any]:
            """Get vulnerability details.
            
            Retrieves complete information about a specific vulnerability including
            description, severity, affected API, remediation steps, and status.
            
            Args:
                gateway_id: Gateway UUID (required)
                vulnerability_id: Vulnerability UUID
            
            Returns:
                dict: Complete vulnerability object
            
            Example:
                >>> vuln = await get_vulnerability(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     vulnerability_id="770e8400-e29b-41d4-a716-446655440002"
                ... )
                >>> print(f"Vulnerability: {vuln['title']}")
                >>> print(f"Severity: {vuln['severity']}")
            """
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/security/vulnerabilities/{vulnerability_id}")
        
        @self.tool(description="Trigger automated remediation for a security vulnerability")
        async def remediate_vulnerability(
            gateway_id: str,
            vulnerability_id: str,
            remediation_strategy: Optional[str] = None
        ) -> Dict[str, Any]:
            """Remediate a vulnerability.
            
            Triggers automated remediation by applying appropriate security policies
            to the API Gateway. Supports various remediation strategies including
            authentication, authorization, rate limiting, TLS, CORS, headers, and validation.
            
            Args:
                gateway_id: Gateway UUID (required)
                vulnerability_id: Vulnerability UUID
                remediation_strategy: Optional specific strategy to use
            
            Returns:
                dict: Remediation result with:
                    - vulnerability_id: Vulnerability identifier
                    - status: Remediation status
                    - remediation_result: Applied remediation details
                    - verification_result: Effectiveness verification
                    - message: Status message
            
            Example:
                >>> result = await remediate_vulnerability(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     vulnerability_id="770e8400-e29b-41d4-a716-446655440002"
                ... )
                >>> print(f"Remediation status: {result['status']}")
            """
            payload = {}
            if remediation_strategy:
                payload["remediation_strategy"] = remediation_strategy
            return await self.backend_client._request(
                "POST",
                f"/gateways/{gateway_id}/security/vulnerabilities/{vulnerability_id}/remediate",
                json=payload if payload else None
            )
        
        @self.tool(description="Verify that vulnerability remediation was effective")
        async def verify_remediation(gateway_id: str, vulnerability_id: str) -> Dict[str, Any]:
            """Verify vulnerability remediation.
            
            Re-scans the API to confirm that the vulnerability has been effectively
            remediated and is no longer present.
            
            Args:
                gateway_id: Gateway UUID (required)
                vulnerability_id: Vulnerability UUID
            
            Returns:
                dict: Verification result with:
                    - vulnerability_id: Vulnerability identifier
                    - verified: Whether remediation was successful
                    - verification_timestamp: When verification was performed
                    - details: Verification details
            
            Example:
                >>> result = await verify_remediation(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     vulnerability_id="770e8400-e29b-41d4-a716-446655440002"
                ... )
                >>> print(f"Verified: {result['verified']}")
            """
            return await self.backend_client._request(
                "POST",
                f"/gateways/{gateway_id}/security/vulnerabilities/{vulnerability_id}/verify"
            )
        
        @self.tool(description="Get security summary for a specific gateway")
        async def get_gateway_security_summary(gateway_id: str) -> Dict[str, Any]:
            """Get security summary for gateway.
            
            Provides gateway-specific security metrics including vulnerability counts
            by severity level.
            
            Args:
                gateway_id: Gateway UUID (required)
            
            Returns:
                dict: Security summary for the gateway
            
            Example:
                >>> summary = await get_gateway_security_summary(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000"
                ... )
            """
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/security/summary")
        
        @self.tool(description="Get security posture for a specific gateway")
        async def get_gateway_security_posture(
            gateway_id: str,
            api_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """Get security posture for gateway.
            
            Gateway-scoped security posture metrics including risk score and
            remediation statistics.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
            
            Returns:
                dict: Security posture metrics for the gateway
            
            Example:
                >>> posture = await get_gateway_security_posture(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000"
                ... )
            """
            params = {"api_id": api_id} if api_id else {}
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/security/posture", params=params)
        
        @self.tool(description="Search security vulnerabilities using flexible multi-criteria filtering")
        async def search_vulnerabilities(
            severity: Optional[str] = None,
            vulnerability_type: Optional[str] = None,
            status: Optional[str] = None,
            api_name: Optional[str] = None,
            gateway_id: Optional[str] = None,
            discovered_after: Optional[str] = None,
            discovered_before: Optional[str] = None,
            page: int = 1,
            page_size: int = 100
        ) -> Dict[str, Any]:
            """Search security vulnerabilities using flexible multi-criteria filtering.
            
            Use this tool when the user's query requires combining multiple filters
            that go beyond simple list operations.
            
            IMPORTANT: Prefer this tool over list_all_vulnerabilities when the query includes:
            - Text pattern matching (API name contains)
            - Multiple filter combinations (severity AND type AND status)
            - Date range filtering (discovered between dates)
            
            Args:
                severity: Severity filter (critical, high, medium, low)
                vulnerability_type: Type filter (missing_authentication, weak_authorization, etc.)
                status: Status filter (open, remediated, in_progress, verified)
                api_name: API name pattern (case-insensitive partial match)
                gateway_id: Optional gateway filter
                discovered_after: Discovered after date (ISO 8601 format)
                discovered_before: Discovered before date (ISO 8601 format)
                page: Page number (1-based, default: 1)
                page_size: Items per page (1-1000, default: 100)
            
            Returns:
                dict: Search results with:
                    - items: List of vulnerability objects
                    - total: Total matching count
                    - page: Current page number
                    - page_size: Items per page
            
            Example:
                >>> result = await search_vulnerabilities(
                ...     severity="critical",
                ...     status="open",
                ...     discovered_after="2026-01-01T00:00:00Z"
                ... )
                >>> print(f"Found {result['total']} critical open vulnerabilities")
            """
            params: Dict[str, Any] = {"page": page, "page_size": page_size}
            if severity:
                params["severity"] = severity
            if vulnerability_type:
                params["type"] = vulnerability_type
            if status:
                params["status"] = status
            if api_name:
                params["api_name"] = api_name
            if gateway_id:
                params["gateway_id"] = gateway_id
            if discovered_after:
                params["discovered_after"] = discovered_after
            if discovered_before:
                params["discovered_before"] = discovered_before
            return await self.backend_client._request("GET", "/security/vulnerabilities/search", params=params)
        
        # ============================================================================
        # COMPLIANCE (6 tools - includes 1 search tool)
        # ============================================================================
        
        @self.tool(description="Scan API for compliance violations across 5 regulatory standards")
        async def scan_api_compliance(
            gateway_id: str,
            api_id: str,
            standards: Optional[List[str]] = None
        ) -> Dict[str, Any]:
            """Scan API for compliance violations.
            
            Performs comprehensive compliance analysis across 5 regulatory standards:
            GDPR, HIPAA, SOC2, PCI-DSS, and ISO 27001. Uses AI-driven detection to
            identify violations and collect audit evidence.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: API UUID (required)
                standards: Optional list of specific standards to check
                          (default: all 5 standards)
            
            Returns:
                dict: Scan results with:
                    - scan_id: Unique scan identifier
                    - api_id: API identifier
                    - api_name: API name
                    - scan_completed_at: Completion timestamp
                    - violations_found: Number of violations
                    - severity_breakdown: By severity level
                    - standard_breakdown: By compliance standard
                    - violations: Detailed violation list
                    - audit_evidence: Evidence for auditors
            
            Example:
                >>> result = await scan_api_compliance(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     api_id="660e8400-e29b-41d4-a716-446655440001",
                ...     standards=["GDPR", "HIPAA"]
                ... )
                >>> print(f"Found {result['violations_found']} violations")
            """
            return await self.backend_client.scan_api_compliance(
                gateway_id=gateway_id,
                api_id=api_id,
                standards=standards
            )
        
        @self.tool(description="List compliance violations for a gateway with filtering")
        async def list_compliance_violations(
            gateway_id: str,
            api_id: Optional[str] = None,
            standard: Optional[str] = None,
            severity: Optional[str] = None,
            status: Optional[str] = None,
            limit: int = 100
        ) -> Dict[str, Any]:
            """List compliance violations for gateway.
            
            Retrieves compliance violations with optional filtering by API,
            standard, severity, and status.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
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
                ...     severity="high"
                ... )
            """
            params: Dict[str, Any] = {"limit": limit}
            if api_id:
                params["api_id"] = api_id
            if standard:
                params["standard"] = standard
            if severity:
                params["severity"] = severity
            if status:
                params["status"] = status
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/compliance/violations", params=params)
        
        @self.tool(description="Get compliance posture metrics and scores for a gateway")
        async def get_compliance_posture(
            gateway_id: str,
            api_id: Optional[str] = None,
            standard: Optional[str] = None
        ) -> Dict[str, Any]:
            """Get compliance posture for gateway.
            
            Provides compliance health metrics including violation counts,
            remediation rate, compliance score, and next audit date.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
                standard: Optional standard filter
            
            Returns:
                dict: Compliance posture with:
                    - total_violations: Total count
                    - by_severity: Breakdown by severity
                    - by_status: Breakdown by status
                    - by_standard: Breakdown by standard
                    - remediation_rate: Percentage remediated
                    - compliance_score: Overall score (0-100)
                    - last_scan: Last scan timestamp
                    - next_audit_date: Next recommended audit
            
            Example:
                >>> posture = await get_compliance_posture(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     standard="HIPAA"
                ... )
                >>> print(f"Compliance score: {posture['compliance_score']}")
            """
            return await self.backend_client.get_compliance_posture(
                gateway_id=gateway_id,
                api_id=api_id,
                standard=standard
            )
        
        @self.tool(description="Generate comprehensive audit report with evidence and recommendations")
        async def generate_audit_report(
            gateway_id: str,
            api_id: Optional[str] = None,
            standard: Optional[str] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
        ) -> Dict[str, Any]:
            """Generate audit report for gateway.
            
            Creates comprehensive audit report suitable for external auditors with
            AI-generated executive summary, compliance analysis, and recommendations.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
                standard: Optional standard filter
                start_date: Report start date (ISO 8601, default: 90 days ago)
                end_date: Report end date (ISO 8601, default: now)
            
            Returns:
                dict: Comprehensive audit report with:
                    - report_id: Unique identifier
                    - generated_at: Generation timestamp
                    - report_period: Time period covered
                    - executive_summary: AI-generated summary
                    - compliance_posture: Overall metrics
                    - violations_by_standard: Breakdown by standard
                    - violations_by_severity: Breakdown by severity
                    - remediation_status: Remediation tracking
                    - violations_needing_audit: Items for audit attention
                    - audit_evidence: Collected evidence
                    - recommendations: Actionable recommendations
            
            Example:
                >>> report = await generate_audit_report(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     standard="GDPR"
                ... )
                >>> print(report['executive_summary'])
            """
            return await self.backend_client.generate_audit_report(
                gateway_id=gateway_id,
                api_id=api_id,
                standard=standard,
                start_date=start_date,
                end_date=end_date
            )
        
        @self.tool(description="Get detailed information about a specific compliance violation")
        async def get_compliance_violation(
            gateway_id: str,
            violation_id: str
        ) -> Dict[str, Any]:
            """Get compliance violation details.
            
            Retrieves complete information about a specific compliance violation
            including standard, requirement, severity, and remediation guidance.
            
            Args:
                gateway_id: Gateway UUID (required)
                violation_id: Violation UUID
            
            Returns:
                dict: Complete violation object
            
            Example:
                >>> violation = await get_compliance_violation(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     violation_id="880e8400-e29b-41d4-a716-446655440003"
                ... )
                >>> print(f"Violation: {violation['title']}")
            """
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/compliance/violations/{violation_id}")
        
        @self.tool(description="Search compliance violations using flexible multi-criteria filtering")
        async def search_compliance_violations(
            standard: Optional[str] = None,
            violation_type: Optional[str] = None,
            severity: Optional[str] = None,
            status: Optional[str] = None,
            api_name: Optional[str] = None,
            gateway_id: Optional[str] = None,
            discovered_after: Optional[str] = None,
            discovered_before: Optional[str] = None,
            page: int = 1,
            page_size: int = 100
        ) -> Dict[str, Any]:
            """Search compliance violations using flexible multi-criteria filtering.
            
            Use this tool when the user's query requires combining multiple filters
            that go beyond simple list operations.
            
            IMPORTANT: Prefer this tool over list_compliance_violations when the query includes:
            - Text pattern matching (API name contains)
            - Multiple filter combinations (standard AND severity AND status)
            - Date range filtering (discovered between dates)
            - Standard-specific filtering for audit reports
            
            Args:
                standard: Standard filter (GDPR, HIPAA, SOC2, PCI_DSS, ISO_27001)
                violation_type: Violation type filter
                severity: Severity filter (critical, high, medium, low)
                status: Status filter (open, in_progress, remediated)
                api_name: API name pattern (case-insensitive partial match)
                gateway_id: Optional gateway filter
                discovered_after: Discovered after date (ISO 8601 format)
                discovered_before: Discovered before date (ISO 8601 format)
                page: Page number (1-based, default: 1)
                page_size: Items per page (1-1000, default: 100)
            
            Returns:
                dict: Search results with:
                    - items: List of compliance violation objects
                    - total: Total matching count
                    - page: Current page number
                    - page_size: Items per page
            
            Example:
                >>> result = await search_compliance_violations(
                ...     standard="GDPR",
                ...     severity="high",
                ...     status="open"
                ... )
                >>> print(f"Found {result['total']} GDPR violations")
            """
            params: Dict[str, Any] = {"page": page, "page_size": page_size}
            if standard:
                params["standard"] = standard
            if violation_type:
                params["violation_type"] = violation_type
            if severity:
                params["severity"] = severity
            if status:
                params["status"] = status
            if api_name:
                params["api_name"] = api_name
            if gateway_id:
                params["gateway_id"] = gateway_id
            if discovered_after:
                params["discovered_after"] = discovered_after
            if discovered_before:
                params["discovered_before"] = discovered_before
            return await self.backend_client._request("GET", "/compliance/violations/search", params=params)
        
        # ============================================================================
        # OPTIMIZATION (13 tools - includes 1 search tool)
        # ============================================================================
        
        @self.tool(description="Generate AI-driven optimization recommendations for an API")
        async def generate_recommendations(
            gateway_id: str,
            api_id: str,
            min_impact: float = 10.0
        ) -> Dict[str, Any]:
            """Generate optimization recommendations.
            
            Triggers AI-driven analysis to generate performance optimization
            recommendations including caching, compression, and rate limiting.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: API UUID (required)
                min_impact: Minimum expected improvement % (0-100, default: 10.0)
            
            Returns:
                dict: Generation result with status and message
            
            Example:
                >>> result = await generate_recommendations(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     api_id="660e8400-e29b-41d4-a716-446655440001",
                ...     min_impact=15.0
                ... )
            """
            params = {"api_id": api_id, "min_impact": min_impact}
            return await self.backend_client._request(
                "POST",
                f"/gateways/{gateway_id}/optimization/recommendations/generate",
                params=params
            )
        
        @self.tool(description="List optimization recommendations for a gateway")
        async def list_recommendations(
            gateway_id: str,
            api_id: Optional[str] = None,
            priority: Optional[str] = None,
            status: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
        ) -> Dict[str, Any]:
            """List optimization recommendations.
            
            Retrieves optimization recommendations with optional filtering by
            API, priority, and status.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
                priority: Priority filter (high, medium, low)
                status: Status filter (pending, implemented, rejected)
                page: Page number (1-indexed, default: 1)
                page_size: Items per page (1-100, default: 20)
            
            Returns:
                dict: Paginated recommendations list
            
            Example:
                >>> recs = await list_recommendations(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     priority="high",
                ...     status="pending"
                ... )
            """
            return await self.backend_client.list_recommendations(
                gateway_id=gateway_id,
                api_id=api_id,
                priority=priority,
                status=status,
                page=page,
                page_size=page_size
            )
        
        @self.tool(description="Get detailed information about a specific recommendation")
        async def get_recommendation(
            gateway_id: str,
            recommendation_id: str
        ) -> Dict[str, Any]:
            """Get recommendation details.
            
            Retrieves complete information about a specific optimization
            recommendation including estimated impact and implementation steps.
            
            Args:
                gateway_id: Gateway UUID (required)
                recommendation_id: Recommendation UUID
            
            Returns:
                dict: Complete recommendation object
            
            Example:
                >>> rec = await get_recommendation(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     recommendation_id="990e8400-e29b-41d4-a716-446655440004"
                ... )
            """
            return await self.backend_client._request(
                "GET",
                f"/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}"
            )
        
        @self.tool(description="Apply optimization recommendation to Gateway")
        async def apply_recommendation(
            gateway_id: str,
            recommendation_id: str
        ) -> Dict[str, Any]:
            """Apply recommendation to Gateway.
            
            Applies the optimization policy (caching, compression, rate limiting)
            to the actual Gateway and updates recommendation status.
            
            Args:
                gateway_id: Gateway UUID (required)
                recommendation_id: Recommendation UUID
            
            Returns:
                dict: Application result with success status
            
            Example:
                >>> result = await apply_recommendation(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     recommendation_id="990e8400-e29b-41d4-a716-446655440004"
                ... )
            """
            return await self.backend_client._request(
                "POST",
                f"/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/apply"
            )
        
        @self.tool(description="Remove applied optimization policy from Gateway")
        async def remove_recommendation_policy(
            gateway_id: str,
            recommendation_id: str
        ) -> Dict[str, Any]:
            """Remove recommendation policy.
            
            Removes a previously applied optimization policy from the Gateway
            and updates recommendation status to PENDING.
            
            Args:
                gateway_id: Gateway UUID (required)
                recommendation_id: Recommendation UUID
            
            Returns:
                dict: Removal result with success status
            
            Example:
                >>> result = await remove_recommendation_policy(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     recommendation_id="990e8400-e29b-41d4-a716-446655440004"
                ... )
            """
            return await self.backend_client._request(
                "DELETE",
                f"/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/policy"
            )
        
        @self.tool(description="Validate recommendation impact after implementation")
        async def validate_recommendation(
            gateway_id: str,
            recommendation_id: str,
            validation_window_hours: int = 24
        ) -> Dict[str, Any]:
            """Validate recommendation impact.
            
            Analyzes post-implementation metrics to determine if the recommendation
            achieved its expected improvement.
            
            Args:
                gateway_id: Gateway UUID (required)
                recommendation_id: Recommendation UUID
                validation_window_hours: Hours of metrics to analyze (default: 24)
            
            Returns:
                dict: Validation results with actual vs expected impact
            
            Example:
                >>> result = await validate_recommendation(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     recommendation_id="990e8400-e29b-41d4-a716-446655440004"
                ... )
            """
            params = {"validation_window_hours": validation_window_hours}
            return await self.backend_client._request(
                "POST",
                f"/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/validate",
                params=params
            )
        
        @self.tool(description="Get AI insights for a recommendation")
        async def get_recommendation_insights(
            gateway_id: str,
            recommendation_id: str
        ) -> Dict[str, Any]:
            """Get AI insights for recommendation.
            
            Retrieves AI-generated insights including performance analysis,
            implementation guidance, and prioritization rationale.
            
            Args:
                gateway_id: Gateway UUID (required)
                recommendation_id: Recommendation UUID
            
            Returns:
                dict: AI-generated insights
            
            Example:
                >>> insights = await get_recommendation_insights(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     recommendation_id="990e8400-e29b-41d4-a716-446655440004"
                ... )
            """
            return await self.backend_client._request(
                "GET",
                f"/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/insights"
            )
        
        @self.tool(description="Get recommendation action history")
        async def get_recommendation_actions(
            gateway_id: str,
            recommendation_id: str
        ) -> Dict[str, Any]:
            """Get recommendation action history.
            
            Returns all remediation actions taken on the recommendation including
            applications, removals, validations, and failures.
            
            Args:
                gateway_id: Gateway UUID (required)
                recommendation_id: Recommendation UUID
            
            Returns:
                list: Remediation action objects
            
            Example:
                >>> actions = await get_recommendation_actions(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     recommendation_id="990e8400-e29b-41d4-a716-446655440004"
                ... )
            """
            return await self.backend_client._request(
                "GET",
                f"/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/actions"
            )
        
        @self.tool(description="Get recommendation statistics for a gateway")
        async def get_recommendation_stats(
            gateway_id: str,
            api_id: Optional[str] = None,
            days: int = 30
        ) -> Dict[str, Any]:
            """Get recommendation statistics.
            
            Provides statistics about optimization recommendations including
            counts by status, priority, type, and cost savings.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
                days: Number of days to analyze (1-365, default: 30)
            
            Returns:
                dict: Recommendation statistics
            
            Example:
                >>> stats = await get_recommendation_stats(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     days=90
                ... )
            """
            params: Dict[str, Any] = {"days": days}
            if api_id:
                params["api_id"] = api_id
            return await self.backend_client._request(
                "GET",
                f"/gateways/{gateway_id}/optimization/recommendations/stats",
                params=params
            )
        
        @self.tool(description="Get optimization summary for a gateway")
        async def get_optimization_summary(gateway_id: str) -> Dict[str, Any]:
            """Get optimization summary.
            
            Provides aggregated optimization metrics including recommendation
            counts by priority.
            
            Args:
                gateway_id: Gateway UUID (required)
            
            Returns:
                dict: Optimization summary with counts by priority
            
            Example:
                >>> summary = await get_optimization_summary(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000"
                ... )
            """
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/optimization/summary")
        
        @self.tool(description="Get global optimization summary across all gateways")
        async def get_global_optimization_summary(
            gateway_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """Get global optimization summary.
            
            Provides optimization summary across all gateways or for a specific
            gateway when gateway_id is provided.
            
            Args:
                gateway_id: Optional gateway filter
            
            Returns:
                dict: Global optimization summary
            
            Example:
                >>> summary = await get_global_optimization_summary()
            """
            params = {"gateway_id": gateway_id} if gateway_id else {}
            return await self.backend_client._request("GET", "/optimization/summary", params=params)
        
        @self.tool(description="Search optimization recommendations using flexible multi-criteria filtering")
        async def search_recommendations(
            recommendation_type: Optional[str] = None,
            priority: Optional[str] = None,
            status: Optional[str] = None,
            impact_min: Optional[float] = None,
            impact_max: Optional[float] = None,
            api_name: Optional[str] = None,
            gateway_id: Optional[str] = None,
            created_after: Optional[str] = None,
            created_before: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
        ) -> Dict[str, Any]:
            """Search optimization recommendations using flexible multi-criteria filtering.
            
            Use this tool when the user's query requires combining multiple filters
            that go beyond simple list operations.
            
            IMPORTANT: Prefer this tool over list_recommendations when the query includes:
            - Text pattern matching (API name contains)
            - Multiple filter combinations (type AND priority AND status)
            - Date range filtering (created between dates)
            - Numeric range filtering (impact thresholds)
            - Implementation status tracking
            
            Args:
                recommendation_type: Type filter (caching, compression, rate_limiting)
                priority: Priority filter (high, medium, low)
                status: Status filter (pending, implemented, rejected)
                impact_min: Minimum expected impact percentage (0-100)
                impact_max: Maximum expected impact percentage (0-100)
                api_name: API name pattern (case-insensitive partial match)
                gateway_id: Optional gateway filter
                created_after: Created after date (ISO 8601 format)
                created_before: Created before date (ISO 8601 format)
                page: Page number (1-based, default: 1)
                page_size: Items per page (1-100, default: 20)
            
            Returns:
                dict: Search results with:
                    - items: List of recommendation objects
                    - total: Total matching count
                    - page: Current page number
                    - page_size: Items per page
            
            Example:
                >>> result = await search_recommendations(
                ...     priority="high",
                ...     status="pending",
                ...     impact_min=20.0
                ... )
                >>> print(f"Found {result['total']} high-priority recommendations")
            """
            params: Dict[str, Any] = {"page": page, "page_size": page_size}
            if recommendation_type:
                params["type"] = recommendation_type
            if priority:
                params["priority"] = priority
            if status:
                params["status"] = status
            if impact_min is not None:
                params["impact_min"] = impact_min
            if impact_max is not None:
                params["impact_max"] = impact_max
            if api_name:
                params["api_name"] = api_name
            if gateway_id:
                params["gateway_id"] = gateway_id
            if created_after:
                params["created_after"] = created_after
            if created_before:
                params["created_before"] = created_before
            return await self.backend_client._request("GET", "/optimization/recommendations/search", params=params)
        
        # ============================================================================
        # RATE LIMITING (8 tools)
        # ============================================================================
        
        @self.tool(description="Create intelligent rate limit policy for an API")
        async def create_rate_limit_policy(
            gateway_id: str,
            api_id: str,
            policy_name: str,
            policy_type: str,
            limit_thresholds: Dict[str, int],
            enforcement_action: str = "throttle"
        ) -> Dict[str, Any]:
            """Create rate limit policy.
            
            Creates an intelligent rate limit policy with specified thresholds
            and enforcement action.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: API UUID (required)
                policy_name: Policy name
                policy_type: Policy type (fixed, adaptive, priority_based)
                limit_thresholds: Thresholds dict with keys:
                    - requests_per_second (optional)
                    - requests_per_minute (optional)
                    - requests_per_hour (optional)
                    - concurrent_requests (optional)
                enforcement_action: Action (throttle, reject, queue, default: throttle)
            
            Returns:
                dict: Created policy object
            
            Example:
                >>> policy = await create_rate_limit_policy(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     api_id="660e8400-e29b-41d4-a716-446655440001",
                ...     policy_name="Production Rate Limit",
                ...     policy_type="adaptive",
                ...     limit_thresholds={
                ...         "requests_per_second": 100,
                ...         "requests_per_minute": 5000
                ...     }
                ... )
            """
            return await self.backend_client.create_rate_limit_policy(
                gateway_id=gateway_id,
                api_id=api_id,
                policy_name=policy_name,
                policy_type=policy_type,
                limit_thresholds=limit_thresholds,
                enforcement_action=enforcement_action
            )
        
        @self.tool(description="List rate limit policies for a gateway")
        async def list_rate_limit_policies(
            gateway_id: str,
            api_id: Optional[str] = None,
            status: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
        ) -> Dict[str, Any]:
            """List rate limit policies.
            
            Retrieves rate limit policies with optional filtering by API and status.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
                status: Status filter (active, inactive, draft)
                page: Page number (1-indexed, default: 1)
                page_size: Items per page (1-100, default: 20)
            
            Returns:
                dict: Paginated policies list
            
            Example:
                >>> policies = await list_rate_limit_policies(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     status="active"
                ... )
            """
            return await self.backend_client.list_rate_limit_policies(
                gateway_id=gateway_id,
                api_id=api_id,
                status=status,
                page=page,
                page_size=page_size
            )
        
        @self.tool(description="Get rate limit policy details")
        async def get_rate_limit_policy(
            gateway_id: str,
            policy_id: str
        ) -> Dict[str, Any]:
            """Get rate limit policy.
            
            Retrieves complete information about a specific rate limit policy.
            
            Args:
                gateway_id: Gateway UUID (required)
                policy_id: Policy UUID
            
            Returns:
                dict: Complete policy object
            
            Example:
                >>> policy = await get_rate_limit_policy(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     policy_id="aa0e8400-e29b-41d4-a716-446655440005"
                ... )
            """
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/rate-limits/{policy_id}")
        
        @self.tool(description="Activate rate limit policy")
        async def activate_rate_limit_policy(
            gateway_id: str,
            policy_id: str
        ) -> Dict[str, Any]:
            """Activate rate limit policy.
            
            Activates a rate limit policy, making it effective for the API.
            
            Args:
                gateway_id: Gateway UUID (required)
                policy_id: Policy UUID
            
            Returns:
                dict: Updated policy object
            
            Example:
                >>> policy = await activate_rate_limit_policy(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     policy_id="aa0e8400-e29b-41d4-a716-446655440005"
                ... )
            """
            return await self.backend_client._request("POST", f"/gateways/{gateway_id}/rate-limits/{policy_id}/activate")
        
        @self.tool(description="Deactivate rate limit policy")
        async def deactivate_rate_limit_policy(
            gateway_id: str,
            policy_id: str
        ) -> Dict[str, Any]:
            """Deactivate rate limit policy.
            
            Deactivates a rate limit policy, removing its effect from the API.
            
            Args:
                gateway_id: Gateway UUID (required)
                policy_id: Policy UUID
            
            Returns:
                dict: Updated policy object
            
            Example:
                >>> policy = await deactivate_rate_limit_policy(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     policy_id="aa0e8400-e29b-41d4-a716-446655440005"
                ... )
            """
            return await self.backend_client._request("POST", f"/gateways/{gateway_id}/rate-limits/{policy_id}/deactivate")
        
        @self.tool(description="Apply rate limit policy to Gateway")
        async def apply_rate_limit_policy(
            gateway_id: str,
            policy_id: str
        ) -> Dict[str, Any]:
            """Apply rate limit policy to Gateway.
            
            Applies the rate limit policy to the actual Gateway infrastructure.
            
            Args:
                gateway_id: Gateway UUID (required)
                policy_id: Policy UUID
            
            Returns:
                dict: Application result
            
            Example:
                >>> result = await apply_rate_limit_policy(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     policy_id="aa0e8400-e29b-41d4-a716-446655440005"
                ... )
            """
            return await self.backend_client._request("POST", f"/gateways/{gateway_id}/rate-limits/{policy_id}/apply")
        
        @self.tool(description="Get rate limit policy suggestion for an API")
        async def suggest_rate_limit_policy(
            gateway_id: str,
            api_id: str
        ) -> Dict[str, Any]:
            """Get rate limit policy suggestion.
            
            Analyzes API traffic patterns and suggests optimal rate limit policy
            parameters.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: API UUID
            
            Returns:
                dict: Suggested policy parameters
            
            Example:
                >>> suggestion = await suggest_rate_limit_policy(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     api_id="660e8400-e29b-41d4-a716-446655440001"
                ... )
            """
            return await self.backend_client._request("GET", f"/gateways/{gateway_id}/rate-limits/suggest/{api_id}")
        
        @self.tool(description="Analyze rate limit policy effectiveness")
        async def analyze_rate_limit_effectiveness(
            gateway_id: str,
            policy_id: str,
            analysis_period_hours: int = 24
        ) -> Dict[str, Any]:
            """Analyze rate limit effectiveness.
            
            Analyzes the effectiveness of a rate limit policy with metrics
            and recommendations.
            
            Args:
                gateway_id: Gateway UUID (required)
                policy_id: Policy UUID
                analysis_period_hours: Hours to analyze (1-720, default: 24)
            
            Returns:
                dict: Effectiveness analysis with metrics and recommendations
            
            Example:
                >>> analysis = await analyze_rate_limit_effectiveness(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     policy_id="aa0e8400-e29b-41d4-a716-446655440005",
                ...     analysis_period_hours=48
                ... )
            """
            params = {"analysis_period_hours": analysis_period_hours}
            return await self.backend_client._request(
                "GET",
                f"/gateways/{gateway_id}/rate-limits/{policy_id}/effectiveness",
                params=params
            )
        
        # ============================================================================
        # PREDICTIONS (6 tools - includes 1 search tool)
        # ============================================================================
        
        @self.tool(description="List failure predictions for a gateway")
        async def list_predictions(
            gateway_id: str,
            api_id: Optional[str] = None,
            severity: Optional[str] = None,
            status: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
        ) -> Dict[str, Any]:
            """List failure predictions.
            
            Retrieves scheduler-generated failure predictions with optional
            filtering by API, severity, and status.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
                severity: Severity filter (critical, high, medium, low)
                status: Status filter (active, resolved, false_positive, expired)
                page: Page number (1-indexed, default: 1)
                page_size: Items per page (1-100, default: 20)
            
            Returns:
                dict: Paginated predictions list
            
            Example:
                >>> predictions = await list_predictions(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     severity="critical",
                ...     status="active"
                ... )
            """
            return await self.backend_client.list_predictions(
                gateway_id=gateway_id,
                api_id=api_id,
                severity=severity,
                status=status,
                page=page,
                page_size=page_size
            )
        
        @self.tool(description="Get detailed information about a specific prediction")
        async def get_prediction(
            gateway_id: str,
            prediction_id: str
        ) -> Dict[str, Any]:
            """Get prediction details.
            
            Retrieves complete information about a specific failure prediction
            including contributing factors and recommended actions.
            
            Args:
                gateway_id: Gateway UUID (required)
                prediction_id: Prediction UUID
            
            Returns:
                dict: Complete prediction object
            
            Example:
                >>> prediction = await get_prediction(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     prediction_id="bb0e8400-e29b-41d4-a716-446655440006"
                ... )
            """
            return await self.backend_client.get_prediction(gateway_id, prediction_id)
        
        @self.tool(description="Get AI-generated explanation for a prediction")
        async def get_prediction_explanation(
            gateway_id: str,
            prediction_id: str
        ) -> Dict[str, Any]:
            """Get prediction explanation.
            
            Retrieves AI-generated natural language explanation for why a
            prediction was made and what it means.
            
            Args:
                gateway_id: Gateway UUID (required)
                prediction_id: Prediction UUID
            
            Returns:
                dict: AI-generated explanation with insights
            
            Example:
                >>> explanation = await get_prediction_explanation(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     prediction_id="bb0e8400-e29b-41d4-a716-446655440006"
                ... )
                >>> print(explanation['explanation'])
            """
            return await self.backend_client.get_prediction_explanation(gateway_id, prediction_id)
        
        @self.tool(description="Get prediction accuracy statistics for a gateway")
        async def get_prediction_accuracy_stats(
            gateway_id: str,
            api_id: Optional[str] = None,
            days: int = 30
        ) -> Dict[str, Any]:
            """Get prediction accuracy statistics.
            
            Provides accuracy metrics for predictions including true positives,
            false positives, and overall accuracy rate.
            
            Args:
                gateway_id: Gateway UUID (required)
                api_id: Optional API filter
                days: Number of days to analyze (1-90, default: 30)
            
            Returns:
                dict: Accuracy statistics and trends
            
            Example:
                >>> stats = await get_prediction_accuracy_stats(
                ...     gateway_id="550e8400-e29b-41d4-a716-446655440000",
                ...     days=60
                ... )
                >>> print(f"Accuracy: {stats['overall_accuracy']}%")
            """
            return await self.backend_client.get_prediction_accuracy_stats(
                gateway_id=gateway_id,
                api_id=api_id,
                days=days
            )
        
        @self.tool(description="Get global predictions summary across all gateways")
        async def get_global_predictions_summary(
            gateway_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """Get global predictions summary.
            
            Provides prediction summary across all gateways or for a specific
            gateway when gateway_id is provided.
            
            Args:
                gateway_id: Optional gateway filter
            
            Returns:
                dict: Global predictions summary
            
            Example:
                >>> summary = await get_global_predictions_summary()
            """
            params = {"gateway_id": gateway_id} if gateway_id else {}
            return await self.backend_client._request("GET", "/predictions", params=params)
        
        @self.tool(description="Search failure predictions using flexible multi-criteria filtering")
        async def search_predictions(
            prediction_type: Optional[str] = None,
            confidence_min: Optional[float] = None,
            confidence_max: Optional[float] = None,
            severity: Optional[str] = None,
            status: Optional[str] = None,
            predicted_after: Optional[str] = None,
            predicted_before: Optional[str] = None,
            api_name: Optional[str] = None,
            gateway_id: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
        ) -> Dict[str, Any]:
            """Search failure predictions using flexible multi-criteria filtering.
            
            Use this tool when the user's query requires combining multiple filters
            that go beyond simple list operations.
            
            IMPORTANT: Prefer this tool over list_predictions when the query includes:
            - Text pattern matching (API name contains)
            - Multiple filter combinations (type AND severity AND status)
            - Date range filtering (predicted between dates)
            - Numeric range filtering (confidence thresholds)
            - Time range filtering patterns
            
            Args:
                prediction_type: Type filter (failure, performance_degradation, capacity_issue)
                confidence_min: Minimum confidence score (0.0-1.0)
                confidence_max: Maximum confidence score (0.0-1.0)
                severity: Severity filter (critical, high, medium, low)
                status: Status filter (active, resolved, false_positive, expired)
                predicted_after: Predicted after date (ISO 8601 format)
                predicted_before: Predicted before date (ISO 8601 format)
                api_name: API name pattern (case-insensitive partial match)
                gateway_id: Optional gateway filter
                page: Page number (1-based, default: 1)
                page_size: Items per page (1-100, default: 20)
            
            Returns:
                dict: Search results with:
                    - items: List of prediction objects
                    - total: Total matching count
                    - page: Current page number
                    - page_size: Items per page
            
            Example:
                >>> result = await search_predictions(
                ...     confidence_min=0.8,
                ...     severity="critical",
                ...     status="active"
                ... )
                >>> print(f"Found {result['total']} high-confidence predictions")
            """
            params: Dict[str, Any] = {"page": page, "page_size": page_size}
            if prediction_type:
                params["prediction_type"] = prediction_type
            if confidence_min is not None:
                params["confidence_min"] = confidence_min
            if confidence_max is not None:
                params["confidence_max"] = confidence_max
            if severity:
                params["severity"] = severity
            if status:
                params["status"] = status
            if predicted_after:
                params["predicted_after"] = predicted_after
            if predicted_before:
                params["predicted_before"] = predicted_before
            if api_name:
                params["api_name"] = api_name
            if gateway_id:
                params["gateway_id"] = gateway_id
            return await self.backend_client._request("GET", "/predictions/search", params=params)

    async def cleanup(self) -> None:
        """Cleanup server resources."""
        await self.backend_client.close()
        await super().cleanup()


def main() -> None:
    """Run the Unified MCP server."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    server = UnifiedMCPServer()
    server.run(transport="streamable-http", port=8000, host="0.0.0.0")


if __name__ == "__main__":
    main()

# Made with Bob
