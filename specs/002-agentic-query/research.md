# Research: Agentic Natural Language Query Service

**Feature**: 002-agentic-query | **Date**: 2026-05-02

## Overview

This document consolidates research findings for implementing a fully agentic natural language query service with iterative coordinator reasoning, LLM-powered synthesis, and intelligent fallback mechanisms.

## 1. Iterative Reasoning Patterns

### Decision: LangChain Agent Loops with State Management

**Rationale**:
- Industry-standard pattern used by AutoGPT, LangChain agents, and production agentic systems
- Enables dynamic adaptation to intermediate results
- Supports "what do I know?" and "what do I need next?" evaluation after each step
- Provides built-in loop detection and timeout mechanisms

**Implementation Approach**:
```python
class CoordinatorState(BaseModel):
    """Tracks coordinator's iterative reasoning state."""
    iteration: int = 0
    max_iterations: int = 10
    query: str
    intermediate_results: Dict[str, Any] = {}
    completed_steps: List[str] = []
    next_actions: List[str] = []
    is_complete: bool = False
    completion_reasoning: str = ""

async def iterative_reasoning_loop(query: str, context: Dict) -> Dict:
    state = CoordinatorState(query=query)
    
    while not state.is_complete and state.iteration < state.max_iterations:
        # Step 1: LLM evaluates current state and decides next action
        next_action = await llm_decide_next_action(state, context)
        
        # Step 2: Execute action (invoke agent/tool)
        result = await execute_action(next_action)
        
        # Step 3: Update state with intermediate results
        state.intermediate_results[next_action.agent] = result
        state.completed_steps.append(next_action.description)
        state.iteration += 1
        
        # Step 4: LLM evaluates if query is answered
        completion_decision = await llm_evaluate_completion(state, query)
        state.is_complete = completion_decision.is_complete
        state.completion_reasoning = completion_decision.reasoning
    
    return synthesize_final_response(state)
```

**Alternatives Considered**:
- **Upfront Planning**: Simpler but less adaptive to unexpected intermediate results
- **ReAct Pattern**: Similar but requires explicit Reason-Act-Observe structure (more verbose)
- **Hybrid Approach**: Adds complexity without significant benefits for this use case

**Key References**:
- LangChain Agent Documentation: https://python.langchain.com/docs/modules/agents/
- ReAct Paper: https://arxiv.org/abs/2210.03629
- AutoGPT Architecture: https://github.com/Significant-Gravitas/AutoGPT

---

## 2. LLM-Powered Synthesis & Entity Grouping

### Decision: Agent-Level Synthesis with Structured Outputs

**Rationale**:
- Distributes synthesis workload across specialized agents
- Enables domain-specific grouping logic (e.g., security agent knows how to group vulnerabilities by API)
- Provides cleaner interfaces between agents (coordinator receives synthesized results, not raw tool outputs)
- Reduces coordinator complexity by delegating synthesis to domain experts

**Implementation Approach**:
```python
class EntityGrouping(BaseModel):
    """Represents aggregated results grouped by entity."""
    entity_type: str  # "api", "gateway", "vulnerability"
    entities: Dict[str, Dict[str, Any]]  # entity_id -> entity_data
    total_count: int
    synthesis_summary: str  # Natural language summary
    confidence: float

async def synthesize_tool_results(
    tool_results: List[Dict],
    query: str,
    agent_domain: str
) -> EntityGrouping:
    """LLM-powered synthesis of tool results."""
    
    # Prompt LLM to group and synthesize
    synthesis_prompt = f"""
    You are a {agent_domain} agent analyzing tool results.
    
    Query: {query}
    Tool Results: {json.dumps(tool_results, indent=2)}
    
    Group these results by the primary entity type (API, gateway, etc.) and provide:
    1. Entity groupings (e.g., vulnerabilities → affected APIs)
    2. Natural language summary matching user intent
    3. Confidence score (0.0-1.0)
    
    Return JSON with: entity_type, entities (dict), total_count, synthesis_summary, confidence
    """
    
    response = await llm.ainvoke([
        SystemMessage(content="You are an expert at synthesizing data."),
        HumanMessage(content=synthesis_prompt)
    ])
    
    return EntityGrouping(**json.loads(response.content))
```

