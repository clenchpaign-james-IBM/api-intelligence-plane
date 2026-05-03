"""
Gateway API Endpoints

REST API endpoints for managing API Gateways.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.adapters.factory import GatewayAdapterFactory
from app.db.repositories.gateway_repository import GatewayRepository
from app.models.gateway import Gateway, GatewayStatus, GatewayVendor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gateways", tags=["Gateways"])


# Status Transition Validator
class GatewayStatusValidator:
    """Validates gateway status transitions."""
    
    # Valid status transitions matrix
    VALID_TRANSITIONS = {
        GatewayStatus.DISCONNECTED: [GatewayStatus.CONNECTED, GatewayStatus.ERROR],
        GatewayStatus.CONNECTED: [GatewayStatus.DISCONNECTED, GatewayStatus.ERROR],
        GatewayStatus.ERROR: [GatewayStatus.CONNECTED, GatewayStatus.DISCONNECTED],
    }
    
    @classmethod
    def is_valid_transition(cls, from_status: GatewayStatus, to_status: GatewayStatus) -> bool:
        """
        Check if a status transition is valid.
        
        Args:
            from_status: Current gateway status
            to_status: Desired gateway status
            
        Returns:
            True if transition is valid, False otherwise
        """
        # Same status is always valid (no-op)
        if from_status == to_status:
            return True
        
        # Check if transition is in valid transitions matrix
        valid_targets = cls.VALID_TRANSITIONS.get(from_status, [])
        return to_status in valid_targets
    
    @classmethod
    def get_valid_transitions(cls, from_status: GatewayStatus) -> List[GatewayStatus]:
        """
        Get list of valid target statuses for a given current status.
        
        Args:
            from_status: Current gateway status
            
        Returns:
            List of valid target statuses
        """
        return cls.VALID_TRANSITIONS.get(from_status, [])
    
    @classmethod
    def validate_transition(cls, from_status: GatewayStatus, to_status: GatewayStatus) -> None:
        """
        Validate a status transition and raise exception if invalid.
        
        Args:
            from_status: Current gateway status
            to_status: Desired gateway status
            
        Raises:
            HTTPException: If transition is invalid
        """
        if not cls.is_valid_transition(from_status, to_status):
            valid_targets = cls.get_valid_transitions(from_status)
            valid_targets_str = ", ".join([s.value for s in valid_targets])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status transition from {from_status.value} to {to_status.value}. "
                    f"Valid transitions from {from_status.value}: {valid_targets_str}"
                ),
            )


# Request/Response Models
class CreateGatewayRequest(BaseModel):
    """Request model for creating a new Gateway."""
    
    name: str = Field(..., description="Gateway name")
    vendor: GatewayVendor = Field(..., description="Gateway vendor")
    version: Optional[str] = Field(None, description="Gateway version")
    base_url: str = Field(..., description="Gateway base URL for APIs, Policies, PolicyActions")
    transactional_logs_url: Optional[str] = Field(None, description="Separate endpoint for transactional logs (optional)")
    connection_type: str = Field(default="rest_api", description="Connection method")
    
    # Base URL credentials (optional)
    base_url_credential_type: str = Field(default="none", description="Credential type for base_url")
    base_url_username: Optional[str] = Field(None, description="Username for base_url authentication")
    base_url_password: Optional[str] = Field(None, description="Password for base_url authentication")
    base_url_api_key: Optional[str] = Field(None, description="API key for base_url authentication")
    base_url_token: Optional[str] = Field(None, description="Bearer token for base_url authentication")
    
    # Transactional logs credentials (optional, separate from base_url)
    transactional_logs_credential_type: Optional[str] = Field(None, description="Credential type for transactional_logs_url")
    transactional_logs_username: Optional[str] = Field(None, description="Username for transactional logs authentication")
    transactional_logs_password: Optional[str] = Field(None, description="Password for transactional logs authentication")
    transactional_logs_api_key: Optional[str] = Field(None, description="API key for transactional logs authentication")
    transactional_logs_token: Optional[str] = Field(None, description="Bearer token for transactional logs authentication")
    
    capabilities: list[str] = Field(default_factory=list, description="Gateway capabilities")
    configuration: Optional[dict] = Field(None, description="Vendor-specific configuration")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class UpdateGatewayRequest(BaseModel):
    """Request model for updating a Gateway."""
    
    name: Optional[str] = Field(None, description="Gateway name")
    version: Optional[str] = Field(None, description="Gateway version")
    base_url: Optional[str] = Field(None, description="Gateway base URL")
    transactional_logs_url: Optional[str] = Field(None, description="Transactional logs endpoint URL")
    connection_type: Optional[str] = Field(None, description="Connection method")
    
    # Base URL credentials
    base_url_credential_type: Optional[str] = Field(None, description="Credential type for base_url")
    base_url_username: Optional[str] = Field(None, description="Username for base_url")
    base_url_password: Optional[str] = Field(None, description="Password for base_url")
    base_url_api_key: Optional[str] = Field(None, description="API key for base_url")
    base_url_token: Optional[str] = Field(None, description="Bearer token for base_url")
    
    # Transactional logs credentials
    transactional_logs_credential_type: Optional[str] = Field(None, description="Credential type for transactional logs")
    transactional_logs_username: Optional[str] = Field(None, description="Username for transactional logs")
    transactional_logs_password: Optional[str] = Field(None, description="Password for transactional logs")
    transactional_logs_api_key: Optional[str] = Field(None, description="API key for transactional logs")
    transactional_logs_token: Optional[str] = Field(None, description="Bearer token for transactional logs")
    
    capabilities: Optional[list[str]] = Field(None, description="Gateway capabilities")
    status: Optional[GatewayStatus] = Field(None, description="Gateway status")
    configuration: Optional[dict] = Field(None, description="Vendor-specific configuration")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class GatewayListResponse(BaseModel):
    """Response model for listing Gateways."""
    
    items: list[Gateway]
    total: int
    page: int
    page_size: int


@router.post(
    "",
    response_model=Gateway,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new API Gateway",
)
async def create_gateway(request: CreateGatewayRequest) -> Gateway:
    """
    Register a new API Gateway.
    
    Args:
        request: Gateway creation request
        
    Returns:
        Created Gateway
        
    Raises:
        HTTPException: If gateway creation fails
    """
    try:
        repo = GatewayRepository()
        
        # Import required types
        from app.models.gateway import GatewayCredentials, ConnectionType
        from app.adapters.factory import GatewayAdapterFactory
        from pydantic import HttpUrl
        from datetime import datetime
        
        # Build base URL credentials (optional)
        base_url_credentials = None
        if request.base_url_credential_type and request.base_url_credential_type != "none":
            base_url_credentials = GatewayCredentials(
                type=request.base_url_credential_type,
                username=request.base_url_username,
                password=request.base_url_password,
                api_key=request.base_url_api_key,
                token=request.base_url_token,
            )
        
        # Build transactional logs credentials (optional, separate from base_url)
        transactional_logs_credentials = None
        if request.transactional_logs_credential_type:
            transactional_logs_credentials = GatewayCredentials(
                type=request.transactional_logs_credential_type,
                username=request.transactional_logs_username,
                password=request.transactional_logs_password,
                api_key=request.transactional_logs_api_key,
                token=request.transactional_logs_token,
            )
        
        # Create Gateway model with initial DISCONNECTED status
        gateway = Gateway(
            name=request.name,
            vendor=request.vendor,
            version=request.version,
            base_url=HttpUrl(request.base_url),
            transactional_logs_url=HttpUrl(request.transactional_logs_url) if request.transactional_logs_url else None,
            connection_type=ConnectionType(request.connection_type),
            base_url_credentials=base_url_credentials,
            transactional_logs_credentials=transactional_logs_credentials,
            capabilities=request.capabilities if request.capabilities else ["discovery"],
            status=GatewayStatus.DISCONNECTED,
            last_connected_at=None,
            last_error=None,
            api_count=0,
            configuration=request.configuration,
            metadata=request.metadata,
        )
        
        # Gateway starts as DISCONNECTED - use connect endpoint to establish connection
        # This follows Option B from the lifecycle analysis document
        logger.info(f"Registering gateway {gateway.name} with status DISCONNECTED")
        
        # Save to database with model UUID as document ID so future get/update/delete
        # operations using gateway.id resolve the same OpenSearch document.
        created_gateway = repo.create(gateway, doc_id=str(gateway.id))
        
        logger.info(f"Created gateway: {created_gateway.id} ({created_gateway.name}) with status {created_gateway.status}")
        return created_gateway
        
    except Exception as e:
        logger.error(f"Failed to create gateway: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create gateway: {str(e)}",
        )


@router.get(
    "",
    response_model=GatewayListResponse,
    summary="List all connected API Gateways",
)
async def list_gateways(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: Optional[GatewayStatus] = Query(None, alias="status", description="Filter by status"),
) -> GatewayListResponse:
    """
    List all registered API Gateways with optional filtering.
    
    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        status_filter: Optional status filter
        
    Returns:
        Paginated list of Gateways
    """
    try:
        repo = GatewayRepository()
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        if status_filter:
            # Filter by status
            gateways, total = repo.find_by_status(
                status=status_filter,
                size=page_size,
                from_=offset,
            )
        else:
            # Get all gateways
            gateways, total = repo.list_all(size=page_size, from_=offset)
        
        return GatewayListResponse(
            items=gateways,
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error(f"Failed to list gateways: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list gateways: {str(e)}",
        )

@router.get(
    "/search",
    response_model=GatewayListResponse,
    summary="Search gateways with multiple filters",
)
async def search_gateways(
    name: Optional[str] = Query(None, description="Gateway name pattern (case-insensitive wildcard)"),
    vendor: Optional[GatewayVendor] = Query(None, description="Gateway vendor filter"),
    gateway_status: Optional[GatewayStatus] = Query(None, alias="status", description="Gateway status filter"),
    created_after: Optional[datetime] = Query(None, description="Filter gateways created after this date (ISO 8601)"),
    created_before: Optional[datetime] = Query(None, description="Filter gateways created before this date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> GatewayListResponse:
    """
    Search gateways with multiple filter criteria.
    
    This endpoint provides flexible multi-criteria filtering for agents,
    complementing the list endpoint with text pattern matching and date ranges.
    
    Args:
        name: Gateway name pattern (case-insensitive wildcard match)
        vendor: Gateway vendor filter
        status: Gateway status filter
        created_after: Filter gateways created after this date
        created_before: Filter gateways created before this date
        page: Page number (1-based)
        page_size: Number of items per page
        
    Returns:
        Paginated list of matching gateways
        
    Examples:
        - Find gateways with "prod" in name that are connected:
          GET /api/v1/gateways/search?name=prod&status=connected
        
        - Find webMethods gateways created in last 7 days:
          GET /api/v1/gateways/search?vendor=webmethods&created_after=2026-04-25T00:00:00Z
    """
    try:
        repo = GatewayRepository()
        
        # Call repository search method
        gateways, total = repo.search_gateways(
            name=name,
            vendor=vendor,
            status=gateway_status,
            created_after=created_after,
            created_before=created_before,
            page=page,
            page_size=page_size,
        )
        
        return GatewayListResponse(
            items=gateways,
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error(f"Failed to search gateways: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search gateways: {str(e)}",
        )



@router.get(
    "/{gateway_id}",
    response_model=Gateway,
    summary="Get gateway details",
)
async def get_gateway(gateway_id: UUID) -> Gateway:
    """
    Get details of a specific Gateway.
    
    Args:
        gateway_id: Gateway UUID
        
    Returns:
        Gateway details
        
    Raises:
        HTTPException: If gateway not found
    """
    try:
        repo = GatewayRepository()
        gateway = repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        return gateway
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get gateway {gateway_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get gateway: {str(e)}",
        )


@router.put(
    "/{gateway_id}",
    response_model=Gateway,
    summary="Update gateway configuration",
)
async def update_gateway(
    gateway_id: UUID,
    request: UpdateGatewayRequest,
) -> Gateway:
    """
    Update Gateway configuration.
    
    Args:
        gateway_id: Gateway UUID
        request: Gateway update request
        
    Returns:
        Updated Gateway
        
    Raises:
        HTTPException: If gateway not found or update fails
    """
    try:
        repo = GatewayRepository()
        
        # Check if gateway exists
        existing_gateway = repo.get(str(gateway_id))
        if not existing_gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Build updates dictionary (only include provided fields)
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.version is not None:
            updates["version"] = request.version
        if request.base_url is not None:
            updates["base_url"] = request.base_url
        if request.transactional_logs_url is not None:
            updates["transactional_logs_url"] = request.transactional_logs_url
        if request.connection_type is not None:
            updates["connection_type"] = request.connection_type
        
        # Update base URL credentials if any field is provided
        if any([request.base_url_credential_type, request.base_url_api_key, request.base_url_username, request.base_url_password, request.base_url_token]):
            from app.models.gateway import GatewayCredentials
            
            # Get existing credentials or create new
            existing_creds = existing_gateway.base_url_credentials
            base_url_credentials = GatewayCredentials(
                type=request.base_url_credential_type if request.base_url_credential_type is not None else (existing_creds.type if existing_creds else "none"),
                username=request.base_url_username if request.base_url_username is not None else (existing_creds.username if existing_creds else None),
                password=request.base_url_password if request.base_url_password is not None else (existing_creds.password if existing_creds else None),
                api_key=request.base_url_api_key if request.base_url_api_key is not None else (existing_creds.api_key if existing_creds else None),
                token=request.base_url_token if request.base_url_token is not None else (existing_creds.token if existing_creds else None),
            )
            updates["base_url_credentials"] = base_url_credentials.model_dump()
        
        # Update transactional logs credentials if any field is provided
        if any([request.transactional_logs_credential_type, request.transactional_logs_api_key, request.transactional_logs_username, request.transactional_logs_password, request.transactional_logs_token]):
            from app.models.gateway import GatewayCredentials
            
            # Get existing credentials or create new
            existing_creds = existing_gateway.transactional_logs_credentials
            transactional_logs_credentials = GatewayCredentials(
                type=request.transactional_logs_credential_type if request.transactional_logs_credential_type is not None else (existing_creds.type if existing_creds else "none"),
                username=request.transactional_logs_username if request.transactional_logs_username is not None else (existing_creds.username if existing_creds else None),
                password=request.transactional_logs_password if request.transactional_logs_password is not None else (existing_creds.password if existing_creds else None),
                api_key=request.transactional_logs_api_key if request.transactional_logs_api_key is not None else (existing_creds.api_key if existing_creds else None),
                token=request.transactional_logs_token if request.transactional_logs_token is not None else (existing_creds.token if existing_creds else None),
            )
            updates["transactional_logs_credentials"] = transactional_logs_credentials.model_dump()
        
        if request.capabilities is not None:
            updates["capabilities"] = request.capabilities
        
        # Validate status transition if status is being updated
        if request.status is not None:
            GatewayStatusValidator.validate_transition(existing_gateway.status, request.status)
            updates["status"] = request.status.value
        
        if request.configuration is not None:
            updates["configuration"] = request.configuration
        if request.metadata is not None:
            updates["metadata"] = request.metadata
        
        # Update gateway
        updated_gateway = repo.update(str(gateway_id), updates)
        
        if not updated_gateway:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update gateway",
            )
        
        logger.info(f"Updated gateway: {gateway_id}")
        return updated_gateway
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update gateway {gateway_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update gateway: {str(e)}",
        )


@router.post(
    "/{gateway_id}/connect",
    response_model=Gateway,
    summary="Connect to gateway",
)
async def connect_gateway(gateway_id: UUID) -> Gateway:
    """
    Establish connection to a gateway.
    
    Validates gateway credentials and updates status to CONNECTED on success.
    
    Args:
        gateway_id: Gateway UUID
        
    Returns:
        Updated Gateway with CONNECTED status
        
    Raises:
        HTTPException: If gateway not found, already connected, or connection fails
    """
    try:
        repo = GatewayRepository()
        
        # Get gateway
        gateway = repo.get(str(gateway_id))
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Check if already connected
        if gateway.status == GatewayStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gateway {gateway_id} is already connected",
            )
        
        # Test connection
        try:
            adapter_factory = GatewayAdapterFactory()
            adapter = adapter_factory.create_adapter(gateway)
            await adapter.connect()
            test_result = await adapter.test_connection()
            await adapter.disconnect()
            
            if test_result.get("connected"):
                # Update status to CONNECTED
                updates = {
                    "status": GatewayStatus.CONNECTED.value,
                    "last_connected_at": datetime.utcnow().isoformat(),
                    "last_error": None,
                }
                updated_gateway = repo.update(str(gateway_id), updates)
                
                logger.info(f"Gateway {gateway.name} ({gateway_id}) connected successfully")
                if not updated_gateway:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update gateway status",
                    )
                return updated_gateway
            else:
                # Connection test failed
                error_msg = test_result.get("error", "Connection test failed")
                updates = {
                    "status": GatewayStatus.ERROR.value,
                    "last_error": error_msg,
                }
                repo.update(str(gateway_id), updates)
                
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to connect to gateway: {error_msg}",
                )
        except Exception as e:
            # Connection attempt failed
            error_msg = str(e)
            updates = {
                "status": GatewayStatus.ERROR.value,
                "last_error": error_msg,
            }
            repo.update(str(gateway_id), updates)
            
            logger.error(f"Failed to connect to gateway {gateway_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to connect to gateway: {error_msg}",
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect gateway {gateway_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect gateway: {str(e)}",
        )


@router.post(
    "/{gateway_id}/disconnect",
    response_model=Gateway,
    summary="Disconnect from gateway",
)
async def disconnect_gateway(gateway_id: UUID) -> Gateway:
    """
    Disconnect from a gateway.
    
    Updates gateway status to DISCONNECTED. Gateway remains registered but inactive.
    
    Args:
        gateway_id: Gateway UUID
        
    Returns:
        Updated Gateway with DISCONNECTED status
        
    Raises:
        HTTPException: If gateway not found or not connected
    """
    try:
        repo = GatewayRepository()
        
        # Get gateway
        gateway = repo.get(str(gateway_id))
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Check if connected
        if gateway.status != GatewayStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gateway {gateway_id} is not connected (current status: {gateway.status})",
            )
        
        # Update status to DISCONNECTED
        updates = {
            "status": GatewayStatus.DISCONNECTED.value,
            "last_error": None,
        }
        updated_gateway = repo.update(str(gateway_id), updates)
        
        logger.info(f"Gateway {gateway.name} ({gateway_id}) disconnected")
        if not updated_gateway:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update gateway status",
            )
        return updated_gateway
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect gateway {gateway_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect gateway: {str(e)}",
        )


@router.delete(
    "/{gateway_id}",
    summary="Remove gateway",
)
async def delete_gateway(gateway_id: UUID) -> dict:
    """
    Remove a Gateway from the system.
    
    Args:
        gateway_id: Gateway UUID
        
    Returns:
        Success message with deleted gateway details
        
    Raises:
        HTTPException: If gateway not found or deletion fails
    """
    repo = GatewayRepository()
    
    # Check if gateway exists (using gateway.id as document ID)
    gateway_id_str = str(gateway_id)
    logger.info(f"Deleting gateway with ID: {gateway_id_str}")
    existing_gateway = repo.get(gateway_id_str)
    if not existing_gateway:
        logger.error(f"Gateway {gateway_id_str} not found in OpenSearch index '{repo.index_name}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gateway {gateway_id} not found",
        )
    
    try:
        # Delete gateway (document ID = gateway.id)
        success = repo.delete(gateway_id_str)
        
        if not success:
            logger.error(f"Failed to delete gateway {gateway_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete gateway",
            )
        
        logger.info(f"Deleted gateway: {gateway_id} ({existing_gateway.name})")
        
        return {
            "success": True,
            "message": f"Gateway '{existing_gateway.name}' deleted successfully",
            "gateway_id": str(gateway_id),
            "gateway_name": existing_gateway.name,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete gateway {gateway_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete gateway: {str(e)}",
        )


@router.post(
    "/{gateway_id}/sync",
    summary="Sync APIs from gateway",
)
async def sync_gateway(
    gateway_id: UUID,
    force_refresh: bool = Query(False, description="Force refresh even if recently synced"),
) -> dict:
    """
    Trigger API discovery/sync from a Gateway.
    
    Args:
        gateway_id: Gateway UUID
        force_refresh: Force refresh even if recently synced
        
    Returns:
        Sync result with number of APIs discovered
        
    Raises:
        HTTPException: If gateway not found or sync fails
    """
    from app.services.discovery_service import DiscoveryService
    from app.db.repositories.api_repository import APIRepository
    from app.adapters.factory import GatewayAdapterFactory
    
    # Initialize services
    api_repo = APIRepository()
    gateway_repo = GatewayRepository()
    adapter_factory = GatewayAdapterFactory()
    discovery_service = DiscoveryService(api_repo, gateway_repo, adapter_factory)
    
    # Check if gateway exists
    gateway = gateway_repo.get(str(gateway_id))
    if not gateway:
        logger.error(f"Gateway {gateway_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gateway {gateway_id} not found",
        )
    
    try:
        # Perform discovery
        logger.info(f"Starting sync for gateway {gateway_id} (force_refresh={force_refresh})")
        result = await discovery_service.discover_gateway_apis(
            gateway_id=gateway_id,
            force_refresh=force_refresh,
        )
        
        logger.info(f"Sync completed for gateway {gateway_id}: {result['apis_discovered']} APIs discovered")
        
        return {
            "success": True,
            "message": "Gateway sync completed successfully",
            "apis_discovered": result["apis_discovered"],
            "new_apis": result["new_apis"],
            "updated_apis": result["updated_apis"],
            "shadow_apis_found": result["shadow_apis_found"],
            "gateway_id": str(gateway_id),
            "gateway_name": result["gateway_name"],
            "timestamp": result["timestamp"],
        }
        
    except ValueError as e:
        logger.error(f"Invalid gateway configuration {gateway_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.error(f"Sync failed for gateway {gateway_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error syncing gateway {gateway_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync gateway: {str(e)}",
        )


@router.post(
    "/test-connection",
    summary="Test gateway connection without saving",
)
async def test_gateway_connection(request: CreateGatewayRequest) -> dict:
    """
    Test gateway connection without saving to database.
    
    This endpoint allows users to validate their gateway configuration
    before saving it. It creates a temporary adapter and tests connectivity.
    
    Args:
        request: Gateway configuration to test
        
    Returns:
        Connection test result with status and details
        
    Raises:
        HTTPException: If test fails with error details
    """
    try:
        from app.adapters.factory import GatewayAdapterFactory
        from app.models.gateway import GatewayCredentials, ConnectionType
        from pydantic import HttpUrl
        import time
        
        # Build temporary gateway configuration
        base_url_credentials = None
        if request.base_url_credential_type and request.base_url_credential_type != "none":
            base_url_credentials = GatewayCredentials(
                type=request.base_url_credential_type,
                username=request.base_url_username,
                password=request.base_url_password,
                api_key=request.base_url_api_key,
                token=request.base_url_token,
            )
        
        transactional_logs_credentials = None
        if request.transactional_logs_credential_type:
            transactional_logs_credentials = GatewayCredentials(
                type=request.transactional_logs_credential_type,
                username=request.transactional_logs_username,
                password=request.transactional_logs_password,
                api_key=request.transactional_logs_api_key,
                token=request.transactional_logs_token,
            )
        
        # Create temporary gateway object (not saved to DB)
        temp_gateway = Gateway(
            name=request.name,
            vendor=request.vendor,
            version=request.version,
            base_url=HttpUrl(request.base_url),
            transactional_logs_url=HttpUrl(request.transactional_logs_url) if request.transactional_logs_url else None,
            connection_type=ConnectionType(request.connection_type),
            base_url_credentials=base_url_credentials,
            transactional_logs_credentials=transactional_logs_credentials,
            capabilities=request.capabilities if request.capabilities else ["discovery"],
            status=GatewayStatus.DISCONNECTED,
            last_connected_at=None,
            last_error=None,
            configuration=request.configuration,
            metadata=request.metadata,
        )
        
        # Create adapter and test connection
        adapter_factory = GatewayAdapterFactory()
        adapter = adapter_factory.create_adapter(temp_gateway)
        
        # Measure connection time
        start_time = time.time()
        
        # First connect to the gateway
        try:
            await adapter.connect()
            # Then test the connection
            test_result = await adapter.test_connection()
            latency_ms = (time.time() - start_time) * 1000
            
            # Enhance result with latency and message
            test_result["latency_ms"] = round(latency_ms, 2)
            test_result["gateway_name"] = request.name
            test_result["gateway_vendor"] = request.vendor
            
            # Add user-friendly message
            if test_result.get("connected"):
                test_result["message"] = f"Successfully connected to {request.vendor} gateway"
            else:
                test_result["message"] = test_result.get("error", "Connection failed")
            
            logger.info(f"Connection test for {request.name}: {'SUCCESS' if test_result.get('connected') else 'FAILED'}")
            
            return test_result
        finally:
            # Always disconnect after testing
            await adapter.disconnect()
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}", exc_info=True)
        return {
            "connected": False,
            "error": str(e),
            "message": f"Failed to connect: {str(e)}",
            "gateway_name": request.name,
            "gateway_vendor": request.vendor,
            "latency_ms": 0,
        }


@router.post(
    "/bulk-sync",
    summary="Sync multiple gateways in parallel",
)
async def bulk_sync_gateways(
    request: dict,
    force_refresh: bool = Query(False, description="Force refresh even if recently synced"),
) -> dict:
    """
    Trigger API discovery/sync for multiple gateways in parallel.
    
    This endpoint allows efficient bulk synchronization of multiple gateways.
    Each gateway is synced independently, and results are aggregated.
    
    Args:
        gateway_ids: List of gateway UUIDs to sync
        force_refresh: Force refresh even if recently synced
        
    Returns:
        Bulk sync results with per-gateway status and aggregated statistics
        
    Raises:
        HTTPException: If bulk sync fails
    """
    try:
        from app.services.discovery_service import DiscoveryService
        from app.db.repositories.api_repository import APIRepository
        from app.adapters.factory import GatewayAdapterFactory
        import asyncio
        import time
        
        # Extract gateway_ids from request body
        gateway_ids = request.get('gatewayIds', [])
        if not gateway_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No gateway IDs provided",
            )
        
        # Convert string IDs to UUIDs
        try:
            gateway_ids = [UUID(gw_id) for gw_id in gateway_ids]
        except (ValueError, AttributeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid gateway ID format: {str(e)}",
            )
        
        if len(gateway_ids) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 50 gateways can be synced at once",
            )
        
        # Initialize services
        api_repo = APIRepository()
        gateway_repo = GatewayRepository()
        adapter_factory = GatewayAdapterFactory()
        discovery_service = DiscoveryService(api_repo, gateway_repo, adapter_factory)
        
        # Verify all gateways exist
        gateways = []
        for gateway_id in gateway_ids:
            gateway = gateway_repo.get(str(gateway_id))
            if not gateway:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Gateway {gateway_id} not found",
                )
            gateways.append(gateway)
        
        logger.info(f"Starting bulk sync for {len(gateway_ids)} gateways (force_refresh={force_refresh})")
        
        start_time = time.time()
        
        # Sync all gateways in parallel
        async def sync_single_gateway(gw_id: UUID, gw: Gateway) -> dict:
            try:
                result = await discovery_service.discover_gateway_apis(
                    gateway_id=gw_id,
                    force_refresh=force_refresh,
                )
                return {
                    "gateway_id": str(gw_id),
                    "gateway_name": gw.name,
                    "success": True,
                    "apis_discovered": result["apis_discovered"],
                    "new_apis": result["new_apis"],
                    "updated_apis": result["updated_apis"],
                    "shadow_apis_found": result["shadow_apis_found"],
                    "error": None,
                }
            except Exception as e:
                logger.error(f"Failed to sync gateway {gw_id}: {e}")
                return {
                    "gateway_id": str(gw_id),
                    "gateway_name": gw.name,
                    "success": False,
                    "apis_discovered": 0,
                    "new_apis": 0,
                    "updated_apis": 0,
                    "shadow_apis_found": 0,
                    "error": str(e),
                }
        
        # Execute all syncs in parallel
        results = await asyncio.gather(
            *[sync_single_gateway(gw_id, gw) for gw_id, gw in zip(gateway_ids, gateways)],
            return_exceptions=False
        )
        
        duration_seconds = time.time() - start_time
        
        # Aggregate statistics
        total_apis_discovered = sum(r["apis_discovered"] for r in results)
        total_new_apis = sum(r["new_apis"] for r in results)
        total_updated_apis = sum(r["updated_apis"] for r in results)
        total_shadow_apis = sum(r["shadow_apis_found"] for r in results)
        successful_syncs = sum(1 for r in results if r["success"])
        failed_syncs = len(results) - successful_syncs
        
        logger.info(
            f"Bulk sync complete: {successful_syncs}/{len(gateway_ids)} successful, "
            f"{total_apis_discovered} APIs discovered"
        )
        
        return {
            "message": "Bulk sync completed",
            "total": len(gateway_ids),
            "successful": successful_syncs,
            "failed": failed_syncs,
            "total_apis_discovered": total_apis_discovered,
            "total_new_apis": total_new_apis,
            "total_updated_apis": total_updated_apis,
            "total_shadow_apis_found": total_shadow_apis,
            "duration_seconds": duration_seconds,
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk sync failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk sync failed: {str(e)}",
        )


# Made with Bob