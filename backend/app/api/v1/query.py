"""
Query API Endpoints

REST API endpoints for natural language query interface.
"""

import logging
from datetime import datetime
from typing import Any, Optional, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status as http_status
from langchain_community.chat_models import ChatLiteLLM
from pydantic import BaseModel, Field

from app.db.repositories.query_repository import QueryRepository
from app.db.repositories.api_repository import APIRepository
from app.db.repositories.metrics_repository import MetricsRepository
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.recommendation_repository import RecommendationRepository
from app.db.repositories.compliance_repository import ComplianceRepository
from app.db.repositories.gateway_repository import GatewayRepository
from app.db.repositories.vulnerability_repository import VulnerabilityRepository
from app.db.repositories.transactional_log_repository import TransactionalLogRepository
from app.services.agentic_query_service import AgenticQueryService
from app.services.context_manager import get_context_manager
from app.services.llm_service import LLMService
from app.services.query_service import QueryService
from app.models.query import Query, UserFeedback
from app.config import Settings
from app.tools import initialize_tools

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query"])


# Request Models
class NewSessionRequest(BaseModel):
    """Request model for creating a new session."""
    
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class NewSessionResponse(BaseModel):
    """Response model for new session creation."""
    
    session_id: UUID = Field(..., description="New session ID")
    created_at: str = Field(..., description="Session creation timestamp")


class QueryRequest(BaseModel):
    """Request model for executing a natural language query."""
    
    query_text: str = Field(..., min_length=1, max_length=5000, description="Natural language query")
    session_id: Optional[UUID] = Field(None, description="Conversation session ID")
    use_ai_agents: bool = Field(default=True, description="Enable AI agent enhancement for predictions and performance queries")


class FeedbackRequest(BaseModel):
    """Request model for providing feedback on a query."""
    
    feedback: UserFeedback = Field(..., description="User feedback")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional feedback comment")


# Response Models
class QueryResponse(BaseModel):
    """Response model for query execution."""
    
    query_id: UUID = Field(..., description="Query ID")
    query_text: str = Field(..., description="Original query text")
    response_text: str = Field(..., description="Natural language response")
    confidence_score: float = Field(..., description="Confidence score (0-1)")
    results: dict = Field(..., description="Query results")
    follow_up_queries: Optional[list[str]] = Field(None, description="Suggested follow-up queries")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    execution_mode: Optional[str] = Field(None, description="Execution mode used")
    agent_decisions: Optional[list[dict]] = Field(None, description="Agent decision trace")
    tool_invocations: Optional[list[dict]] = Field(None, description="Tool invocation trace")
    session_id: Optional[UUID] = Field(None, description="Session identifier")


class QueryHistoryResponse(BaseModel):
    """Response model for query history."""
    
    items: list[Query]
    total: int
    page: int
    page_size: int


# Initialize dependencies
settings = Settings()
query_repo = QueryRepository()
api_repo = APIRepository()
metrics_repo = MetricsRepository()
prediction_repo = PredictionRepository()
recommendation_repo = RecommendationRepository()
compliance_repo = ComplianceRepository()
gateway_repo = GatewayRepository()
vulnerability_repo = VulnerabilityRepository()
transactional_log_repo = TransactionalLogRepository()
llm_service = LLMService(settings)
tool_registry = initialize_tools()

# Initialize query services
query_service = QueryService(
    query_repository=query_repo,
    api_repository=api_repo,
    metrics_repository=metrics_repo,
    prediction_repository=prediction_repo,
    recommendation_repository=recommendation_repo,
    llm_service=llm_service,
    compliance_repository=compliance_repo,
    gateway_repository=gateway_repo,
    vulnerability_repository=vulnerability_repo,
    transactional_log_repository=transactional_log_repo,
)

# Initialize LangChain-compatible LLM for agents
# Use the first configured provider from LLMService
if llm_service.providers:
    first_provider = llm_service.providers[0]
    langchain_llm = ChatLiteLLM(
        model=first_provider["model"],
        api_key=first_provider.get("api_key"),
        api_base=first_provider.get("api_base"),
        temperature=0.7,
    )