**Entity Relationship Patterns**:
- Vulnerabilities → APIs (group 40 vulnerabilities into 8 affected APIs)
- APIs → Gateways (group APIs by managing gateway)
- Metrics → APIs (aggregate performance data by API)
- Violations → APIs (group compliance violations by API)
- Recommendations → APIs (group optimization suggestions by API)

**Alternatives Considered**:
- **Coordinator-Level Synthesis**: Creates bottleneck, loses domain-specific knowledge
- **Hardcoded Grouping Rules**: Fragile, requires maintenance for new entity types
- **No Synthesis**: Poor user experience, returns raw tool outputs

**Key References**:
- Pydantic Structured Outputs: https://docs.pydantic.dev/latest/
- LangChain Output Parsers: https://python.langchain.com/docs/modules/model_io/output_parsers/

---

## 3. Completion Criteria & Loop Prevention

### Decision: LLM-Based Completion with Hard Iteration Limit

**Rationale**:
- LLM can evaluate semantic completeness better than rule-based systems
- Prevents infinite loops with hard limit (10 iterations = industry standard)
- Provides explainable completion reasoning for observability
- Balances flexibility (complex queries) with safety (runaway prevention)

**Implementation Approach**:
```python
class CompletionDecision(BaseModel):
    """LLM decision on whether query is answered."""
    is_complete: bool
    confidence: float
    reasoning: str
    missing_information: List[str] = []

async def evaluate_completion(
    state: CoordinatorState,
    original_query: str
) -> CompletionDecision:
    """LLM evaluates if sufficient information gathered."""
    
    prompt = f"""
    Original Query: {original_query}
    
    Completed Steps: {state.completed_steps}
    Intermediate Results: {summarize_results(state.intermediate_results)}
    Current Iteration: {state.iteration}/{state.max_iterations}
    
    Evaluate:
    1. Do we have sufficient information to answer the user's query?
    2. What information is still missing (if any)?
    3. Should we stop iterating or continue?
    
    Return JSON: is_complete (bool), confidence (float), reasoning (str), missing_information (list)
    """
    
    response = await llm.ainvoke([
        SystemMessage(content="You are an expert at evaluating query completeness."),
        HumanMessage(content=prompt)
    ])
    
    return CompletionDecision(**json.loads(response.content))
```

**Loop Prevention Mechanisms**:
1. **Hard Iteration Limit**: Max 10 iterations (typical queries complete in 2-3)
2. **No Progress Detection**: Stop if last iteration produced no new entities/data
3. **Confidence Threshold**: Stop if confidence drops below 0.3 (likely stuck)
4. **Timeout**: Overall workflow timeout of 10 seconds for multi-agent queries

**Alternatives Considered**:
- **Goal-Based Completion**: Requires upfront goal definition (less flexible)
- **Confidence Threshold Only**: Can miss semantic completeness
- **No New Information**: Too conservative, may stop prematurely

**Key References**:
- Agent Loop Best Practices: https://python.langchain.com/docs/modules/agents/how_to/max_iterations
- Production Agent Patterns: https://www.anthropic.com/research/building-effective-agents

---

## 4. Tool Selection & Parameter Validation

### Decision: LLM-Driven Tool Selection with Schema Validation

**Rationale**:
- LLM understands natural language → tool parameter mapping better than regex
- Pydantic schemas provide automatic validation and type safety
- Tool descriptions guide LLM to correct parameter values
- Retry logic handles transient failures

**Implementation Approach**:
```python
class ToolParameter(BaseModel):
    """Validated tool parameter."""
    name: str
    value: Any
    type: str
    validated: bool = False

async def select_and_invoke_tool(
    query: str,
    available_tools: List[BaseTool],
    context: Dict
) -> Dict:
    """LLM selects tool and validates parameters."""
    
    # Step 1: LLM selects tool
    tool_selection = await llm_select_tool(query, available_tools, context)
    
    # Step 2: LLM generates parameters
    parameters = await llm_generate_parameters(
        query, 
        tool_selection.tool,
        tool_selection.tool.args_schema
    )
    
    # Step 3: Validate with Pydantic
    try:
        validated_params = tool_selection.tool.args_schema(**parameters)
    except ValidationError as e:
        # Retry with validation errors as feedback
        parameters = await llm_fix_parameters(query, parameters, str(e))
        validated_params = tool_selection.tool.args_schema(**parameters)
    
    # Step 4: Invoke tool with retry logic
    return await invoke_with_retry(
        tool_selection.tool,
        validated_params,
        max_retries=3
    )
```

