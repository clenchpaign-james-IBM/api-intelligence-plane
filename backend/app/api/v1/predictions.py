"""
Predictions API Endpoints

REST API endpoints for API failure predictions.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status as http_status
from pydantic import BaseModel

from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.metrics_repository import MetricsRepository
from app.db.repositories.api_repository import APIRepository
from app.models.prediction import PredictionSeverity, PredictionStatus, PredictionType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Predictions"])


# Response Models
class ContributingFactorResponse(BaseModel):
    """Response model for contributing factor."""
    
    factor: str
    current_value: float
    threshold: float
    trend: str
    weight: float


class PredictionResponse(BaseModel):
    """Response model for a single prediction."""
    
    id: str
    api_id: str
    api_name: Optional[str] = None
    prediction_type: str
    predicted_at: str
    predicted_time: str
    confidence_score: float
    severity: str
    status: str
    contributing_factors: list[ContributingFactorResponse]
    recommended_actions: list[str]
    actual_outcome: Optional[str] = None
    actual_time: Optional[str] = None
    accuracy_score: Optional[float] = None
    model_version: str
    metadata: Optional[dict] = None
    created_at: str
    updated_at: str


class PredictionListResponse(BaseModel):
    """Response model for prediction list."""
    
    predictions: list[PredictionResponse]
    total: int
    page: int
    page_size: int


@router.get(
    "/predictions",
    response_model=PredictionListResponse,
    summary="List all failure predictions across all gateways",
)
async def list_all_predictions(
    gateway_id: Optional[UUID] = Query(None, description="Optional gateway filter"),
    api_id: Optional[UUID] = Query(None, description="Filter by API ID"),
    severity: Optional[PredictionSeverity] = Query(None, description="Filter by severity"),
    status: Optional[PredictionStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PredictionListResponse:
    """
    List all failure predictions across all gateways with optional filtering.
    
    This is an aggregate endpoint that returns predictions from all gateways.
    Use gateway_id parameter to filter by specific gateway.
    
    Args:
        gateway_id: Optional gateway filter
        api_id: Optional filter by specific API ID
        severity: Filter by severity level
        status: Filter by prediction status
        page: Page number (1-indexed)
        page_size: Items per page
        
    Returns:
        List of predictions with pagination info
    """
    try:
        # Initialize repository
        prediction_repo = PredictionRepository()
        
        # Get predictions with filters
        result = prediction_repo.list_predictions(
            api_id=str(api_id) if api_id else None,
            severity=severity,
            status=status,
            page=page,
            page_size=page_size,
        )
        
        # Filter by gateway if specified
        if gateway_id:
            api_repo = APIRepository()
            gateway_apis, _ = api_repo.find_by_gateway(gateway_id=gateway_id, size=10000)
            gateway_api_ids = {str(api.id) for api in gateway_apis}
            
            filtered_predictions = [
                p for p in result["predictions"]
                if str(p.api_id) in gateway_api_ids
            ]
            result["predictions"] = filtered_predictions
            result["total"] = len(filtered_predictions)
        
        # Convert to response models
        predictions_response = [
            PredictionResponse(
                id=str(p.id),
                api_id=str(p.api_id),
                api_name=p.api_name,
                prediction_type=p.prediction_type,
                predicted_at=p.predicted_at.isoformat(),
                predicted_time=p.predicted_time.isoformat(),
                confidence_score=p.confidence_score,
                severity=p.severity.value,
                status=p.status.value,
                contributing_factors=[
                    ContributingFactorResponse(**factor.model_dump())
                    for factor in p.contributing_factors
                ],
                recommended_actions=p.recommended_actions,
                actual_outcome=p.actual_outcome,
                actual_time=p.actual_time.isoformat() if p.actual_time else None,
                accuracy_score=p.accuracy_score,
                model_version=p.model_version,
                metadata=p.metadata,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in result["predictions"]
        ]
        
        return PredictionListResponse(
            predictions=predictions_response,
            total=result["total"],
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error(f"Failed to list predictions: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list predictions: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/predictions",
    response_model=PredictionListResponse,
    summary="List failure predictions for a gateway",
)
async def list_gateway_predictions(
    gateway_id: UUID,
    api_id: Optional[UUID] = Query(None, description="Filter by API ID within gateway"),
    severity: Optional[PredictionSeverity] = Query(None, description="Filter by severity"),
    status: Optional[PredictionStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PredictionListResponse:
    """
    List failure predictions for APIs within a specific gateway.
    
    Args:
        gateway_id: Gateway UUID (required)
        api_id: Optional filter by specific API ID within gateway
        severity: Filter by severity level
        status: Filter by prediction status
        page: Page number (1-indexed)
        page_size: Items per page
        
    Returns:
        List of predictions with pagination info
        
    Raises:
        HTTPException: If gateway not found or prediction retrieval fails
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
        
        # Initialize repository
        prediction_repo = PredictionRepository()
        
        # Get predictions with filters
        # Note: We need to filter by gateway_id at the repository level
        # For now, we'll get predictions and filter by gateway
        result = prediction_repo.list_predictions(
            api_id=str(api_id) if api_id else None,
            severity=severity,
            status=status,
            page=page,
            page_size=page_size,
        )
        
        # Filter predictions to only include those from APIs in this gateway
        if not api_id:
            # Get all APIs for this gateway
            api_repo = APIRepository()
            gateway_apis, _ = api_repo.find_by_gateway(gateway_id=gateway_id, size=10000)
            gateway_api_ids = {str(api.id) for api in gateway_apis}
            
            # Filter predictions
            filtered_predictions = [
                p for p in result["predictions"]
                if str(p.api_id) in gateway_api_ids
            ]
            result["predictions"] = filtered_predictions
            result["total"] = len(filtered_predictions)
        
        # Convert to response models
        predictions_response = [
            PredictionResponse(
                id=str(p.id),
                api_id=str(p.api_id),
                api_name=p.api_name,
                prediction_type=p.prediction_type.value,
                predicted_at=p.predicted_at.isoformat(),
                predicted_time=p.predicted_time.isoformat(),
                confidence_score=p.confidence_score,
                severity=p.severity.value,
                status=p.status.value,
                contributing_factors=[
                    ContributingFactorResponse(
                        factor=f.factor,
                        current_value=f.current_value,
                        threshold=f.threshold,
                        trend=f.trend,
                        weight=f.weight,
                    )
                    for f in p.contributing_factors
                ],
                recommended_actions=p.recommended_actions,
                actual_outcome=p.actual_outcome.value if p.actual_outcome else None,
                actual_time=p.actual_time.isoformat() if p.actual_time else None,
                accuracy_score=p.accuracy_score,
                model_version=p.model_version,
                metadata=p.metadata,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in result["predictions"]
        ]
        
        return PredictionListResponse(
            predictions=predictions_response,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
        )
        
    except Exception as e:
        logger.error(f"Failed to list predictions: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve predictions: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/predictions/{prediction_id}",
    response_model=PredictionResponse,
    summary="Get prediction details",
)
async def get_gateway_prediction(
    gateway_id: UUID,
    prediction_id: UUID,
) -> PredictionResponse:
    """
    Get details for a specific prediction within a gateway.
    
    Args:
        gateway_id: Gateway UUID (required)
        prediction_id: Prediction UUID
        
    Returns:
        Prediction details
        
    Raises:
        HTTPException: If gateway or prediction not found
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
        
        # Initialize repository
        prediction_repo = PredictionRepository()
        
        # Get prediction
        prediction = prediction_repo.get_prediction(str(prediction_id))
        
        if not prediction:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Prediction {prediction_id} not found",
            )
        
        # Verify prediction's API belongs to the gateway
        api_repo = APIRepository()
        try:
            api = api_repo.get(str(prediction.api_id))
            if not api or str(api.gateway_id) != str(gateway_id):
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Prediction {prediction_id} not found in gateway {gateway_id}",
                )
            api_name = api.name if api else None
        except HTTPException:
            raise
        except Exception:
            api_name = None
        
        # Convert to response model
        return PredictionResponse(
            id=str(prediction.id),
            api_id=str(prediction.api_id),
            api_name=api_name or f"API {str(prediction.api_id)[:8]}",
            prediction_type=prediction.prediction_type.value,
            predicted_at=prediction.predicted_at.isoformat(),
            predicted_time=prediction.predicted_time.isoformat(),
            confidence_score=prediction.confidence_score,
            severity=prediction.severity.value,
            status=prediction.status.value,
            contributing_factors=[
                ContributingFactorResponse(
                    factor=f.factor,
                    current_value=f.current_value,
                    threshold=f.threshold,
                    trend=f.trend,
                    weight=f.weight,
                )
                for f in prediction.contributing_factors
            ],
            recommended_actions=prediction.recommended_actions,
            actual_outcome=prediction.actual_outcome.value if prediction.actual_outcome else None,
            actual_time=prediction.actual_time.isoformat() if prediction.actual_time else None,
            accuracy_score=prediction.accuracy_score,
            model_version=prediction.model_version,
            created_at=prediction.created_at.isoformat(),
            updated_at=prediction.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prediction {prediction_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve prediction: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/predictions/stats/accuracy",
    summary="Get prediction accuracy statistics for a gateway",
)
async def get_gateway_prediction_accuracy_stats(
    gateway_id: UUID,
    api_id: Optional[UUID] = Query(None, description="Filter by API ID within gateway"),
    days: int = Query(30, ge=1, le=90, description="Number of days to look back"),
) -> dict:
    """
    Get prediction accuracy statistics for APIs within a gateway.
    
    Args:
        gateway_id: Gateway UUID (required)
        api_id: Optional API ID filter within gateway
        days: Number of days to look back (1-90)
        
    Returns:
        Accuracy statistics
        
    Raises:
        HTTPException: If gateway not found or retrieval fails
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
        
        # Initialize repository
        prediction_repo = PredictionRepository()
        
        # Get accuracy stats
        stats = prediction_repo.get_prediction_accuracy_stats(
            api_id=str(api_id) if api_id else None,
            days=days,
        )
        
        return {
            "status": "success",
            "stats": stats,
            "period_days": days,
        }
        
    except Exception as e:
        logger.error(f"Failed to get accuracy stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve accuracy statistics: {str(e)}",
        )

@router.get(
    "/gateways/{gateway_id}/predictions/{prediction_id}/explanation",
    summary="Get AI explanation for prediction",
)
async def get_gateway_prediction_explanation(
    gateway_id: UUID,
    prediction_id: UUID,
) -> dict:
    """
    Get AI-generated explanation for a specific prediction within a gateway.
    
    Args:
        gateway_id: Gateway UUID (required)
        prediction_id: Prediction UUID
        
    Returns:
        AI-generated explanation
        
    Raises:
        HTTPException: If gateway or prediction not found or explanation fails
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
        
        # Initialize repositories
        prediction_repo = PredictionRepository()
        
        # Get prediction
        prediction = prediction_repo.get_prediction(str(prediction_id))
        
        if not prediction:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Prediction {prediction_id} not found",
            )
        
        # Verify prediction's API belongs to the gateway
        api_repo = APIRepository()
        api = api_repo.get(str(prediction.api_id))
        if not api or str(api.gateway_id) != str(gateway_id):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Prediction {prediction_id} not found in gateway {gateway_id}",
            )
        
        # Try to get LLM service
        try:
            from app.services.llm_service import LLMService
            from app.config import Settings
            settings = Settings()
            llm_service = LLMService(settings)
            
            # Generate explanation
            explanation = await llm_service.generate_prediction_explanation({
                "prediction_type": prediction.prediction_type.value,
                "confidence_score": prediction.confidence_score,
                "severity": prediction.severity.value,
                "contributing_factors": [
                    {
                        "factor": f.factor,
                        "current_value": f.current_value,
                        "threshold": f.threshold,
                        "trend": f.trend,
                    }
                    for f in prediction.contributing_factors
                ],
                "recommended_actions": prediction.recommended_actions,
            })
            
            return {
                "status": "success",
                "prediction_id": str(prediction_id),
                "explanation": explanation,
            }
            
        except Exception as e:
            logger.warning(f"LLM explanation unavailable: {e}")
            return {
                "status": "fallback",
                "prediction_id": str(prediction_id),
                "explanation": f"This is a {prediction.severity.value} severity {prediction.prediction_type.value} prediction with {prediction.confidence_score:.1%} confidence.",
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prediction explanation: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prediction explanation: {str(e)}",
        )

@router.get(
    "/predictions/search",
    response_model=PredictionListResponse,
    summary="Search failure predictions with multiple filters",
    description="Search failure predictions across all gateways with flexible multi-criteria filtering",
)
async def search_predictions(
    prediction_type: Optional[PredictionType] = Query(None, description="Filter by prediction type (failure, degradation, capacity, security)"),
    confidence_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score (0.0-1.0)"),
    confidence_max: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum confidence score (0.0-1.0)"),
    severity: Optional[PredictionSeverity] = Query(None, description="Filter by severity"),
    pred_status: Optional[PredictionStatus] = Query(None, alias="status", description="Filter by status"),
    predicted_after: Optional[datetime] = Query(None, description="Filter predictions made after this date (ISO 8601)"),
    predicted_before: Optional[datetime] = Query(None, description="Filter predictions made before this date (ISO 8601)"),
    api_name: Optional[str] = Query(None, description="Filter by API name pattern (case-insensitive wildcard)"),
    gateway_id: Optional[UUID] = Query(None, description="Filter by gateway ID"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
) -> PredictionListResponse:
    """
    Search failure predictions with multiple filters.
    
    Supports flexible filtering by:
    - Prediction type (failure, degradation, capacity, security)
    - Confidence score range (0.0-1.0)
    - Severity (critical, high, medium, low)
    - Status (pending, confirmed, false_positive, resolved)
    - Prediction date range
    - API name pattern (case-insensitive wildcard search)
    - Gateway ID
    
    All filters are optional and combined with AND logic.
    Results are paginated with configurable page size (max 100).
    
    Args:
        prediction_type: Optional prediction type filter
        confidence_min: Optional minimum confidence score
        confidence_max: Optional maximum confidence score
        severity: Optional severity filter
        pred_status: Optional status filter
        predicted_after: Optional start date for prediction range
        predicted_before: Optional end date for prediction range
        api_name: Optional API name pattern (case-insensitive)
        gateway_id: Optional gateway ID filter
        page: Page number (1-based)
        page_size: Number of items per page (max 100)
        
    Returns:
        Paginated list of predictions matching filters
        
    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(
            f"Searching predictions: type={prediction_type}, confidence_min={confidence_min}, "
            f"confidence_max={confidence_max}, severity={severity}, status={pred_status}, "
            f"predicted_after={predicted_after}, predicted_before={predicted_before}, "
            f"api_name={api_name}, gateway_id={gateway_id}, page={page}, page_size={page_size}"
        )
        
        prediction_repo = PredictionRepository()
        
        # Call repository search method
        predictions, total = prediction_repo.search_predictions(
            prediction_type=prediction_type,
            confidence_min=confidence_min,
            confidence_max=confidence_max,
            severity=severity,
            status=pred_status,
            predicted_after=predicted_after,
            predicted_before=predicted_before,
            api_name=api_name,
            gateway_id=gateway_id,
            page=page,
            page_size=page_size,
        )
        
        logger.info(f"Found {total} predictions matching search criteria")
        
        # Convert to response models
        api_repo = APIRepository()
        prediction_responses = []
        
        for pred in predictions:
            # Get API name
            api = api_repo.get(str(pred.api_id))
            api_name_str = api.name if api else "Unknown"
            
            # Convert contributing factors
            contributing_factors = [
                ContributingFactorResponse(
                    factor=cf.factor,
                    current_value=cf.current_value,
                    threshold=cf.threshold,
                    trend=cf.trend,
                    weight=cf.weight,
                )
                for cf in pred.contributing_factors
            ]
            
            prediction_responses.append(
                PredictionResponse(
                    id=str(pred.id),
                    api_id=str(pred.api_id),
                    api_name=api_name_str,
                    prediction_type=pred.prediction_type.value,
                    predicted_at=pred.predicted_at.isoformat(),
                    predicted_time=pred.predicted_time.isoformat(),
                    confidence_score=pred.confidence_score,
                    severity=pred.severity.value,
                    status=pred.status.value,
                    contributing_factors=contributing_factors,
                    recommended_actions=pred.recommended_actions,
                    actual_outcome=pred.actual_outcome,
                    actual_time=pred.actual_time.isoformat() if pred.actual_time else None,
                    accuracy_score=pred.accuracy_score,
                    model_version=pred.model_version,
                    metadata=pred.metadata,
                    created_at=pred.created_at.isoformat(),
                    updated_at=pred.updated_at.isoformat(),
                )
            )
        
        return PredictionListResponse(
            predictions=prediction_responses,
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error(f"Failed to search predictions: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search predictions: {str(e)}",
        )


# Made with Bob
