# Implementation Plan: Agentic Natural Language Query Service

**Branch**: `002-agentic-query` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-agentic-query/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Transform the natural language query service from a probabilistic OpenSearch query generator to a fully agentic system using LangChain/LangGraph agents. The coordinator agent uses iterative reasoning loops to dynamically select and invoke specialized agents (discovery, metrics, security, compliance, optimization, prediction), which autonomously choose and execute MCP server tools. Each specialized agent performs LLM-powered synthesis to group tool results by entities (e.g., vulnerabilities → APIs) before returning to the coordinator. The system maintains conversational context across multi-turn queries and falls back to OpenSearch when the agentic approach fails.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI 0.109+, LangChain 0.1+, LangGraph 0.0.20+, LiteLLM 1.17+, FastMCP 0.1+  
**Storage**: OpenSearch 2.11+ (for fallback queries and query history)  
**Testing**: pytest 7.4+, pytest-asyncio 0.21+ (focus on integration and E2E tests per project spec)  
**Target Platform**: Linux server (Docker containers, Kubernetes deployment)  
**Project Type**: Web service (FastAPI backend with React frontend)  
**Performance Goals**: 
- Single-agent queries: <5 seconds
- Multi-agent queries: <10 seconds
- Coordinator iterative reasoning: <5 seconds (typical 2-3 iterations)
- LLM synthesis per agent: <1 second
- Support 100 concurrent agent workflows

**Constraints**: 
- Agent reasoning + tool selection: <2 seconds
- Single MCP tool invocation: <3 seconds
- Memory per agent workflow: <100MB
- Maximum coordinator iterations: 10 (loop prevention)
- Fallback activation: <1 second on failure detection

**Scale/Scope**: 
- 6 specialized agents (discovery, metrics, security, compliance, optimization, prediction)
- 1 coordinator agent with iterative reasoning
- 20+ MCP server tools across all domains
- Support 1000+ concurrent query sessions
- 90% agentic success rate (10% fallback to OpenSearch)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Project Constitution**: This project uses AGENTS.md as its development guidelines rather than a formal constitution file. The guidelines emphasize:

1. **Integration Testing Focus**: Project specification explicitly states "Integration Tests: Cross-component testing (required), E2E Tests: Complete workflow validation (required), Unit Tests: Not required per project specification"

2. **Existing Architecture Compliance**: 
   - ✅ Integrated within existing backend (not a separate microservice)
   - ✅ Uses direct function calls to backend routers (not HTTP calls)
   - ✅ Maintains existing REST API contracts
   - ✅ Follows established project structure (backend/app/agents/, backend/app/services/)

3. **Technology Stack Alignment**:
   - ✅ Python 3.11+ with FastAPI 0.109+
   - ✅ LangChain 0.1+, LangGraph 0.0.20+, LiteLLM 1.17+ (already in AGENTS.md)
   - ✅ OpenSearch 2.11+ for fallback mechanism
   - ✅ pytest 7.4+ for testing

4. **Code Quality Standards**:
   - ✅ Black, isort, flake8, mypy for code quality
   - ✅ Comprehensive logging and observability
   - ✅ Type hints and Pydantic models

**Gate Status**: ✅ PASS - No constitution violations. Feature aligns with existing architecture and guidelines.

## Project Structure

### Documentation (this feature)