**Parameter Interpretation Patterns** (from agent system prompts):
- Severity: "critical" → severity="critical", "severe" → severity="critical"
- Status: "open" → status="open", "unresolved" → status="open"
- Time: "last week" → discovered_after=(7 days ago)
- Comparison: "greater than X" → gt=X or gte=X

**Alternatives Considered**:
- **Keyword Matching**: Fragile, requires maintenance
- **No Validation**: Leads to tool invocation errors
- **Hardcoded Parameter Maps**: Not scalable to new tools

**Key References**:
- LangChain Tool Calling: https://python.langchain.com/docs/modules/agents/agent_types/tool_calling
- Pydantic Validation: https://docs.pydantic.dev/latest/concepts/validators/

---

## 5. Context Management & Multi-Turn Conversations

### Decision: Session-Based Context with Entity Tracking

**Rationale**:
- Enables natural follow-up questions ("Which of those have vulnerabilities?")
- Tracks entity mentions for reference resolution ("those APIs", "the vulnerable ones")
- Maintains query history for context-aware responses
- 1-hour TTL balances memory usage with user experience

**Implementation Approach**:
```python
class QueryContext(BaseModel):
    """Session context for multi-turn conversations."""
    session_id: str
    query_history: List[str] = []  # Max 10 queries
    entity_mentions: Dict[str, List[str]] = {}  # entity_type -> [entity_ids]
    resolved_references: Dict[str, str] = {}  # "those" -> "apis_from_query_1"
    last_query_results: Dict[str, Any] = {}
    created_at: datetime
    last_accessed: datetime
    ttl_seconds: int = 3600  # 1 hour

class ContextManager:
    """Manages query session contexts."""
    
    def __init__(self):
        self.contexts: Dict[str, QueryContext] = {}
    
    async def resolve_references(
        self, 
        query: str, 
        context: QueryContext
    ) -> str:
        """Resolve references like 'those', 'these', 'them'."""
        
        if any(ref in query.lower() for ref in ["those", "these", "them", "it"]):
            # LLM resolves reference to specific entities
            resolution = await llm_resolve_reference(query, context)
            return resolution.resolved_query
        
        return query
    
    async def update_context(
        self,
        session_id: str,
        query: str,
        results: Dict
    ):
        """Update context with new query and results."""
        context = self.contexts.get(session_id, QueryContext(session_id=session_id))
        
        # Add to history
        context.query_history.append(query)
        if len(context.query_history) > 10:
            context.query_history.pop(0)
        
        # Extract and track entities
        entities = extract_entities(results)
        for entity_type, entity_ids in entities.items():
            if entity_type not in context.entity_mentions:
                context.entity_mentions[entity_type] = []
            context.entity_mentions[entity_type].extend(entity_ids)
        
        # Store results
        context.last_query_results = results
        context.last_accessed = datetime.utcnow()
        
        self.contexts[session_id] = context
```

**Alternatives Considered**:
- **Stateless Queries**: Poor UX, requires full context in each query
- **Persistent Storage**: Overkill for 1-hour TTL, adds latency
- **No Reference Resolution**: Users must repeat entity IDs

**Key References**:
- Conversational AI Patterns: https://www.anthropic.com/research/conversational-ai
- Session Management Best Practices: https://fastapi.tiangolo.com/advanced/middleware/

---

## 6. Fallback Mechanisms & Graceful Degradation

### Decision: Confidence-Based Fallback with Trigger Logging

**Rationale**:
- Maintains service availability when agentic approach fails
- Confidence thresholds based on production data (0.6 = realistic)
- Comprehensive logging enables fallback rate optimization
- Backward compatible with existing OpenSearch query service