else:
    # Fallback to a default model if no providers configured
    logger.warning("No LLM providers configured, using default model")
    langchain_llm = ChatLiteLLM(model="gpt-3.5-turbo", temperature=0.7)

# Initialize agentic query service with fallback support (T072, T073)
from app.services.fallback_manager import FallbackManager
from app.db.client import get_client

context_manager = get_context_manager()
opensearch_client = get_client()
fallback_manager = FallbackManager(
    confidence_threshold=settings.FALLBACK_CONFIDENCE_THRESHOLD,
    failure_rate_threshold=settings.FALLBACK_FAILURE_RATE_THRESHOLD,
    timeout_seconds=settings.FALLBACK_TIMEOUT_SECONDS,
    opensearch_client=opensearch_client,  # T070: Enable OpenSearch logging
)
agentic_query_service = AgenticQueryService(
    llm=langchain_llm,
    tool_registry=tool_registry,
    context_manager=context_manager,
    fallback_service=query_service,  # T072: Enable fallback to OpenSearch
    fallback_manager=fallback_manager,  # T073: Use configured thresholds
)


@router.post(
    "/query/session/new",
    response_model=NewSessionResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create new query session",
    description="Create a new conversation session for natural language queries",
)
async def create_new_session(request: Optional[NewSessionRequest] = None) -> NewSessionResponse:
    """
    Create a new query session.
    
    Args:
        request: Optional request with user_id
        
    Returns:
        New session response with session ID
    """
    session_id = uuid4()
    created_at = datetime.utcnow().isoformat()
    
    logger.info(f"Created new query session: {session_id}")
    
    return NewSessionResponse(
        session_id=session_id,
        created_at=created_at,
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Execute natural language query",
    description="Process a natural language query and return results with AI-generated response",
)
async def execute_query(request: QueryRequest) -> QueryResponse:
    """
    Execute a natural language query.
    
    Args:
        request: Query request with query text, optional session ID, and AI agent flag
        
    Returns:
        Query response with results and natural language answer
        
    Raises:
        HTTPException: If query processing fails
    """
    request.use_ai_agents = True
    try:
        session_id = request.session_id or uuid4()

        if request.use_ai_agents:
            query = await agentic_query_service.process_query(
                query_text=request.query_text,
                session_id=session_id,
            )
        else:
            query = await query_service.process_query(
                query_text=request.query_text,
                session_id=session_id,
            )

        logger.info(f"Processed query {query.id} with confidence {query.confidence_score}")

        return QueryResponse(
            query_id=query.id,
            query_text=query.query_text,
            response_text=query.response_text,
            confidence_score=query.confidence_score,
            results=query.results.model_dump(),
            follow_up_queries=query.follow_up_queries,
            execution_time_ms=query.execution_time_ms,
            execution_mode=query.execution_mode.value if query.execution_mode else None,
            agent_decisions=[
                decision.model_dump() for decision in (query.agent_decisions or [])
            ] or None,
            tool_invocations=[
                invocation.model_dump() for invocation in (query.tool_invocations or [])
            ] or None,
            session_id=query.session_id,
        )
        
    except Exception as e:
        logger.error(f"Failed to execute query: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}",
        )


@router.get(
    "/query/{query_id}",
    response_model=Query,
    status_code=http_status.HTTP_200_OK,
    summary="Get query by ID",
    description="Retrieve a specific query by its ID",
)
async def get_query(query_id: UUID) -> Query:
    """
    Get a query by ID.
    
    Args:
        query_id: Query UUID
        
    Returns:
        Query object
        
    Raises:
        HTTPException: If query not found
    """
    query = query_repo.get(str(query_id))
    
    if not query:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Query {query_id} not found",
        )
    
    return query


