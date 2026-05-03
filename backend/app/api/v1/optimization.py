"""
Optimization API Endpoints

REST API endpoints for performance optimization recommendations.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status as http_status
from pydantic import BaseModel

from app.db.repositories.recommendation_repository import RecommendationRepository
from app.db.repositories.metrics_repository import MetricsRepository
from app.db.repositories.api_repository import APIRepository
from app.services.optimization_service import OptimizationService
from app.models.recommendation import (
    RecommendationType,
    RecommendationPriority,
    RecommendationStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Optimization"])


# Response Models
class EstimatedImpactResponse(BaseModel):
    """Response model for estimated impact."""

    metric: str
    current_value: float
    expected_value: float
    improvement_percentage: float
    confidence: float


class AIContextResponse(BaseModel):
    """Response model for AI-generated insights."""
    
    performance_analysis: Optional[str] = None
    implementation_guidance: Optional[str] = None
    prioritization: Optional[str] = None
    generated_at: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Response model for a single recommendation."""

    id: str
    gateway_id: str
    api_id: str
    api_name: Optional[str] = None
    recommendation_type: str
    title: str
    description: str
    priority: str
    estimated_impact: EstimatedImpactResponse
    implementation_effort: str
    implementation_steps: list[str]
    status: str
    implemented_at: Optional[str] = None
    cost_savings: Optional[float] = None
    ai_context: Optional[AIContextResponse] = None
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None


class RecommendationListResponse(BaseModel):
    """Response model for recommendation list."""

    recommendations: list[RecommendationResponse]
    total: int
    page: int
    page_size: int


class RecommendationStatsResponse(BaseModel):
    """Response model for recommendation statistics."""

    total_recommendations: int
    by_status: list[dict]
    by_priority: list[dict]
    by_type: list[dict]
    avg_improvement: float
    total_cost_savings: float


class OptimizationSummaryResponse(BaseModel):
    """Response model for optimization summary."""
    
    total_recommendations: int
    high_priority_recommendations: int
    medium_priority_recommendations: int
    low_priority_recommendations: int


