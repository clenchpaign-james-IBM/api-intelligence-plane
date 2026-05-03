# Data Model: Agentic Natural Language Query Service

**Feature**: 002-agentic-query | **Date**: 2026-05-02

## Overview

This document defines the data entities, relationships, and state management for the agentic query service with iterative coordinator reasoning and LLM-powered synthesis.

## Core Entities

### 1. CoordinatorState

**Purpose**: Tracks the coordinator's iterative reasoning state across multiple iterations.

**Fields**:
```python
class CoordinatorState(BaseModel):
    """State management for iterative coordinator reasoning."""
    
    # Iteration tracking
    iteration: int = 0
    max_iterations: int = 10
    
    # Query context
    query: str
    session_id: Optional[str] = None
    
    # Execution state
    intermediate_results: Dict[str, Any] = {}  # agent_name -> result
    completed_steps: List[str] = []  # Human-readable step descriptions
    next_actions: List[str] = []  # Planned next actions
    
    # Completion tracking
    is_complete: bool = False
    completion_reasoning: str = ""
    completion_confidence: float = 0.0
    
    # Metadata
    started_at: datetime
    last_updated: datetime
    total_execution_time_ms: int = 0
```

**Relationships**:
- Contains multiple `AgentDecision` records (one per iteration)
- References `QueryContext` via session_id
- Produces final `EntityGrouping` when complete

**State Transitions**:
```
INITIALIZED → ITERATING → COMPLETE
            ↓
            FAILED (max iterations or timeout)
```

**Validation Rules**:
- `iteration` must be ≤ `max_iterations`
- `is_complete` can only be True if `completion_reasoning` is provided
- `intermediate_results` keys must match registered agent names

---

### 2. AgentDecision

**Purpose**: Records a single agent's reasoning, tool selection, and execution results.

**Fields**:
```python
class AgentDecision(BaseModel):
    """Records agent reasoning and tool selection."""
    
    # Agent identification
    agent_type: AgentType  # DISCOVERY, METRICS, SECURITY, etc.
    agent_name: str
    
    # Decision metadata
    query: str  # Sub-query for this agent
    reasoning: str  # Why this agent was selected
    confidence: float  # 0.0 to 1.0
    
    # Tool selection
    selected_tools: List[str]  # Tool names
    tool_selection_reasoning: str
    
    # Execution results
    tool_invocations: List[ToolInvocation] = []
    synthesis_result: Optional[EntityGrouping] = None
    
    # Performance
    execution_time_ms: int
    started_at: datetime
    completed_at: datetime
    
    # Status
    success: bool
    error_message: Optional[str] = None
```

**Relationships**:
- Contains multiple `ToolInvocation` records
- Produces one `EntityGrouping` via synthesis
- Referenced by `CoordinatorState.intermediate_results`

**Validation Rules**:
- `confidence` must be between 0.0 and 1.0
- `success=False` requires `error_message`
- `synthesis_result` required if `success=True`

---

### 3. ToolInvocation

**Purpose**: Represents a single MCP tool call with parameters, results, and execution metadata.

**Fields**:
```python
class ToolInvocation(BaseModel):
    """Records a single tool invocation."""
    
    # Tool identification
    tool_name: str
    tool_domain: str  # "discovery", "security", etc.
    
    # Invocation details
    parameters: Dict[str, Any]
    parameter_validation: bool  # Pydantic validation passed
    
    # Results
    result: Optional[Dict[str, Any]] = None
    result_count: int = 0  # Number of entities returned
    
    # Execution metadata
    started_at: datetime
    completed_at: datetime
    execution_time_ms: int
    
    # Status
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Caching
    cache_hit: bool = False
    cache_key: Optional[str] = None
```

**Relationships**:
- Belongs to one `AgentDecision`
- Results feed into `EntityGrouping` synthesis

**Validation Rules**:
- `success=False` requires `error_message`
- `retry_count` must be ≤ 3
- `result_count` must match actual entities in `result`

---

### 4. EntityGrouping