**Implementation Approach**:
```python
class FallbackTrigger(BaseModel):
    """Records fallback event."""
    reason: FallbackReason  # LOW_CONFIDENCE, TOOL_FAILURE, TIMEOUT, etc.
    confidence_score: float
    tool_failure_rate: float
    execution_time_ms: int
    query_text: str
    timestamp: datetime

class FallbackManager:
    """Manages fallback decisions and logging."""
    
    CONFIDENCE_THRESHOLD = 0.6
    TOOL_FAILURE_THRESHOLD = 0.5
    TIMEOUT_MS = 10000
    
    async def should_fallback(
        self,
        agent_result: Dict,
        execution_time_ms: int
    ) -> Tuple[bool, Optional[FallbackTrigger]]:
        """Evaluate if fallback is needed."""
        
        # Check confidence
        if agent_result.get("confidence", 0.0) < self.CONFIDENCE_THRESHOLD:
            return True, FallbackTrigger(
                reason=FallbackReason.LOW_CONFIDENCE,
                confidence_score=agent_result["confidence"],
                ...
            )
        
        # Check tool failure rate
        tool_calls = agent_result.get("tool_calls", [])
        if tool_calls:
            failures = sum(1 for t in tool_calls if not t.get("success", True))
            failure_rate = failures / len(tool_calls)
            if failure_rate > self.TOOL_FAILURE_THRESHOLD:
                return True, FallbackTrigger(
                    reason=FallbackReason.TOOL_FAILURE,
                    tool_failure_rate=failure_rate,
                    ...
                )
        
        # Check timeout
        if execution_time_ms > self.TIMEOUT_MS:
            return True, FallbackTrigger(
                reason=FallbackReason.TIMEOUT,
                execution_time_ms=execution_time_ms,
                ...
            )
        
        return False, None
```

**Fallback Triggers**:
1. **Low Confidence**: <0.6 (LLM not confident in agent/tool selection)
2. **Tool Failure Rate**: >50% (more than half of tool invocations failed)
3. **Timeout**: >10 seconds (workflow taking too long)
4. **No Tools Found**: LLM couldn't identify appropriate tools
5. **LLM Unavailable**: LLM service down or rate-limited

**Alternatives Considered**:
- **No Fallback**: Poor availability, service fails when agents fail
- **Always Fallback**: Defeats purpose of agentic approach
- **Manual Fallback**: Requires user intervention

**Key References**:
- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
- Graceful Degradation: https://www.nngroup.com/articles/graceful-degradation-vs-progressive-enhancement/

---

## 7. Performance Optimization

### Decision: Multi-Layer Caching with Connection Pooling

**Rationale**:
- LLM calls are expensive (latency + cost)
- Common query patterns benefit from caching
- Connection pooling prevents resource exhaustion
- Parallel execution reduces multi-agent latency

**Implementation Approach**:
```python
class LLMCache:
    """Multi-layer cache for LLM responses."""
    
    def __init__(self):
        self.query_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes
        self.tool_result_cache = TTLCache(maxsize=500, ttl=60)  # 1 minute
    
    async def get_or_compute(
        self,
        cache_key: str,
        compute_fn: Callable,
        cache_type: str = "query"
    ) -> Any:
        """Get from cache or compute and cache."""
        cache = self.query_cache if cache_type == "query" else self.tool_result_cache
        
        if cache_key in cache:
            return cache[cache_key]
        
        result = await compute_fn()
        cache[cache_key] = result
        return result

# Connection pooling
llm_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent LLM requests

async def invoke_llm_with_pooling(prompt: str) -> str:
    async with llm_semaphore:
        return await llm.ainvoke(prompt)

# Parallel agent execution
async def execute_parallel_agents(sub_queries: Dict) -> Dict:
    tasks = [
        agent.execute(query)
        for agent, query in sub_queries.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return dict(zip(sub_queries.keys(), results))
```

**Optimization Strategies**:
1. **LLM Response Caching**: 5-minute TTL for common query patterns
2. **Tool Result Caching**: 60-second TTL for frequently accessed data
3. **Connection Pooling**: Limit concurrent LLM requests (max 10)
4. **Parallel Execution**: Execute independent agents in parallel with timeout
5. **Retry Logic**: Exponential backoff for tool invocations (max 3 retries)

**Alternatives Considered**:
- **No Caching**: High latency and cost
- **Persistent Cache**: Overkill for short TTLs
- **Sequential Execution**: Higher latency for multi-agent queries

**Key References**:
- Caching Strategies: https://docs.python.org/3/library/functools.html#functools.lru_cache
- Async Best Practices: https://docs.python.org/3/library/asyncio.html