@router.get(
    "/optimization/summary",
    response_model=OptimizationSummaryResponse,
    summary="Get optimization summary across all gateways",
)
async def get_optimization_summary(
    gateway_id: Optional[UUID] = Query(None, description="Optional gateway filter"),
) -> OptimizationSummaryResponse:
    """
    Get aggregated optimization summary across all gateways or for a specific gateway.
    
    Returns recommendation counts by priority.
    """
    try:
        # Initialize service
        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=RecommendationRepository(),
            metrics_repository=MetricsRepository(),
            api_repository=APIRepository(),
            llm_service=llm_service,
        )

        # If gateway_id is provided, get gateway-specific recommendations
        if gateway_id:
            # Verify gateway exists
            from app.db.repositories.gateway_repository import GatewayRepository
            gateway_repo = GatewayRepository()
            gateway = gateway_repo.get(str(gateway_id))
            
            if not gateway:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Gateway {gateway_id} not found",
                )
            
            # Get all APIs for this gateway
            api_repo = APIRepository()
            gateway_apis, _ = api_repo.find_by_gateway(gateway_id=gateway_id, size=10000)
            gateway_api_ids = {str(api.id) for api in gateway_apis}
            
            # Get recommendations for each API in the gateway
            all_recommendations = []
            for api in gateway_apis:
                result = optimization_service.list_recommendations(
                    api_id=str(api.id),
                    page=1,
                    page_size=10000,
                )
                all_recommendations.extend(result["recommendations"])
            
            # Count by priority
            high = sum(1 for r in all_recommendations if r.priority == RecommendationPriority.HIGH)
            medium = sum(1 for r in all_recommendations if r.priority == RecommendationPriority.MEDIUM)
            low = sum(1 for r in all_recommendations if r.priority == RecommendationPriority.LOW)
            
            return OptimizationSummaryResponse(
                total_recommendations=len(all_recommendations),
                high_priority_recommendations=high,
                medium_priority_recommendations=medium,
                low_priority_recommendations=low,
            )
        
        # Get summary for all gateways
        summary = optimization_service.get_optimization_summary()
        
        return OptimizationSummaryResponse(
            total_recommendations=summary["total_recommendations"],
            high_priority_recommendations=summary["high_priority_recommendations"],
            medium_priority_recommendations=summary["medium_priority_recommendations"],
            low_priority_recommendations=summary["low_priority_recommendations"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get optimization summary: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimization summary: {str(e)}",
        )


@router.get(
    "/recommendations",
    response_model=RecommendationListResponse,
    summary="List all optimization recommendations across all gateways",
)
async def list_all_recommendations(
    gateway_id: Optional[UUID] = Query(None, description="Optional gateway filter"),
    api_id: Optional[UUID] = Query(None, description="Filter by API ID"),
    priority: Optional[RecommendationPriority] = Query(None, description="Filter by priority"),
    status: Optional[RecommendationStatus] = Query(None, description="Filter by status"),
    recommendation_type: Optional[RecommendationType] = Query(None, description="Filter by type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> RecommendationListResponse:
    """
    List all optimization recommendations across all gateways with optional filtering.
    
    This is an aggregate endpoint that returns recommendations from all gateways.
    Use gateway_id parameter to filter by specific gateway.

    Args:
        gateway_id: Optional gateway filter
        api_id: Filter by API ID
        priority: Filter by priority level
        status: Filter by recommendation status
        recommendation_type: Filter by recommendation type
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        List of recommendations with pagination info
    """
    try:
        # Initialize service
        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=RecommendationRepository(),
            metrics_repository=MetricsRepository(),
            api_repository=APIRepository(),
            llm_service=llm_service,
        )

        # Get recommendations with API name enrichment from service
        result = optimization_service.list_recommendations(
            api_id=str(api_id) if api_id else None,
            priority=priority,
            status=status,
            recommendation_type=recommendation_type,
            page=page,
            page_size=page_size,
        )
        
        # Filter by gateway if specified
        if gateway_id:
            api_repo = APIRepository()
            gateway_apis, _ = api_repo.find_by_gateway(gateway_id=gateway_id, size=10000)
            gateway_api_ids = {str(api.id) for api in gateway_apis}
            
            filtered_recommendations = [
                r for r in result["recommendations"]
                if str(r["recommendation"].api_id) in gateway_api_ids
            ]
            result["recommendations"] = filtered_recommendations
            result["total"] = len(filtered_recommendations)

        # Convert to response models
        recommendations_response = []
        for rec in result["recommendations"]:
            recommendation = rec["recommendation"]
            ai_context = None
            if recommendation.ai_context:
                ai_context = AIContextResponse(
                    performance_analysis=recommendation.ai_context.performance_analysis,
                    implementation_guidance=recommendation.ai_context.implementation_guidance,
                    prioritization=recommendation.ai_context.prioritization,
                    generated_at=recommendation.ai_context.generated_at.isoformat() if recommendation.ai_context.generated_at else None,
                )
            
            recommendations_response.append(
                RecommendationResponse(
                    id=str(recommendation.id),
                    gateway_id=str(recommendation.gateway_id),
                    api_id=str(recommendation.api_id),
                    api_name=rec["api_name"],
                    recommendation_type=recommendation.recommendation_type.value,
                    title=recommendation.title,
                    description=recommendation.description,
                    priority=recommendation.priority.value,
                    estimated_impact=EstimatedImpactResponse(**recommendation.estimated_impact.model_dump()),
                    implementation_effort=recommendation.implementation_effort,
                    implementation_steps=recommendation.implementation_steps,
                    status=recommendation.status.value,
                    implemented_at=recommendation.implemented_at.isoformat() if recommendation.implemented_at else None,
                    cost_savings=recommendation.cost_savings,
                    ai_context=ai_context,
                    created_at=recommendation.created_at.isoformat(),
                    updated_at=recommendation.updated_at.isoformat(),
                    expires_at=recommendation.expires_at.isoformat() if recommendation.expires_at else None,
                )
            )

        return RecommendationListResponse(
            recommendations=recommendations_response,
            total=result["total"],
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Failed to list recommendations: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list recommendations: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/optimization/recommendations",
    response_model=RecommendationListResponse,
    summary="List optimization recommendations for a gateway",
)
async def list_gateway_recommendations(
    gateway_id: UUID,
    api_id: Optional[UUID] = Query(None, description="Filter by API ID within gateway"),
    priority: Optional[RecommendationPriority] = Query(None, description="Filter by priority"),
    status: Optional[RecommendationStatus] = Query(None, description="Filter by status"),
    recommendation_type: Optional[RecommendationType] = Query(None, description="Filter by type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> RecommendationListResponse:
    """
    List optimization recommendations for APIs within a gateway with optional filters.

    Args:
        gateway_id: Gateway UUID (required)
        api_id: Filter by API ID within gateway
        priority: Filter by priority level
        status: Filter by recommendation status
        recommendation_type: Filter by recommendation type
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        List of recommendations with pagination info

    Raises:
        HTTPException: If gateway not found or recommendation retrieval fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # If api_id is provided, verify it belongs to the gateway
        if api_id:
            api_repo = APIRepository()
            api = api_repo.get(str(api_id))
            if not api or str(api.gateway_id) != str(gateway_id):
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"API {api_id} not found in gateway {gateway_id}",
                )
        
        # Initialize service
        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=RecommendationRepository(),
            metrics_repository=MetricsRepository(),
            api_repository=APIRepository(),
            llm_service=llm_service,
        )

        # Get recommendations with API name enrichment from service
        result = optimization_service.list_recommendations(
            api_id=str(api_id) if api_id else None,
            priority=priority,
            status=status,
            recommendation_type=recommendation_type,
            page=page,
            page_size=page_size,
        )
        
        # Filter recommendations to only include those from APIs in this gateway
        if not api_id:
            api_repo = APIRepository()
            gateway_apis, _ = api_repo.find_by_gateway(gateway_id=gateway_id, size=10000)
            gateway_api_ids = {str(api.id) for api in gateway_apis}
            
            filtered_items = [
                item for item in result["recommendations"]
                if str(item["recommendation"].api_id) in gateway_api_ids
            ]
            result["recommendations"] = filtered_items
            result["total"] = len(filtered_items)

        # Convert to response models
        recommendations = []
        for item in result["recommendations"]:
            rec = item["recommendation"]
            api_name = item["api_name"]

            ai_context = None
            if rec.ai_context:
                ai_context = AIContextResponse(
                    performance_analysis=rec.ai_context.performance_analysis,
                    implementation_guidance=rec.ai_context.implementation_guidance,
                    prioritization=rec.ai_context.prioritization,
                    generated_at=rec.ai_context.generated_at.isoformat() if rec.ai_context.generated_at else None,
                )
            
            recommendations.append(
                RecommendationResponse(
                    id=str(rec.id),
                    gateway_id=str(rec.gateway_id),
                    api_id=str(rec.api_id),
                    api_name=api_name,
                    recommendation_type=rec.recommendation_type.value,
                    title=rec.title,
                    description=rec.description,
                    priority=rec.priority.value,
                    estimated_impact=EstimatedImpactResponse(
                        metric=rec.estimated_impact.metric,
                        current_value=rec.estimated_impact.current_value,
                        expected_value=rec.estimated_impact.expected_value,
                        improvement_percentage=rec.estimated_impact.improvement_percentage,
                        confidence=rec.estimated_impact.confidence,
                    ),
                    implementation_effort=rec.implementation_effort.value,
                    implementation_steps=rec.implementation_steps,
                    status=rec.status.value,
                    implemented_at=rec.implemented_at.isoformat() if rec.implemented_at else None,
                    cost_savings=rec.cost_savings,
                    ai_context=ai_context,
                    created_at=rec.created_at.isoformat(),
                    updated_at=rec.updated_at.isoformat(),
                    expires_at=rec.expires_at.isoformat() if rec.expires_at else None,
                )
            )

        return RecommendationListResponse(
            recommendations=recommendations,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
        )

    except Exception as e:
        logger.error(f"Failed to list recommendations: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recommendations: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/optimization/recommendations/stats",
    response_model=RecommendationStatsResponse,
    summary="Get recommendation statistics for a gateway",
)
async def get_gateway_recommendation_stats(
    gateway_id: UUID,
    api_id: Optional[UUID] = Query(None, description="Filter by API ID within gateway"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
) -> RecommendationStatsResponse:
    """
    Get statistics about optimization recommendations for APIs within a gateway.

    Args:
        gateway_id: Gateway UUID (required)
        api_id: Optional API ID filter within gateway
        days: Number of days to look back

    Returns:
        Recommendation statistics

    Raises:
        HTTPException: If gateway not found or stats retrieval fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # If api_id is provided, verify it belongs to the gateway
        if api_id:
            api_repo = APIRepository()
            api = api_repo.get(str(api_id))
            if not api or str(api.gateway_id) != str(gateway_id):
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"API {api_id} not found in gateway {gateway_id}",
                )
        
        # Initialize service
        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=RecommendationRepository(),
            metrics_repository=MetricsRepository(),
            api_repository=APIRepository(),
            llm_service=llm_service,
        )

        # Get statistics from service
        stats = optimization_service.get_recommendation_stats(
            api_id=str(api_id) if api_id else None,
            days=days,
        )

        return RecommendationStatsResponse(
            total_recommendations=stats["total_recommendations"],
            by_status=stats["by_status"],
            by_priority=stats["by_priority"],
            by_type=stats["by_type"],
            avg_improvement=stats["avg_improvement"],
            total_cost_savings=stats["total_cost_savings"],
        )

    except Exception as e:
        logger.error(f"Failed to get recommendation stats: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/optimization/summary",
    summary="Get optimization summary for a gateway",
    description="Get aggregated optimization metrics for a gateway's APIs",
)
async def get_gateway_optimization_summary(gateway_id: UUID) -> dict:
    """
    Get optimization summary metrics for a gateway's APIs.

    Args:
        gateway_id: Gateway UUID (required)

    Returns:
        Dictionary with recommendation counts by priority

    Raises:
        HTTPException: If gateway not found or query fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        logger.info(f"Fetching optimization summary for gateway {gateway_id}")

        # Initialize service
        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=RecommendationRepository(),
            metrics_repository=MetricsRepository(),
            api_repository=APIRepository(),
            llm_service=llm_service,
        )

        # Get summary from service
        summary = optimization_service.get_optimization_summary()
        summary["gateway_id"] = str(gateway_id)
        return summary

    except Exception as e:
        logger.error(f"Failed to fetch optimization summary: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch optimization summary: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}",
    response_model=RecommendationResponse,
    summary="Get recommendation details",
)
async def get_gateway_recommendation(
    gateway_id: UUID,
    recommendation_id: UUID,
) -> RecommendationResponse:
    """
    Get detailed information about a specific recommendation within a gateway.

    Args:
        gateway_id: Gateway UUID (required)
        recommendation_id: Recommendation UUID

    Returns:
        Recommendation details

    Raises:
        HTTPException: If gateway or recommendation not found or retrieval fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Initialize service
        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=RecommendationRepository(),
            metrics_repository=MetricsRepository(),
            api_repository=APIRepository(),
            llm_service=llm_service,
        )

        # Get recommendation from service
        recommendation = optimization_service.get_recommendation_details(str(recommendation_id))

        if not recommendation:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {recommendation_id} not found",
            )
        
        # Verify recommendation's API belongs to the gateway
        api_repo = APIRepository()
        api = api_repo.get(str(recommendation.api_id))
        if not api or str(api.gateway_id) != str(gateway_id):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {recommendation_id} not found in gateway {gateway_id}",
            )

        # Convert to response model
        return RecommendationResponse(
            id=str(recommendation.id),
            gateway_id=str(recommendation.gateway_id),
            api_id=str(recommendation.api_id),
            recommendation_type=recommendation.recommendation_type.value,
            title=recommendation.title,
            description=recommendation.description,
            priority=recommendation.priority.value,
            estimated_impact=EstimatedImpactResponse(
                metric=recommendation.estimated_impact.metric,
                current_value=recommendation.estimated_impact.current_value,
                expected_value=recommendation.estimated_impact.expected_value,
                improvement_percentage=recommendation.estimated_impact.improvement_percentage,
                confidence=recommendation.estimated_impact.confidence,
            ),
            implementation_effort=recommendation.implementation_effort.value,
            implementation_steps=recommendation.implementation_steps,
            status=recommendation.status.value,
            implemented_at=recommendation.implemented_at.isoformat()
            if recommendation.implemented_at
            else None,
            cost_savings=recommendation.cost_savings,
            created_at=recommendation.created_at.isoformat(),
            updated_at=recommendation.updated_at.isoformat(),
            expires_at=recommendation.expires_at.isoformat() if recommendation.expires_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendation {recommendation_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recommendation: {str(e)}",
        )


@router.post(
    "/gateways/{gateway_id}/optimization/recommendations/generate",
    response_model=dict,
    summary="Generate recommendations for an API within a gateway",
)
async def generate_gateway_recommendations(
    gateway_id: UUID,
    api_id: UUID = Query(..., description="API ID to generate recommendations for"),
    min_impact: float = Query(10.0, ge=0, le=100, description="Minimum expected improvement %"),
) -> dict:
    """
    Generate AI-driven hybrid optimization recommendations for a specific API within a gateway.

    Args:
        gateway_id: Gateway UUID (required)
        api_id: API UUID
        min_impact: Minimum expected improvement percentage

    Returns:
        Generation results with a unified recommendation flow

    Raises:
        HTTPException: If gateway or API not found or generation fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Verify API belongs to gateway
        api_repo = APIRepository()
        api = api_repo.get(str(api_id))
        
        if not api:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"API {api_id} not found",
            )
        
        if str(api.gateway_id) != str(gateway_id):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"API {api_id} not found in gateway {gateway_id}",
            )
        
        recommendation_repo = RecommendationRepository()
        metrics_repo = MetricsRepository()

        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=recommendation_repo,
            metrics_repository=metrics_repo,
            api_repository=api_repo,
            llm_service=llm_service,
        )

        result = await optimization_service.generate_recommendations_for_api(
            api_id=api_id,
            gateway_id=gateway_id,
            min_impact=min_impact,
        )

        return {
            "status": "accepted",
            "message": f"Generated AI-driven optimization recommendations for API {api_id}",
            "result": result,
        }

    except Exception as e:
        logger.error(f"Failed to generate recommendations for API {api_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/insights",
    summary="Get AI insights for recommendation",
)
async def get_gateway_recommendation_insights(
    gateway_id: UUID,
    recommendation_id: UUID,
) -> dict:
    """
    Get AI-generated insights for a specific recommendation within a gateway.

    Args:
        gateway_id: Gateway UUID (required)
        recommendation_id: Recommendation UUID

    Returns:
        AI-generated insights

    Raises:
        HTTPException: If gateway or recommendation not found or insights fail
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Initialize service
        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=RecommendationRepository(),
            metrics_repository=MetricsRepository(),
            api_repository=APIRepository(),
            llm_service=llm_service,
        )

        # Get insights from service
        result = await optimization_service.get_recommendation_insights(str(recommendation_id))

        if result.get("status") == "error":
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=result.get("message", "Recommendation not found"),
            )
        
        # Verify recommendation's API belongs to the gateway
        recommendation = optimization_service.get_recommendation_details(str(recommendation_id))
        if recommendation:
            api_repo = APIRepository()
            api = api_repo.get(str(recommendation.api_id))
            if not api or str(api.gateway_id) != str(gateway_id):
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Recommendation {recommendation_id} not found in gateway {gateway_id}",
                )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendation insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendation insights: {str(e)}",
        )