**Purpose**: Represents aggregated and synthesized results grouped by entity type.

**Fields**:
```python
class EntityGrouping(BaseModel):
    """LLM-synthesized entity grouping."""
    
    # Entity information
    entity_type: str  # "api", "gateway", "vulnerability", etc.
    entities: Dict[str, Dict[str, Any]]  # entity_id -> entity_data
    total_count: int
    
    # Synthesis
    synthesis_summary: str  # Natural language summary
    synthesis_reasoning: str  # How entities were grouped
    confidence: float  # Synthesis confidence (0.0-1.0)
    
    # Relationships
    related_entities: Dict[str, List[str]] = {}  # entity_type -> [entity_ids]
    # Example: {"vulnerabilities": ["vuln-1", "vuln-2"]} for an API entity
    
    # Metadata
    source_tool_calls: List[str]  # Tool names that produced this data
    synthesized_at: datetime
    synthesis_time_ms: int
```

**Relationships**:
- Produced by one `AgentDecision`
- Can reference other `EntityGrouping` via `related_entities`
- Consumed by coordinator for final response synthesis

**Entity Relationship Patterns**:
```python
# Example 1: Vulnerabilities grouped by affected APIs
EntityGrouping(
    entity_type="api",
    entities={
        "api-1": {"name": "Payment API", "vulnerability_count": 15},
        "api-2": {"name": "User API", "vulnerability_count": 25}
    },
    total_count=2,
    synthesis_summary="Found 2 APIs with 40 total vulnerabilities",
    related_entities={
        "vulnerabilities": ["vuln-1", "vuln-2", ..., "vuln-40"]
    }
)

# Example 2: APIs grouped by gateway
EntityGrouping(
    entity_type="api",
    entities={
        "api-1": {"name": "Payment API", "gateway_id": "gw-local"},
        "api-2": {"name": "User API", "gateway_id": "gw-local"}
    },
    total_count=2,
    synthesis_summary="Found 2 APIs managed by gateway 'local'",
    related_entities={
        "gateways": ["gw-local"]
    }
)
```

**Validation Rules**:
- `total_count` must equal `len(entities)`
- `confidence` must be between 0.0 and 1.0
- `synthesis_summary` must be non-empty
- `related_entities` keys must be valid entity types

---

### 5. QueryContext

**Purpose**: Maintains conversational state across multiple query turns within a session.

**Fields**:
```python
class QueryContext(BaseModel):
    """Session context for multi-turn conversations."""
    
    # Session identification
    session_id: str
    user_id: Optional[str] = None
    
    # Query history
    query_history: List[str] = []  # Max 10 queries
    query_timestamps: List[datetime] = []
    
    # Entity tracking
    entity_mentions: Dict[str, List[str]] = {}  # entity_type -> [entity_ids]
    # Example: {"apis": ["api-1", "api-2"], "gateways": ["gw-local"]}
    
    # Reference resolution
    resolved_references: Dict[str, str] = {}  # reference -> resolved_entity
    # Example: {"those": "apis_from_query_1", "them": "vulnerabilities_from_query_2"}
    
    # Last query results
    last_query_results: Dict[str, Any] = {}
    last_entity_grouping: Optional[EntityGrouping] = None
    
    # Session metadata
    created_at: datetime
    last_accessed: datetime
    ttl_seconds: int = 3600  # 1 hour
    
    # Statistics
    total_queries: int = 0
    fallback_count: int = 0
```

**Relationships**:
- Referenced by `CoordinatorState` via session_id
- Contains historical `EntityGrouping` references
- Tracks entities across multiple queries

**State Transitions**:
```
CREATED → ACTIVE → EXPIRED
        ↓
        INACTIVE (no access for TTL duration)
```

**Validation Rules**:
- `query_history` max length: 10
- `session_id` must be unique
- `last_accessed` must be updated on each query
- Session expires if `datetime.utcnow() - last_accessed > ttl_seconds`

---

### 6. FallbackTrigger

**Purpose**: Records when and why the system fell back to OpenSearch approach.