```text
specs/002-agentic-query/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── query-api.md     # REST API contract for /query endpoint
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── agents/
│   │   └── query/
│   │       ├── base_agent.py           # Base class for specialized agents
│   │       ├── coordinator_agent.py    # Iterative reasoning coordinator (ENHANCED)
│   │       ├── discovery_agent.py      # Gateway/API discovery queries
│   │       ├── metrics_agent.py        # Performance/analytics queries
│   │       ├── security_agent.py       # Vulnerability/security queries
│   │       ├── compliance_agent.py     # Compliance/audit queries
│   │       ├── optimization_agent.py   # Recommendation queries
│   │       └── prediction_agent.py     # Failure prediction queries
│   ├── services/
│   │   ├── agentic_query_service.py    # Main orchestration service (ENHANCED)
│   │   ├── context_manager.py          # Session context management
│   │   ├── fallback_manager.py         # Fallback decision logic
│   │   ├── llm_service.py              # LLM client wrapper
│   │   └── llm_cache.py                # LLM response caching
│   ├── tools/
│   │   ├── tool_registry.py            # Tool registration and discovery
│   │   ├── tracked_tool.py             # Tool invocation tracking
│   │   ├── gateway_tools.py            # Gateway-related tools
│   │   ├── api_tools.py                # API-related tools
│   │   ├── security_tools.py           # Security-related tools
│   │   ├── compliance_tools.py         # Compliance-related tools
│   │   ├── metrics_tools.py            # Metrics-related tools
│   │   └── prediction_tools.py         # Prediction-related tools
│   ├── models/
│   │   ├── agent.py                    # Agent-related Pydantic models (ENHANCED)
│   │   └── query.py                    # Query-related Pydantic models
│   └── api/
│       └── v1/
│           └── query.py                # Query REST API endpoint (ENHANCED)
└── tests/
    ├── integration/
    │   ├── test_agentic_query_flow.py          # Single-agent workflow tests
    │   ├── test_multi_agent_collaboration.py   # Multi-agent workflow tests
    │   ├── test_iterative_reasoning.py         # Coordinator iteration tests
    │   ├── test_entity_synthesis.py            # Agent synthesis tests
    │   └── test_fallback_mechanism.py          # Fallback trigger tests
    └── e2e/
        ├── test_query_scenarios.py             # End-to-end query scenarios
        └── test_conversational_context.py      # Multi-turn conversation tests

frontend/
└── src/
    ├── pages/
    │   └── Query.tsx                   # Query interface page (ENHANCED)
    ├── components/
    │   └── query/
    │       ├── QueryInput.tsx          # Natural language input
    │       ├── QueryResponse.tsx       # Response display (ENHANCED)
    │       └── QueryHistory.tsx        # Session history
    └── services/
        └── query-service.ts            # Query API client (ENHANCED)
```

**Structure Decision**: Web application structure (Option 2) with backend and frontend. This feature enhances existing backend agents and services while maintaining the established project structure. New files are added to existing directories (backend/app/agents/query/, backend/app/services/) rather than creating new top-level directories.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - this section is not applicable.

## Phase 0: Research & Technical Decisions

See [research.md](./research.md) for detailed research findings on:

1. **Iterative Reasoning Patterns**: LangChain agent loops, ReAct pattern, coordinator state management
2. **LLM-Powered Synthesis**: Entity grouping strategies, natural language generation, confidence scoring
3. **Tool Selection Strategies**: Dynamic tool discovery, parameter validation, retry mechanisms
4. **Context Management**: Session state, entity tracking, reference resolution
5. **Fallback Mechanisms**: Trigger detection, graceful degradation, confidence thresholds
6. **Performance Optimization**: LLM caching, parallel execution, timeout management
7. **Testing Strategies**: Integration test patterns for agentic workflows, mock LLM responses

## Phase 1: Design Artifacts

### Data Model

See [data-model.md](./data-model.md) for entity definitions:

- **CoordinatorState**: Tracks iterative reasoning state (steps completed, intermediate results, next actions)
- **AgentDecision**: Records agent reasoning, tool selection rationale, confidence scores
- **ToolInvocation**: Represents MCP tool calls with parameters, results, execution metadata
- **EntityGrouping**: Aggregated results grouped by entity type (APIs, gateways, vulnerabilities)
- **QueryContext**: Session state including query history, entity mentions, resolved references
- **FallbackTrigger**: Records when/why system fell back to OpenSearch

### API Contracts

See [contracts/query-api.md](./contracts/query-api.md) for:

- **POST /api/v1/query**: Enhanced with agentic metadata (agent decisions, tool invocations, confidence scores, synthesis details)
- **Response Format**: Backward-compatible with additional fields for agentic mode indicators
- **Session Management**: Session ID for multi-turn conversations

### Quickstart Guide

See [quickstart.md](./quickstart.md) for:

- Local development setup for agentic query service
- Running integration tests for iterative reasoning
- Testing multi-agent collaboration scenarios
- Debugging agent decisions and tool invocations

## Phase 2: Task Breakdown

*Generated by `/speckit.tasks` command - not included in this plan output*

## Implementation Notes

### Key Design Decisions

1. **Iterative Reasoning Loop**: Coordinator evaluates after EACH tool invocation, decides if more information is needed, and dynamically invokes additional agents/tools based on intermediate results (industry-standard agentic pattern)

2. **Agent-Level Synthesis**: Each specialized agent uses LLM to synthesize and group its own tool results before returning to coordinator (distributes workload, enables domain-specific grouping)

3. **LLM-Based Completion**: After each iteration, LLM evaluates if sufficient information has been gathered to answer the user's query (stops when complete or max 10 iterations reached)

4. **Loop Prevention**: Maximum 10 iterations (industry standard) - allows complex multi-step queries while preventing runaway loops

5. **Entity Grouping**: LLM analyzes tool results and groups by entity relationships (e.g., 40 vulnerabilities → 8 affected APIs)

### Critical Implementation Paths

1. **Coordinator Iterative Reasoning** (Priority: P1)
   - Implement reasoning loop with state tracking
   - Add LLM-based completion decision after each iteration
   - Implement loop detection (max 10 iterations)
   - Add intermediate result evaluation

2. **Agent LLM Synthesis** (Priority: P1)
   - Add synthesis step to each specialized agent
   - Implement entity grouping logic
   - Generate natural language summaries
   - Track synthesis confidence scores

3. **Multi-Step Query Handling** (Priority: P1)
   - Enable coordinator to invoke same agent multiple times
   - Pass intermediate results as context to subsequent invocations
   - Implement dependency tracking between steps

4. **Fallback Enhancement** (Priority: P2)
   - Update fallback triggers for iterative reasoning failures
   - Add confidence-based fallback decisions
   - Implement graceful degradation

### Testing Strategy

Focus on integration and E2E tests per project specification:

1. **Integration Tests**:
   - Single-agent workflows with synthesis
   - Multi-agent collaboration with entity correlation
   - Iterative reasoning with multiple coordinator iterations
   - Fallback mechanism triggers

2. **E2E Tests**:
   - Complete query scenarios (simple → complex)
   - Multi-turn conversations with context
   - Multi-step queries requiring iteration
   - Error recovery and fallback paths

3. **Mock Strategy**:
   - Mock LLM responses for deterministic testing
   - Mock MCP tool results for agent testing
   - Mock intermediate results for coordinator testing

## Success Metrics

- **SC-013**: Coordinator successfully resolves 90%+ of multi-step queries requiring iterative reasoning
- **SC-014**: Entity grouping accuracy reaches 95%+ (e.g., correctly grouping 40 vulnerabilities into 8 affected APIs)
- **SC-015**: Iterative coordinator reasoning completes within 3 iterations for 80%+ of multi-step queries
- **SC-002**: 90% of queries handled by agentic workflow without fallback
- **SC-003**: Average query response time <5s (single-agent), <10s (multi-agent)

## Risk Mitigation

1. **LLM Latency**: Implement aggressive caching (5-minute TTL for common patterns)
2. **Infinite Loops**: Hard limit of 10 iterations with early termination on no progress
3. **Synthesis Accuracy**: Validate entity grouping with integration tests, track accuracy metrics
4. **Fallback Rate**: Monitor fallback triggers, tune confidence thresholds based on production data
5. **Memory Usage**: Profile agent workflows, ensure <100MB per workflow constraint met