@router.post(
    "/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/apply",
    summary="Apply recommendation policy to Gateway",
)
async def apply_gateway_recommendation(
    gateway_id: UUID,
    recommendation_id: UUID,
) -> dict:
    """
    Apply a recommendation's policy to the actual Gateway.

    This endpoint:
    1. Retrieves the recommendation from the database
    2. Gets the API and Gateway information
    3. Creates a Gateway adapter
    4. Applies the appropriate policy (caching, compression, rate limiting) to the Gateway
    5. Updates the recommendation status

    Args:
        gateway_id: Gateway UUID (required)
        recommendation_id: Recommendation UUID to apply

    Returns:
        Dictionary with application result:
            - success: bool
            - recommendation_id: str
            - api_id: str
            - gateway_id: str
            - policy_type: str
            - message: str
            - applied_at: str (ISO format)

    Raises:
        HTTPException: If gateway or recommendation not found or application fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Initialize service
        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=RecommendationRepository(),
            metrics_repository=MetricsRepository(),
            api_repository=APIRepository(),
            llm_service=llm_service,
        )

        # Verify recommendation belongs to gateway before applying
        recommendation = optimization_service.get_recommendation_details(str(recommendation_id))
        if recommendation:
            api_repo = APIRepository()
            api = api_repo.get(str(recommendation.api_id))
            if not api or str(api.gateway_id) != str(gateway_id):
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Recommendation {recommendation_id} not found in gateway {gateway_id}",
                )
        
        # Apply recommendation through service
        return await optimization_service.apply_recommendation_to_gateway(str(recommendation_id))

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.error(f"Gateway operation failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply recommendation {recommendation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply recommendation: {str(e)}",
        )


@router.delete(
    "/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/policy",
    summary="Remove applied optimization policy from Gateway",
)
async def remove_gateway_recommendation_policy(
    gateway_id: UUID,
    recommendation_id: UUID,
) -> dict:
    """
    Remove a previously applied optimization policy from the Gateway.

    This endpoint:
    1. Retrieves the recommendation from the database
    2. Gets the API and Gateway information
    3. Creates a Gateway adapter
    4. Removes the policy (caching, compression, rate limiting) from the Gateway
    5. Updates the recommendation status to PENDING

    Args:
        gateway_id: Gateway UUID (required)
        recommendation_id: Recommendation UUID to remove policy for

    Returns:
        Dictionary with removal result:
            - success: bool
            - recommendation_id: str
            - api_id: str
            - gateway_id: str
            - policy_type: str
            - message: str
            - removed_at: str (ISO format)

    Raises:
        HTTPException: If gateway or recommendation not found, not implemented, or removal fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Initialize service
        from app.services.llm_service import LLMService
        from app.config import Settings

        settings = Settings()
        llm_service = LLMService(settings)

        optimization_service = OptimizationService(
            recommendation_repository=RecommendationRepository(),
            metrics_repository=MetricsRepository(),
            api_repository=APIRepository(),
            llm_service=llm_service,
        )

        # Verify recommendation belongs to gateway before removing
        recommendation = optimization_service.get_recommendation_details(str(recommendation_id))
        if recommendation:
            api_repo = APIRepository()
            api = api_repo.get(str(recommendation.api_id))
            if not api or str(api.gateway_id) != str(gateway_id):
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Recommendation {recommendation_id} not found in gateway {gateway_id}",
                )
        
        # Remove recommendation policy through service
        return await optimization_service.remove_recommendation_policy(str(recommendation_id))

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        if "not implemented" in str(e).lower():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.error(f"Gateway operation failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to remove policy for recommendation {recommendation_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove recommendation policy: {str(e)}",
        )