@router.get(
    "/query/session/{session_id}",
    response_model=QueryHistoryResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Get queries by session",
    description="Retrieve all queries for a specific conversation session",
)
async def get_session_queries(
    session_id: UUID,
    page: int = 1,
    page_size: int = 50,
) -> QueryHistoryResponse:
    """
    Get all queries for a session.
    
    Args:
        session_id: Session UUID
        page: Page number (1-based)
        page_size: Number of items per page
        
    Returns:
        Query history response
    """
    from_ = (page - 1) * page_size
    
    queries, total = query_repo.get_by_session(
        session_id=session_id,
        size=page_size,
        from_=from_,
    )
    
    return QueryHistoryResponse(
        items=queries,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/query/stats",
    status_code=http_status.HTTP_200_OK,
    summary="Get query statistics",
    description="Retrieve aggregate query statistics for monitoring",
)
async def get_query_stats(
    session_id: Optional[UUID] = None,
    hours: int = 24,
) -> dict:
    """Get query execution statistics."""
    try:
        return query_repo.get_query_statistics(session_id=session_id, hours=hours)
    except Exception as e:
        logger.error(f"Failed to retrieve query statistics: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve query statistics: {str(e)}",
        )


@router.get(
    "/query/fallback/statistics",
    status_code=http_status.HTTP_200_OK,
    summary="Get fallback statistics",
    description="Retrieve fallback rate and reason analytics for monitoring (T072)",
)
async def get_fallback_statistics() -> dict[str, Any]:
    """
    T072: Get fallback reason analytics.
    
    Returns statistics about fallback usage including:
    - Total queries processed
    - Fallback queries count
    - Fallback rate percentage
    - Agentic queries count
    - Agentic rate percentage
    - Breakdown by fallback reason
    
    Returns:
        Dictionary with fallback statistics
    """
    try:
        stats = agentic_query_service.get_fallback_statistics()
        
        logger.info(
            f"Fallback statistics retrieved: "
            f"{stats['fallback_rate']:.1%} fallback rate "
            f"({stats['fallback_queries']}/{stats['total_queries']} queries)"
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to retrieve fallback statistics: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve fallback statistics: {str(e)}",
        )


@router.get(
    "/query/recent",
    response_model=list[Query],
    status_code=http_status.HTTP_200_OK,
    summary="Get recent queries",
    description="Retrieve recent queries, optionally filtered by user",
)
async def get_recent_queries(
    user_id: Optional[str] = None,
    hours: int = 24,
    size: int = 20,
) -> list[Query]:
    """
    Get recent queries.
    
    Args:
        user_id: Optional user identifier
        hours: Number of hours to look back
        size: Maximum number of results
        
    Returns:
        List of recent queries
    """
    queries = query_repo.get_recent_queries(
        user_id=user_id,
        hours=hours,
        size=size,
    )
    
    return queries


@router.post(
    "/query/{query_id}/feedback",
    response_model=Query,
    status_code=http_status.HTTP_200_OK,
    summary="Provide feedback on query",
    description="Submit user feedback on a query result",
)
async def submit_feedback(
    query_id: UUID,
    request: FeedbackRequest,
) -> Query:
    """
    Submit feedback on a query.
    
    Args:
        query_id: Query UUID
        request: Feedback request
        
    Returns:
        Updated query
        
    Raises:
        HTTPException: If query not found
    """
    updated_query = query_repo.update_feedback(
        query_id=str(query_id),
        feedback=request.feedback,
        comment=request.comment,
    )
    
    if not updated_query:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Query {query_id} not found",
        )
    
    logger.info(f"Updated feedback for query {query_id}: {request.feedback}")
    
    return updated_query


@router.get(
    "/query/statistics",
    response_model=dict,
    status_code=http_status.HTTP_200_OK,
    summary="Get query statistics",
    description="Retrieve query analytics and statistics",
)
async def get_query_statistics(
    session_id: Optional[UUID] = None,
    hours: int = 24,
) -> dict:
    """
    Get query statistics.
    
    Args:
        session_id: Optional session to filter by
        hours: Number of hours to look back
        
    Returns:
        Query statistics
    """
    stats = query_repo.get_query_statistics(
        session_id=session_id,
        hours=hours,
    )
    
    return stats


# Made with Bob