---

## 8. Testing Strategies for Agentic Workflows

### Decision: Integration Tests with Mock LLM Responses

**Rationale**:
- Project specification: "Integration Tests: Cross-component testing (required)"
- Agentic workflows are inherently integration-heavy (agents + tools + LLM)
- Mock LLM responses enable deterministic testing
- Focus on workflow correctness, not LLM accuracy

**Implementation Approach**:
```python
# Mock LLM for deterministic testing
class MockLLM:
    """Mock LLM with predefined responses."""
    
    def __init__(self, responses: Dict[str, str]):
        self.responses = responses
        self.call_count = 0
    
    async def ainvoke(self, messages: List) -> str:
        query = messages[-1].content
        self.call_count += 1
        
        # Match query pattern to response
        for pattern, response in self.responses.items():
            if pattern in query.lower():
                return response
        
        return self.responses.get("default", "{}")

# Integration test example
@pytest.mark.asyncio
async def test_iterative_reasoning_multi_step_query():
    """Test coordinator iterates to resolve gateway name then fetch APIs."""
    
    # Mock LLM responses for each iteration
    mock_llm = MockLLM({
        "decide next action": json.dumps({
            "action": "invoke_discovery_agent",
            "parameters": {"query": "get gateway with name 'local'"}
        }),
        "evaluate completion": json.dumps({
            "is_complete": False,
            "reasoning": "Need to fetch APIs for gateway"
        }),
        "gateway with name": json.dumps({
            "gateway_id": "gw-123",
            "name": "local"
        }),
        "fetch apis": json.dumps({
            "apis": [{"id": "api-1"}, {"id": "api-2"}]
        })
    })
    
    coordinator = CoordinatorAgent(llm=mock_llm, agents=mock_agents)
    result = await coordinator.execute_iterative_workflow(
        "Show APIs managed by gateway 'local'"
    )
    
    # Verify coordinator iterated twice
    assert result["iterations"] == 2
    assert result["completed_steps"] == [
        "Resolved gateway 'local' to gw-123",
        "Fetched APIs for gateway gw-123"
    ]
    assert len(result["apis"]) == 2
```

**Test Coverage Areas**:
1. **Single-Agent Workflows**: Agent selects tools, synthesizes results
2. **Multi-Agent Collaboration**: Coordinator orchestrates multiple agents
3. **Iterative Reasoning**: Coordinator iterates based on intermediate results
4. **Entity Synthesis**: Agents group tool results by entities
5. **Fallback Triggers**: System falls back on low confidence/failures
6. **Context Management**: Multi-turn conversations resolve references

**Alternatives Considered**:
- **Unit Tests Only**: Insufficient for agentic workflows (integration-heavy)
- **Real LLM in Tests**: Non-deterministic, slow, expensive
- **No Mocking**: Tests become flaky and slow

**Key References**:
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- Mock Patterns: https://docs.python.org/3/library/unittest.mock.html
- Integration Testing Best Practices: https://martinfowler.com/articles/practical-test-pyramid.html

---

## Summary of Key Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Iterative Reasoning** | LangChain agent loops with state management | Industry-standard, adaptive, built-in loop detection |
| **Synthesis** | Agent-level LLM synthesis with entity grouping | Distributes workload, domain-specific logic, cleaner interfaces |
| **Completion** | LLM-based with 10-iteration hard limit | Semantic completeness + safety, industry standard |
| **Tool Selection** | LLM-driven with Pydantic validation | Better than regex, automatic validation, retry logic |
| **Context** | Session-based with entity tracking | Enables follow-ups, 1-hour TTL balances UX and memory |
| **Fallback** | Confidence-based (0.6 threshold) with logging | Maintains availability, realistic thresholds, observable |
| **Performance** | Multi-layer caching + connection pooling | Reduces latency and cost, prevents resource exhaustion |
| **Testing** | Integration tests with mock LLM | Per project spec, deterministic, workflow-focused |

## Next Steps

1. **Phase 1**: Generate data-model.md, contracts/, quickstart.md
2. **Phase 1**: Update AGENTS.md with new technologies
3. **Phase 2**: Break down into implementation tasks (via `/speckit.tasks`)