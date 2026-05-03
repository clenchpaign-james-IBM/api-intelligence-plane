"""
Agentic Query Service - Agent Data Models

This module defines all data models for the agentic query service including
agent decisions, tool invocations, query context, and fallback triggers.

Feature: 001-agentic-query
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums (T006-T008)
# ============================================================================


class AgentType(str, Enum):
    """Valid agent types for the agentic query service."""

    COORDINATOR = "coordinator"
    DISCOVERY = "discovery"
    METRICS = "metrics"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPTIMIZATION = "optimization"
    PREDICTION = "prediction"


class ExecutionMode(str, Enum):
    """Query execution modes."""

    AGENTIC = "agentic"  # Using agentic workflow
    FALLBACK = "fallback"  # Fell back to OpenSearch


class FallbackReason(str, Enum):
    """Reasons for fallback to OpenSearch."""

    LOW_CONFIDENCE = "low_confidence"  # Agent confidence < threshold
    TOOL_FAILURES = "tool_failures"  # Too many tool invocation failures
    TIMEOUT = "timeout"  # Workflow exceeded time limit
    NO_TOOLS_FOUND = "no_tools_found"  # No appropriate tools identified
    LLM_UNAVAILABLE = "llm_unavailable"  # LLM service error


# ============================================================================
# Core Data Models (T007-T012 for Feature 002-agentic-query)
# ============================================================================


class CoordinatorState(BaseModel):
    """
    Tracks the coordinator's iterative reasoning state across multiple iterations.
    
    Feature: 002-agentic-query (Iterative Multi-Step Coordinator Reasoning)
    """
    
    # Iteration tracking
    iteration: int = Field(default=0, ge=0, description="Current iteration number")
    max_iterations: int = Field(default=10, ge=1, le=20, description="Maximum allowed iterations")
    
    # Query context
    query: str = Field(description="Original user query")
    session_id: Optional[UUID] = Field(default=None, description="Session identifier")
    
    # Execution state
    intermediate_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results from each agent invocation (agent_name -> result)"
    )
    completed_steps: List[str] = Field(
        default_factory=list,
        description="Human-readable descriptions of completed steps"
    )
    next_actions: List[str] = Field(
        default_factory=list,
        description="Planned next actions"
    )
    
    # Completion tracking
    is_complete: bool = Field(default=False, description="Whether query is fully answered")
    completion_reasoning: str = Field(default="", description="LLM reasoning for completion decision")
    completion_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in completion decision"
    )
    
    # Metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    total_execution_time_ms: int = Field(default=0, ge=0, description="Total execution time")
    
    @field_validator("iteration")
    @classmethod
    def validate_iteration(cls, v: int, info) -> int:
        """Validate iteration doesn't exceed max_iterations."""
        max_iter = info.data.get("max_iterations", 10)
        if v > max_iter:
            raise ValueError(f"iteration ({v}) cannot exceed max_iterations ({max_iter})")
        return v
    
    @field_validator("completion_reasoning")
    @classmethod
    def validate_completion_reasoning(cls, v: str, info) -> str:
        """Validate completion_reasoning is provided when is_complete=True."""
        is_complete = info.data.get("is_complete", False)
        if is_complete and not v:
            raise ValueError("completion_reasoning required when is_complete=True")
        return v


class EntityGrouping(BaseModel):
    """
    Represents aggregated and synthesized results grouped by entity type.
    
    Feature: 002-agentic-query (LLM-Powered Synthesis & Entity Grouping)
    """
    
    # Entity information
    entity_type: str = Field(description="Type of entity (api, gateway, vulnerability, etc.)")
    entities: Dict[str, Dict[str, Any]] = Field(
        description="Entities grouped by ID (entity_id -> entity_data)"
    )
    total_count: int = Field(ge=0, description="Total number of entities")
    
    # Synthesis
    synthesis_summary: str = Field(description="Natural language summary of grouped entities")
    synthesis_reasoning: str = Field(description="How entities were grouped")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Synthesis confidence (0.0-1.0)"
    )
    
    # Relationships
    related_entities: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Related entities by type (entity_type -> [entity_ids])"
    )
    
    # Metadata
    source_tool_calls: List[str] = Field(
        default_factory=list,
        description="Tool names that produced this data"
    )
    synthesized_at: datetime = Field(default_factory=datetime.utcnow)
    synthesis_time_ms: int = Field(ge=0, description="Time taken for synthesis")
    
    @field_validator("total_count")
    @classmethod
    def validate_total_count(cls, v: int, info) -> int:
        """Validate total_count matches entities length."""
        entities = info.data.get("entities", {})
        if v != len(entities):
            raise ValueError(f"total_count ({v}) must equal len(entities) ({len(entities)})")
        return v
    
    @field_validator("synthesis_summary")
    @classmethod
    def validate_synthesis_summary(cls, v: str) -> str:
        """Validate synthesis_summary is not empty."""
        if not v.strip():
            raise ValueError("synthesis_summary must not be empty")
        return v


# ============================================================================
# Legacy Core Data Models (from Feature 001-agentic-query)
# ============================================================================