@router.post(
    "/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/validate",
    response_model=dict,
    status_code=http_status.HTTP_200_OK,
    summary="Validate recommendation impact",
    description="Validate that an implemented recommendation achieved its expected impact by analyzing post-implementation metrics"
)
async def validate_gateway_recommendation(
    gateway_id: UUID,
    recommendation_id: UUID,
    validation_window_hours: int = Query(24, description="Hours of post-implementation metrics to analyze"),
) -> dict:
    """
    Validate the impact of an implemented recommendation.
    
    Analyzes post-implementation metrics to determine if the recommendation
    achieved its expected improvement. Requires at least validation_window_hours
    to have passed since implementation.
    
    Args:
        gateway_id: Gateway UUID
        recommendation_id: Recommendation UUID to validate
        validation_window_hours: Hours of metrics to analyze (default: 24)
        settings: Application settings
        llm_service: LLM service dependency
        
    Returns:
        Validation results with actual vs expected impact
        
    Raises:
        HTTPException: If gateway/recommendation not found or validation fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Create optimization service
        from app.db.repositories.recommendation_repository import RecommendationRepository
        from app.db.repositories.metrics_repository import MetricsRepository
        from app.db.repositories.api_repository import APIRepository
        
        recommendation_repo = RecommendationRepository()
        metrics_repo = MetricsRepository()
        api_repo = APIRepository()
        
        from app.config import Settings
        from app.services.llm_service import LLMService
        
        settings = Settings()
        llm_service = LLMService(settings)
        
        optimization_service = OptimizationService(
            recommendation_repository=recommendation_repo,
            metrics_repository=metrics_repo,
            api_repository=api_repo,
            llm_service=llm_service
        )
        
        # Validate recommendation
        result = await optimization_service.validate_recommendation_impact(
            recommendation_id=str(recommendation_id),
            validation_window_hours=validation_window_hours
        )
        
        logger.info(
            f"Validated recommendation {recommendation_id} for gateway {gateway_id}: "
            f"Success={result['success']}, Actual={result['actual_improvement']}%"
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error for recommendation {recommendation_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.error(f"Validation runtime error for recommendation {recommendation_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate recommendation {recommendation_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate recommendation: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/actions",
    response_model=list,
    summary="Get recommendation action history",
    description="Get the history of all actions taken on a recommendation"
)
async def get_recommendation_actions(
    gateway_id: UUID,
    recommendation_id: UUID,
) -> list:
    """
    Get the action history for a recommendation.
    
    Returns all remediation actions that have been taken on the recommendation,
    including policy applications, removals, validations, and failures.
    
    Args:
        gateway_id: Gateway UUID
        recommendation_id: Recommendation UUID
        settings: Application settings
        llm_service: LLM service dependency
        
    Returns:
        List of remediation actions
        
    Raises:
        HTTPException: If gateway/recommendation not found
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Get recommendation
        from app.db.repositories.recommendation_repository import RecommendationRepository
        recommendation_repo = RecommendationRepository()
        
        recommendation = recommendation_repo.get_recommendation(str(recommendation_id))
        
        if not recommendation:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {recommendation_id} not found",
            )
        
        # Return remediation actions
        actions = recommendation.remediation_actions or []
        
        logger.info(
            f"Retrieved {len(actions)} actions for recommendation {recommendation_id}"
        )
        
        return [action.dict() if hasattr(action, 'dict') else action for action in actions]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get actions for recommendation {recommendation_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendation actions: {str(e)}",
        )


