"""Query model for API Intelligence Plane.

Represents a natural language query with original text, interpreted intent,
results, and user feedback.

Extended for agentic query service (Feature: 001-agentic-query) to include
agent decisions, tool invocations, and execution mode metadata.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

# Import agentic models for extended query support
from app.models.agent import (
    AgentDecision,
    ExecutionMode,
    FallbackReason,
    ToolInvocation,
)


class QueryType(str, Enum):
    """Classified natural language query type.
    
    Categorizes user queries to enable appropriate data retrieval, analysis,
    and response generation strategies.
    
    Attributes:
        STATUS: Current state queries - "What is the status of API X?", "Show me open vulnerabilities"
        TREND: Historical trend queries - "Show API performance over the last week", "Error rate trends"
        PREDICTION: Future prediction queries - "Will API X fail?", "Show upcoming capacity issues"
        SECURITY: Security-focused queries - "Show critical vulnerabilities", "List security violations"
        PERFORMANCE: Performance analysis queries - "Which APIs are slowest?", "Show response time metrics"
        COMPARISON: Comparative queries - "Compare API A vs API B", "Which gateway has most issues?"
        COMPLIANCE: Compliance-related queries - "Show HIPAA violations", "List compliance issues"
        GENERAL: General information queries - "How many APIs?", "What gateways are connected?"
    """

    STATUS = "status"
    TREND = "trend"
    PREDICTION = "prediction"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPARISON = "comparison"
    COMPLIANCE = "compliance"
    GENERAL = "general"


class UserFeedback(str, Enum):
    """User feedback on query results quality.
    
    Captures user satisfaction with query results to improve natural language
    understanding and response generation over time.
    
    Attributes:
        HELPFUL: Query results fully answered the user's question and were accurate.
        NOT_HELPFUL: Query results did not answer the question or were incorrect.
        PARTIALLY_HELPFUL: Query results were somewhat relevant but incomplete or
                          partially inaccurate.
    """

    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    PARTIALLY_HELPFUL = "partially_helpful"


class TimeRange(BaseModel):
    """Time range filter for temporal queries.
    
    Defines a time window for filtering query results, enabling historical
    analysis and trend queries.
    
    Attributes:
        start: Start of the time range (inclusive) in UTC.
        end: End of the time range (inclusive) in UTC. Must be after start.
    """

    start: datetime = Field(
        ...,
        description="Start of the time range (inclusive) in UTC."
    )
    end: datetime = Field(
        ...,
        description="End of the time range (inclusive) in UTC. Must be after start."
    )


class InterpretedIntent(BaseModel):
    """Parsed intent from natural language query.
    
    Represents the structured interpretation of a user's natural language query,
    breaking it down into actionable components for data retrieval.
    
    Attributes:
        action: The primary action to perform. Common values: 'list', 'show', 'compare',
               'count', 'analyze', 'find', 'summarize'.
        entities: List of entity types involved in the query (e.g., ['api', 'vulnerability'],
                 ['gateway', 'metrics'], ['prediction']). Determines which data sources to query.
        filters: Dictionary of filter conditions extracted from the query (e.g.,
                {'severity': 'critical', 'status': 'open'}). Keys are field names,
                values are filter values.
        time_range: Optional time range filter for temporal queries. Extracted from
                   phrases like "in the last week", "since yesterday", "between X and Y".
    """

    action: str = Field(
        ...,
        description="The primary action to perform. Common values: 'list', 'show', 'compare', 'count', 'analyze', 'find', 'summarize'."
    )
    entities: list[str] = Field(
        ...,
        description="List of entity types involved in the query (e.g., ['api', 'vulnerability'], ['gateway', 'metrics'], ['prediction']). Determines which data sources to query."
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of filter conditions extracted from the query (e.g., {'severity': 'critical', 'status': 'open'}). Keys are field names, values are filter values."
    )
    time_range: Optional[TimeRange] = Field(
        None,
        description="Optional time range filter for temporal queries. Extracted from phrases like 'in the last week', 'since yesterday', 'between X and Y'."
    )


class QueryResults(BaseModel):
    """Query execution results.
    
    Contains the data retrieved from OpenSearch and metadata about the query execution.
    
    Attributes:
        data: List of result documents matching the query. Each document is a dictionary
             containing the fields from the matched entity (API, vulnerability, etc.).
        count: Total number of results returned. May be less than total matches if
              pagination is applied.
        execution_time: Time taken to execute the query in milliseconds, including
                       OpenSearch query time and result processing.
        aggregations: Optional aggregation results for statistical queries (e.g., counts
                     by severity, averages, percentiles). Structure depends on query type.
    """

    data: list[dict[str, Any]] = Field(
        ...,
        description="List of result documents matching the query. Each document is a dictionary containing the fields from the matched entity (API, vulnerability, etc.)."
    )
    count: int = Field(
        ...,
        ge=0,
        description="Total number of results returned. May be less than total matches if pagination is applied."
    )
    execution_time: int = Field(
        ...,
        ge=0,
        description="Time taken to execute the query in milliseconds, including OpenSearch query time and result processing."
    )
    aggregations: Optional[dict[str, Any]] = Field(
        None,
        description="Optional aggregation results for statistical queries (e.g., counts by severity, averages, percentiles). Structure depends on query type."
    )


class Query(BaseModel):
    """Query entity representing a natural language query.

    Extended for agentic query service (Feature: 001-agentic-query) to include
    agent decisions, tool invocations, and execution mode metadata.

    Attributes:
        id: Unique identifier (UUID v4)
        session_id: Conversation session (UUID v4)
        user_id: User identifier (1-255 characters)
        query_text: Original query (1-5000 characters)
        query_type: Classified query type
        interpreted_intent: Parsed intent
        opensearch_query: Generated query DSL
        results: Query results
        response_text: Natural language response (1-10000 characters)
        confidence_score: Intent confidence (0-1)
        execution_time_ms: Query execution time (non-negative)
        feedback: User feedback
        feedback_comment: Feedback details (max 1000 characters)
        follow_up_queries: Suggested follow-ups (max 5)
        metadata: Additional data
        created_at: Query timestamp
        
        # Agentic query fields (Feature: 001-agentic-query)
        execution_mode: Execution mode (agentic or fallback)
        agent_decisions: List of agent decisions made
        tool_invocations: List of tool invocations
        fallback_reason: Reason for fallback (if mode=fallback)
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    session_id: UUID = Field(..., description="Conversation session")
    user_id: Optional[str] = Field(
        None, min_length=1, max_length=255, description="User identifier"
    )
    query_text: str = Field(
        ..., min_length=1, max_length=5000, description="Original query"
    )
    query_type: QueryType = Field(..., description="Classified query type")
    interpreted_intent: InterpretedIntent = Field(..., description="Parsed intent")
    opensearch_query: Optional[dict[str, Any]] = Field(
        None, description="Generated query DSL"
    )
    results: QueryResults = Field(..., description="Query results")
    response_text: str = Field(
        ..., min_length=1, max_length=10000, description="Natural language response"
    )
    confidence_score: float = Field(..., ge=0, le=1, description="Intent confidence (0-1)")
    execution_time_ms: int = Field(..., ge=0, description="Query execution time")
    feedback: Optional[UserFeedback] = Field(None, description="User feedback")
    feedback_comment: Optional[str] = Field(
        None, max_length=1000, description="Feedback details"
    )
    follow_up_queries: Optional[list[str]] = Field(
        None, max_length=5, description="Suggested follow-ups"
    )
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional data")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Query timestamp"
    )
    
    # Agentic query fields (Feature: 001-agentic-query)
    execution_mode: Optional[ExecutionMode] = Field(
        None,
        description="Execution mode: agentic (using agents) or fallback (using OpenSearch)"
    )
    agent_decisions: Optional[List[AgentDecision]] = Field(
        None,
        description="List of agent decisions made during query processing"
    )
    tool_invocations: Optional[List[ToolInvocation]] = Field(
        None,
        description="List of tool invocations performed by agents"
    )
    fallback_reason: Optional[FallbackReason] = Field(
        None,
        description="Reason for fallback to OpenSearch (only if execution_mode=fallback)"
    )

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        """Validate query_text is not empty."""
        if not v.strip():
            raise ValueError("query_text must not be empty")
        return v

    @field_validator("follow_up_queries")
    @classmethod
    def validate_follow_up_queries(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate follow_up_queries max 5 items."""
        if v and len(v) > 5:
            raise ValueError("follow_up_queries can have maximum 5 items")
        return v

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: Optional[UserFeedback], info) -> Optional[UserFeedback]:
        """Validate if feedback is set, query must have been executed."""
        if v is not None and "results" not in info.data:
            raise ValueError("feedback can only be set if query has been executed")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440007",
                "session_id": "550e8400-e29b-41d4-a716-446655440008",
                "user_id": "user123",
                "query_text": "Show me all critical vulnerabilities in the last week",
                "query_type": "security",
                "interpreted_intent": {
                    "action": "list",
                    "entities": ["vulnerability"],
                    "filters": {
                        "severity": "critical",
                        "status": "open",
                    },
                    "time_range": {
                        "start": "2026-03-02T00:00:00Z",
                        "end": "2026-03-09T23:59:59Z",
                    },
                },
                "opensearch_query": {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"severity": "critical"}},
                                {"term": {"status": "open"}},
                                {
                                    "range": {
                                        "detected_at": {
                                            "gte": "2026-03-02T00:00:00Z",
                                            "lte": "2026-03-09T23:59:59Z",
                                        }
                                    }
                                },
                            ]
                        }
                    }
                },
                "results": {
                    "data": [
                        {
                            "id": "vuln-001",
                            "title": "SQL Injection",
                            "severity": "critical",
                        }
                    ],
                    "count": 1,
                    "execution_time": 245,
                },
                "response_text": "I found 1 critical vulnerability in the last week: SQL Injection vulnerability detected in the User API.",
                "confidence_score": 0.95,
                "execution_time_ms": 245,
                "follow_up_queries": [
                    "Show me the remediation status",
                    "What APIs are affected?",
                    "Show vulnerability trends",
                ],
            }
        }


class ExecutionStrategy(str, Enum):
    """Query execution strategy.
    
    Determines how a multi-index query should be executed.
    
    Attributes:
        SINGLE_INDEX: Query targets a single index
        SEQUENTIAL: Execute queries sequentially with result filtering
        PARALLEL: Execute queries in parallel and merge results
        NESTED: Use nested queries for complex relationships
    """
    
    SINGLE_INDEX = "single_index"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    NESTED = "nested"


class IndexQuery(BaseModel):
    """Query plan for a single index.
    
    Attributes:
        index: Target index name
        query_dsl: OpenSearch query DSL
        filters: Additional filters to apply
        required_fields: Fields needed from this index
        join_fields: Fields used for joining with other indices
        depends_on: List of index queries this depends on
    """
    
    index: str = Field(..., description="Target index name")
    query_dsl: Dict[str, Any] = Field(..., description="OpenSearch query DSL")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")
    required_fields: List[str] = Field(default_factory=list, description="Required fields")
    join_fields: Dict[str, str] = Field(
        default_factory=dict,
        description="Join fields mapping (source_field: target_field)"
    )
    depends_on: List[str] = Field(
        default_factory=list,
        description="Indices this query depends on"
    )


class QueryPlan(BaseModel):
    """Execution plan for a multi-index query.
    
    Represents the complete execution strategy for a natural language query
    that may span multiple OpenSearch indices with relationships.
    
    Attributes:
        query_id: Unique identifier for this query plan
        session_id: Session this plan belongs to
        original_query: Original natural language query text
        interpreted_intent: Parsed intent from the query
        strategy: Execution strategy to use
        index_queries: List of index queries in execution order
        estimated_cost: Estimated execution cost (0-1, higher = more expensive)
        requires_join: Whether results need to be joined
        join_strategy: Strategy for joining results if needed
        context_filters: Filters from session context
        created_at: When this plan was created
    """
    
    query_id: UUID = Field(default_factory=uuid4, description="Unique query plan identifier")
    session_id: UUID = Field(..., description="Session identifier")
    original_query: str = Field(..., description="Original natural language query")
    interpreted_intent: InterpretedIntent = Field(..., description="Parsed intent")
    strategy: ExecutionStrategy = Field(..., description="Execution strategy")
    index_queries: List[IndexQuery] = Field(..., description="Index queries in execution order")
    estimated_cost: float = Field(
        ...,
        ge=0,
        le=1,
        description="Estimated execution cost (0-1)"
    )
    requires_join: bool = Field(default=False, description="Whether join is required")
    join_strategy: Optional[str] = Field(None, description="Join strategy if needed")
    context_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters from session context"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    class Config:
        """Pydantic model configuration."""
        
        json_schema_extra = {
            "example": {
                "query_id": "550e8400-e29b-41d4-a716-446655440009",
                "session_id": "550e8400-e29b-41d4-a716-446655440008",
                "original_query": "Show me APIs with critical vulnerabilities",
                "interpreted_intent": {
                    "action": "list",
                    "entities": ["api", "vulnerability"],
                    "filters": {"severity": "critical"},
                    "time_range": None
                },
                "strategy": "sequential",
                "index_queries": [
                    {
                        "index": "security-findings",
                        "query_dsl": {
                            "query": {
                                "bool": {
                                    "must": [{"term": {"severity": "critical"}}]
                                }
                            }
                        },
                        "filters": {"severity": "critical"},
                        "required_fields": ["api_id", "gateway_id", "title"],
                        "join_fields": {"api_id": "id", "gateway_id": "gateway_id"},
                        "depends_on": []
                    },
                    {
                        "index": "api-inventory",
                        "query_dsl": {
                            "query": {
                                "bool": {
                                    "must": [{"terms": {"id": ["API-001", "API-002"]}}]
                                }
                            }
                        },
                        "filters": {},
                        "required_fields": ["id", "name", "base_path", "status"],
                        "join_fields": {},
                        "depends_on": ["security-findings"]
                    }
                ],
                "estimated_cost": 0.6,
                "requires_join": True,
                "join_strategy": "api_id",
                "context_filters": {},
                "created_at": "2026-04-21T07:00:00Z"
            }
        }


# Made with Bob