class AgentDecision(BaseModel):
    """
    Represents a decision made by an agent during query processing.

    An agent decision captures the reasoning process, tool selection,
    and confidence level for a specific query or sub-query.
    """

    decision_id: UUID = Field(default_factory=uuid4)
    agent_type: AgentType
    query_text: str
    reasoning: str = Field(
        description="LLM-generated reasoning for the decision"
    )
    selected_tools: List[str] = Field(
        default_factory=list,
        description="Names of tools selected for invocation"
    )
    tool_parameters: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Parameters for each selected tool"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the decision (0.0-1.0)"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: int = Field(
        gt=0,
        description="Time taken to make the decision (milliseconds)"
    )
    context_used: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context information used in decision"
    )

    @field_validator("selected_tools")
    @classmethod
    def validate_tools(cls, v: List[str], info) -> List[str]:
        """Validate that tools are selected when confidence is high."""
        confidence = info.data.get("confidence_score", 0)
        if confidence > 0.5 and not v:
            raise ValueError(
                "selected_tools cannot be empty with confidence > 0.5"
            )
        return v


class ToolInvocation(BaseModel):
    """
    Represents an invocation of a router tool by an agent.

    Captures the complete lifecycle of a tool invocation including
    parameters, results, success status, and execution time.
    """

    invocation_id: UUID = Field(default_factory=uuid4)
    tool_name: str
    agent_type: AgentType
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters passed to the tool"
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Tool execution result (None if failed)"
    )
    success: bool
    error: Optional[str] = Field(
        default=None,
        description="Error message if invocation failed"
    )
    execution_time_ms: int = Field(
        gt=0,
        description="Tool execution time (milliseconds)"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = Field(
        ge=0,
        default=0,
        description="Number of retries attempted"
    )

    @field_validator("result")
    @classmethod
    def validate_result(cls, v: Optional[Dict[str, Any]], info) -> Optional[Dict[str, Any]]:
        """Validate result consistency with success status."""
        success = info.data.get("success")
        if success and v is None:
            raise ValueError("result must not be None if success is True")
        if not success and v is not None:
            raise ValueError("result must be None if success is False")
        return v


class QueryContext(BaseModel):
    """
    Maintains conversational state for a query session.

    Tracks query history, entity mentions, and resolved references
    to enable context-aware follow-up queries.
    """

    session_id: UUID
    query_history: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="Previous queries in this session (max 10)"
    )
    entity_mentions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Entities mentioned in conversation by type"
    )
    resolved_references: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resolved references from previous queries"
    )
    last_query_results: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Results from the last query"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last context update timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context metadata"
    )

    def add_query(self, query_text: str) -> None:
        """Add query to history, maintaining max 10 entries."""
        self.query_history.append(query_text)
        if len(self.query_history) > 10:
            self.query_history.pop(0)
        self.last_updated = datetime.utcnow()

    def add_entity_mention(self, entity_type: str, entity_id: str) -> None:
        """Track entity mention in conversation."""
        if entity_type not in self.entity_mentions:
            self.entity_mentions[entity_type] = []
        if entity_id not in self.entity_mentions[entity_type]:
            self.entity_mentions[entity_type].append(entity_id)
        self.last_updated = datetime.utcnow()

    def resolve_reference(self, reference: str) -> Optional[Any]:
        """Resolve pronoun or reference to entity."""
        return self.resolved_references.get(reference)

    def update_results(self, results: Dict[str, Any]) -> None:
        """Update last query results for context."""
        self.last_query_results = results
        self.last_updated = datetime.utcnow()


class AgenticQueryResult(BaseModel):
    """
    Complete result of an agentic query workflow.

    Encapsulates all agent decisions, tool invocations, and the
    final response for a query execution.
    """

    query_id: UUID = Field(default_factory=uuid4)
    query_text: str
    session_id: UUID
    mode: ExecutionMode
    agent_decisions: List[AgentDecision] = Field(
        default_factory=list,
        description="All agent decisions made"
    )
    tool_invocations: List[ToolInvocation] = Field(
        default_factory=list,
        description="All tool invocations"
    )
    response_text: str = Field(
        description="Natural language response"
    )
    results: Dict[str, Any] = Field(
        description="Structured query results"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence (0.0-1.0)"
    )
    fallback_reason: Optional[FallbackReason] = Field(
        default=None,
        description="Why fallback was triggered (if mode=fallback)"
    )
    execution_time_ms: int = Field(
        gt=0,
        description="Total execution time"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    follow_up_queries: Optional[List[str]] = Field(
        default=None,
        description="Suggested follow-up queries"
    )

    @field_validator("fallback_reason")
    @classmethod
    def validate_fallback(
        cls,
        v: Optional[FallbackReason],
        info
    ) -> Optional[FallbackReason]:
        """Validate fallback reason consistency with mode."""
        mode = info.data.get("mode")
        if mode == ExecutionMode.AGENTIC and v is not None:
            raise ValueError(
                "fallback_reason must be None for agentic mode"
            )
        if mode == ExecutionMode.FALLBACK and v is None:
            raise ValueError(
                "fallback_reason required for fallback mode"
            )
        return v

    @field_validator("agent_decisions")
    @classmethod
    def validate_decisions(
        cls,
        v: List[AgentDecision],
        info
    ) -> List[AgentDecision]:
        """Validate agent decisions exist for agentic mode."""
        mode = info.data.get("mode")
        if mode == ExecutionMode.AGENTIC and not v:
            raise ValueError(
                "agent_decisions cannot be empty for agentic mode"
            )
        return v


class FallbackTrigger(BaseModel):
    """
    Records when and why the system fell back to OpenSearch.

    Used for monitoring, analytics, and improving the agentic
    workflow over time.
    """

    trigger_id: UUID = Field(default_factory=uuid4)
    query_id: UUID
    session_id: UUID
    reason: FallbackReason
    agent_state: Dict[str, Any] = Field(
        description="Agent state at fallback time"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score at fallback time"
    )
    elapsed_time_ms: int = Field(
        gt=0,
        description="Time elapsed before fallback"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional fallback metadata"
    )

# Made with Bob