@router.get(
    "/optimization/recommendations/search",
    response_model=RecommendationListResponse,
    summary="Search optimization recommendations with multiple filters",
    description="Search optimization recommendations across all gateways with flexible multi-criteria filtering",
)
async def search_recommendations(
    recommendation_type: Optional[RecommendationType] = Query(None, alias="type", description="Filter by recommendation type"),
    priority: Optional[RecommendationPriority] = Query(None, description="Filter by priority"),
    rec_status: Optional[RecommendationStatus] = Query(None, alias="status", description="Filter by status"),
    impact_min: Optional[float] = Query(None, ge=0, le=100, description="Minimum expected impact percentage"),
    impact_max: Optional[float] = Query(None, ge=0, le=100, description="Maximum expected impact percentage"),
    api_name: Optional[str] = Query(None, description="Filter by API name pattern (case-insensitive wildcard)"),
    gateway_id: Optional[UUID] = Query(None, description="Filter by gateway ID"),
    created_after: Optional[datetime] = Query(None, description="Filter recommendations created after this date (ISO 8601)"),
    created_before: Optional[datetime] = Query(None, description="Filter recommendations created before this date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
) -> RecommendationListResponse:
    """
    Search optimization recommendations with multiple filters.
    
    Supports flexible filtering by:
    - Recommendation type (caching, rate_limiting, connection_pooling, etc.)
    - Priority (high, medium, low)
    - Status (pending, in_progress, implemented, rejected)
    - Expected impact range (0-100%)
    - API name pattern (case-insensitive wildcard search)
    - Gateway ID
    - Creation date range
    
    All filters are optional and combined with AND logic.
    Results are paginated with configurable page size (max 100).
    
    Args:
        recommendation_type: Optional recommendation type filter
        priority: Optional priority filter
        rec_status: Optional status filter
        impact_min: Optional minimum expected impact percentage
        impact_max: Optional maximum expected impact percentage
        api_name: Optional API name pattern (case-insensitive)
        gateway_id: Optional gateway ID filter
        created_after: Optional start date for creation range
        created_before: Optional end date for creation range
        page: Page number (1-based)
        page_size: Number of items per page (max 100)
        
    Returns:
        Paginated list of recommendations matching filters
        
    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(
            f"Searching recommendations: type={recommendation_type}, priority={priority}, "
            f"status={rec_status}, impact_min={impact_min}, impact_max={impact_max}, "
            f"api_name={api_name}, gateway_id={gateway_id}, created_after={created_after}, "
            f"created_before={created_before}, page={page}, page_size={page_size}"
        )
        
        recommendation_repo = RecommendationRepository()
        
        # Call repository search method
        recommendations, total = recommendation_repo.search_recommendations(
            type=recommendation_type,
            priority=priority,
            status=rec_status,
            impact_min=impact_min,
            impact_max=impact_max,
            api_name=api_name,
            gateway_id=gateway_id,
            created_after=created_after,
            created_before=created_before,
            page=page,
            page_size=page_size,
        )
        
        logger.info(f"Found {total} recommendations matching search criteria")
        
        # Convert to response models
        api_repo = APIRepository()
        recommendation_responses = []
        
        for rec in recommendations:
            # Get API name
            api = api_repo.get(str(rec.api_id))
            api_name_str = api.name if api else "Unknown"
            
            ai_context = None
            if rec.ai_context:
                ai_context = AIContextResponse(
                    performance_analysis=rec.ai_context.performance_analysis,
                    implementation_guidance=rec.ai_context.implementation_guidance,
                    prioritization=rec.ai_context.prioritization,
                    generated_at=rec.ai_context.generated_at.isoformat() if rec.ai_context.generated_at else None,
                )
            
            recommendation_responses.append(
                RecommendationResponse(
                    id=str(rec.id),
                    gateway_id=str(rec.gateway_id),
                    api_id=str(rec.api_id),
                    api_name=api_name_str,
                    recommendation_type=rec.recommendation_type.value,
                    title=rec.title,
                    description=rec.description,
                    priority=rec.priority.value,
                    estimated_impact=EstimatedImpactResponse(
                        metric=rec.estimated_impact.metric,
                        current_value=rec.estimated_impact.current_value,
                        expected_value=rec.estimated_impact.expected_value,
                        improvement_percentage=rec.estimated_impact.improvement_percentage,
                        confidence=rec.estimated_impact.confidence,
                    ),
                    implementation_effort=rec.implementation_effort.value,
                    implementation_steps=rec.implementation_steps,
                    status=rec.status.value,
                    implemented_at=rec.implemented_at.isoformat() if rec.implemented_at else None,
                    cost_savings=rec.cost_savings,
                    ai_context=ai_context,
                    created_at=rec.created_at.isoformat(),
                    updated_at=rec.updated_at.isoformat(),
                    expires_at=rec.expires_at.isoformat() if rec.expires_at else None,
                )
            )
        
        return RecommendationListResponse(
            recommendations=recommendation_responses,
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error(f"Failed to search recommendations: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search recommendations: {str(e)}",
        )