**Fields**:
```python
class FallbackReason(str, Enum):
    """Reasons for fallback to OpenSearch."""
    LOW_CONFIDENCE = "low_confidence"
    TOOL_FAILURE = "tool_failure"
    TIMEOUT = "timeout"
    NO_TOOLS_FOUND = "no_tools_found"
    LLM_UNAVAILABLE = "llm_unavailable"
    MAX_ITERATIONS = "max_iterations"
    PARSING_ERROR = "parsing_error"

class FallbackTrigger(BaseModel):
    """Records fallback event for observability."""
    
    # Trigger information
    reason: FallbackReason
    reasoning: str  # Detailed explanation
    
    # Metrics that triggered fallback
    confidence_score: Optional[float] = None
    tool_failure_rate: Optional[float] = None
    execution_time_ms: Optional[int] = None
    iteration_count: Optional[int] = None
    
    # Query context
    query_text: str
    session_id: Optional[str] = None
    
    # Fallback execution
    opensearch_query: Optional[str] = None
    opensearch_success: bool = False
    opensearch_execution_time_ms: Optional[int] = None
    
    # Metadata
    timestamp: datetime
    agent_type: Optional[AgentType] = None
```

**Relationships**:
- Referenced by query response metadata
- Aggregated for fallback rate monitoring
- Used for threshold tuning

**Validation Rules**:
- `reason` must be valid `FallbackReason` enum value
- Reason-specific fields must be populated:
  - `LOW_CONFIDENCE` requires `confidence_score`
  - `TOOL_FAILURE` requires `tool_failure_rate`
  - `TIMEOUT` requires `execution_time_ms`
  - `MAX_ITERATIONS` requires `iteration_count`

---

## Supporting Enums

### AgentType
```python
class AgentType(str, Enum):
    """Types of specialized agents."""
    DISCOVERY = "discovery"
    METRICS = "metrics"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPTIMIZATION = "optimization"
    PREDICTION = "prediction"
```

### ExecutionMode
```python
class ExecutionMode(str, Enum):
    """Query execution mode."""
    AGENTIC = "agentic"  # Full agentic workflow
    FALLBACK = "fallback"  # OpenSearch fallback
    HYBRID = "hybrid"  # Partial agentic + fallback
```

---

## Entity Relationships Diagram

```
QueryContext (session)
    ↓ references
CoordinatorState (iteration state)
    ↓ contains
AgentDecision (per agent invocation)
    ↓ contains
ToolInvocation (per tool call)
    ↓ produces
EntityGrouping (synthesized results)
    ↓ references
Related EntityGrouping (cross-entity relationships)

FallbackTrigger (observability)
    ← triggered by
CoordinatorState or AgentDecision
```

---

## Data Flow Example

### Multi-Step Query: "Show insecure APIs managed by gateway 'local'"

**Step 1: Initialize Coordinator State**
```python
state = CoordinatorState(
    query="Show insecure APIs managed by gateway 'local'",
    session_id="session-123",
    iteration=0,
    max_iterations=10,
    started_at=datetime.utcnow()
)
```

**Step 2: Iteration 1 - Resolve Gateway Name**
```python
# LLM decides: Need to resolve gateway name first
decision_1 = AgentDecision(
    agent_type=AgentType.DISCOVERY,
    query="Get gateway with name 'local'",
    reasoning="Need gateway ID to query APIs",
    confidence=0.95,
    selected_tools=["list_gateways"],
    tool_invocations=[
        ToolInvocation(
            tool_name="list_gateways",
            parameters={"name_filter": "local"},
            result={"gateways": [{"id": "gw-123", "name": "local"}]},
            success=True
        )
    ],
    synthesis_result=EntityGrouping(
        entity_type="gateway",
        entities={"gw-123": {"name": "local"}},
        total_count=1,
        synthesis_summary="Found gateway 'local' with ID gw-123"
    )
)

state.intermediate_results["discovery_1"] = decision_1
state.completed_steps.append("Resolved gateway 'local' to gw-123")
state.iteration = 1
```

**Step 3: LLM Evaluates Completion**
```python
# LLM: Not complete, need to fetch vulnerabilities for this gateway
state.is_complete = False
state.completion_reasoning = "Need to fetch vulnerabilities for gateway gw-123"
```

**Step 4: Iteration 2 - Fetch Vulnerabilities**
```python
decision_2 = AgentDecision(
    agent_type=AgentType.SECURITY,
    query="Get vulnerabilities for gateway gw-123",
    reasoning="Need security data for APIs in this gateway",
    confidence=0.92,
    selected_tools=["list_vulnerabilities"],
    tool_invocations=[
        ToolInvocation(
            tool_name="list_vulnerabilities",
            parameters={"gateway_id": "gw-123"},
            result={"vulnerabilities": [...]},  # 40 vulnerabilities
            success=True
        )
    ],
    synthesis_result=EntityGrouping(
        entity_type="api",
        entities={
            "api-1": {"name": "Payment API", "vulnerability_count": 15},
            "api-2": {"name": "User API", "vulnerability_count": 25}
        },
        total_count=2,
        synthesis_summary="Found 2 insecure APIs with 40 total vulnerabilities",
        related_entities={
            "gateways": ["gw-123"],
            "vulnerabilities": ["vuln-1", ..., "vuln-40"]
        }
    )
)

state.intermediate_results["security_1"] = decision_2
state.completed_steps.append("Found 2 insecure APIs in gateway gw-123")
state.iteration = 2
```

**Step 5: LLM Evaluates Completion**
```python
# LLM: Complete! We have the insecure APIs for the specified gateway
state.is_complete = True
state.completion_reasoning = "Successfully identified insecure APIs managed by gateway 'local'"
state.completion_confidence = 0.95
```

**Step 6: Update Context**
```python
context = QueryContext(
    session_id="session-123",
    query_history=["Show insecure APIs managed by gateway 'local'"],
    entity_mentions={
        "gateways": ["gw-123"],
        "apis": ["api-1", "api-2"],
        "vulnerabilities": ["vuln-1", ..., "vuln-40"]
    },
    last_entity_grouping=decision_2.synthesis_result
)
```

---

## Storage & Persistence

### In-Memory (Runtime)
- `CoordinatorState`: Active workflow state
- `QueryContext`: Session contexts (1-hour TTL)
- LLM response cache (5-minute TTL)
- Tool result cache (60-second TTL)

### OpenSearch (Persistent)
- Query history (for analytics)
- `FallbackTrigger` records (for monitoring)
- Agent decision logs (for observability)
- Performance metrics (for optimization)

### Not Persisted
- Intermediate `AgentDecision` objects (logged but not stored)
- `ToolInvocation` details (logged but not stored)
- `EntityGrouping` objects (regenerated on each query)

---

## Validation & Constraints

### Global Constraints
- All timestamps in UTC
- All confidence scores: 0.0 ≤ confidence ≤ 1.0
- All execution times in milliseconds
- All entity IDs must be non-empty strings

### Performance Constraints
- `CoordinatorState.iteration` ≤ 10
- `QueryContext.query_history` ≤ 10 entries
- `AgentDecision.tool_invocations` ≤ 20 per agent
- `EntityGrouping.entities` ≤ 1000 per grouping

### Business Rules
- Fallback triggers when confidence < 0.6
- Session expires after 1 hour of inactivity
- Tool invocations retry max 3 times
- Coordinator timeout at 10 seconds

---

## Migration Notes

### Existing Models (No Changes)
- `Query`: Existing query model (backward compatible)
- `QueryResults`: Existing results model (extended with agentic metadata)
- `InterpretedIntent`: Existing intent model (still used for fallback)

### New Models (This Feature)
- `CoordinatorState`: New
- `AgentDecision`: New
- `ToolInvocation`: New
- `EntityGrouping`: New
- `FallbackTrigger`: Enhanced from existing

### Backward Compatibility
- All new fields are optional in API responses
- Existing clients ignore new agentic metadata
- Fallback mode returns same format as before