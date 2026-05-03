# Tasks: Agentic Natural Language Query Service

**Input**: Design documents from `/specs/002-agentic-query/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Integration and E2E tests are REQUIRED per project specification. Tests are included in each user story phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/app/`, `frontend/src/`, `tests/`
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Verify Python 3.11+ environment and create virtual environment in backend/
- [X] T002 Install dependencies from backend/requirements.txt (FastAPI, LangChain, LangGraph, LiteLLM, FastMCP)
- [X] T003 [P] Configure environment variables in backend/.env (LLM API keys, OpenSearch, MCP server URL)
- [X] T004 [P] Verify OpenSearch 2.11+ is running and accessible
- [X] T005 [P] Verify unified MCP server is running at configured URL
- [X] T006 [P] Configure logging infrastructure in backend/app/utils/logging.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create CoordinatorState model in backend/app/models/agent.py (iteration tracking, intermediate results, completion state)
- [X] T008 [P] Create AgentDecision model in backend/app/models/agent.py (reasoning, tool selection, confidence)
- [X] T009 [P] Create ToolInvocation model in backend/app/models/agent.py (parameters, results, execution metadata)
- [X] T010 [P] Create EntityGrouping model in backend/app/models/agent.py (entity type, synthesis summary, relationships)
- [X] T011 [P] Create QueryContext model in backend/app/models/query.py (session state, entity tracking, reference resolution)
- [X] T012 [P] Create FallbackTrigger model in backend/app/models/agent.py (reason, metrics, opensearch query)
- [X] T013 Create ContextManager service in backend/app/services/context_manager.py (session management, entity tracking, reference resolution)
- [X] T014 [P] Create FallbackManager service in backend/app/services/fallback_manager.py (confidence thresholds, trigger detection, logging)
- [X] T015 [P] Create LLMCache service in backend/app/services/llm_cache.py (multi-layer caching with TTL)
- [X] T016 [P] Create LLMService wrapper in backend/app/services/llm_service.py (LiteLLM client, connection pooling, retry logic)
- [X] T017 Create ToolRegistry in backend/app/tools/tool_registry.py (tool registration, domain filtering, schema management)
- [X] T018 [P] Create TrackedTool wrapper in backend/app/tools/tracked_tool.py (invocation tracking, caching, retry logic)
- [X] T019 Initialize tool registry with existing MCP tools in backend/app/tools/__init__.py (gateway, API, security, compliance, metrics, prediction tools)
- [X] T020 Create BaseAgent class in backend/app/agents/query/base_agent.py (common agent interface, tool execution, synthesis pattern)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 6 - Iterative Multi-Step Coordinator Reasoning (Priority: P1) 🎯 MVP CORE

**Goal**: Implement coordinator agent with iterative reasoning loops that evaluates after each tool invocation and dynamically decides next steps

**Independent Test**: Submit "Show APIs managed by gateway 'local'" and verify coordinator iterates: (1) resolve gateway name to ID, (2) fetch APIs for that gateway ID

### Integration Tests for User Story 6

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T021 [P] [US6] Integration test for single iteration workflow in tests/integration/test_iterative_reasoning.py
- [X] T022 [P] [US6] Integration test for multi-step query (gateway name → APIs) in tests/integration/test_iterative_reasoning.py
- [X] T023 [P] [US6] Integration test for multi-step query (gateway → vulnerabilities → APIs) in tests/integration/test_iterative_reasoning.py
- [X] T024 [P] [US6] Integration test for loop prevention (max 10 iterations) in tests/integration/test_iterative_reasoning.py
- [X] T025 [P] [US6] Integration test for LLM-based completion decision in tests/integration/test_iterative_reasoning.py
- [X] T026 [P] [US6] Integration test for no-progress detection in tests/integration/test_iterative_reasoning.py

### Implementation for User Story 6

- [X] T027 [US6] Implement CoordinatorAgent with iterative reasoning loop in backend/app/agents/query/coordinator_agent.py (state management, LLM decision making)
- [X] T028 [US6] Add LLM-based agent selection with structured outputs in backend/app/agents/query/coordinator_agent.py (AgentSelectionDecision Pydantic model)
- [X] T029 [US6] Add LLM-based completion evaluation in backend/app/agents/query/coordinator_agent.py (CompletionDecision Pydantic model)
- [X] T030 [US6] Implement loop prevention mechanisms in backend/app/agents/query/coordinator_agent.py (max iterations, no-progress detection, timeout)
- [X] T031 [US6] Add intermediate result evaluation logic in backend/app/agents/query/coordinator_agent.py (extract entities, check sufficiency)
- [X] T032 [US6] Implement context enrichment for subsequent iterations in backend/app/agents/query/coordinator_agent.py (pass previous results to next agent)
- [X] T033 [US6] Add comprehensive logging for coordinator decisions in backend/app/agents/query/coordinator_agent.py (iteration steps, reasoning traces)
- [X] T034 [US6] Update AgenticQueryService to use iterative coordinator in backend/app/services/agentic_query_service.py
- [X] T035 [US6] Add coordinator state tracking to query responses in backend/app/api/v1/query.py (iteration count, completed steps)

**Checkpoint**: Coordinator can now iterate through multi-step queries, evaluating after each step

---

## Phase 4: User Story 1 - Basic Agentic Query Execution (Priority: P1) 🎯 MVP

**Goal**: Implement specialized agents that autonomously select and invoke MCP tools with LLM-powered synthesis

**Independent Test**: Submit "Show me all APIs with critical vulnerabilities" and verify agent selects correct tools and synthesizes results

### Integration Tests for User Story 1

- [X] T036 [P] [US1] Integration test for discovery agent workflow in tests/integration/test_agentic_query_flow.py (EXISTS from Feature 001)
- [X] T037 [P] [US1] Integration test for security agent workflow in tests/integration/test_agentic_query_flow.py (EXISTS from Feature 001)
- [X] T038 [P] [US1] Integration test for metrics agent workflow in tests/integration/test_agentic_query_flow.py (EXISTS from Feature 001)
- [X] T039 [P] [US1] Integration test for agent tool selection in tests/integration/test_agentic_query_flow.py (EXISTS from Feature 001)
- [X] T040 [P] [US1] Integration test for agent synthesis with entity grouping in tests/integration/test_entity_synthesis.py

### Implementation for User Story 1

- [X] T041 [P] [US1] Implement DiscoveryAgent in backend/app/agents/query/discovery_agent.py (gateway/API queries, tool selection, synthesis) (EXISTS from Feature 001)
- [X] T042 [P] [US1] Implement SecurityAgent in backend/app/agents/query/security_agent.py (vulnerability queries, tool selection, synthesis) (EXISTS from Feature 001)
- [X] T043 [P] [US1] Implement MetricsAgent in backend/app/agents/query/metrics_agent.py (performance queries, tool selection, synthesis) (EXISTS from Feature 001)
- [X] T044 [P] [US1] Implement ComplianceAgent in backend/app/agents/query/compliance_agent.py (compliance queries, tool selection, synthesis) (EXISTS from Feature 001)
- [X] T045 [P] [US1] Implement OptimizationAgent in backend/app/agents/query/optimization_agent.py (recommendation queries, tool selection, synthesis) (EXISTS from Feature 001)
- [X] T046 [P] [US1] Implement PredictionAgent in backend/app/agents/query/prediction_agent.py (prediction queries, tool selection, synthesis) (EXISTS from Feature 001)
- [X] T047 [US1] Add LLM-powered synthesis to each agent in backend/app/agents/query/*.py (entity grouping, natural language generation)
- [X] T048 [US1] Implement tool parameter validation in backend/app/agents/query/base_agent.py (Pydantic schema validation, retry on errors) (EXISTS from Feature 001)
- [X] T049 [US1] Add agent confidence scoring in backend/app/agents/query/base_agent.py (based on tool success rate, LLM certainty) (EXISTS from Feature 001)
- [X] T050 [US1] Register all specialized agents in backend/app/services/agentic_query_service.py (EXISTS from Feature 001)
- [X] T051 [US1] Update query API endpoint to return agentic metadata in backend/app/api/v1/query.py (agent decisions, tool invocations) (EXISTS from Feature 001)

**Checkpoint**: All 6 specialized agents can now handle single-domain queries with LLM-powered synthesis ✅

---

## Phase 5: User Story 2 - Multi-Agent Collaboration (Priority: P2)

**Goal**: Enable coordinator to orchestrate multiple specialized agents for complex cross-domain queries

**Independent Test**: Submit "Which APIs have both high latency and security vulnerabilities?" and verify metrics + security agents collaborate

### Integration Tests for User Story 2

- [X] T052 [P] [US2] Integration test for parallel agent execution in tests/integration/test_multi_agent_collaboration.py
- [X] T053 [P] [US2] Integration test for sequential agent execution in tests/integration/test_multi_agent_collaboration.py
- [X] T054 [P] [US2] Integration test for entity correlation across agents in tests/integration/test_multi_agent_collaboration.py
- [X] T055 [P] [US2] Integration test for conflict resolution in tests/integration/test_multi_agent_collaboration.py

### Implementation for User Story 2

- [X] T056 [US2] Implement LLM-based query decomposition in backend/app/agents/query/coordinator_agent.py (MultiAgentDecomposition Pydantic model) (EXISTS from Feature 001)
- [X] T057 [US2] Add parallel agent execution with timeout in backend/app/agents/query/coordinator_agent.py (asyncio.gather with timeout) (EXISTS from Feature 001)
- [X] T058 [US2] Add sequential agent execution with dependencies in backend/app/agents/query/coordinator_agent.py (topological sort, context enrichment) (EXISTS from Feature 001)
- [X] T059 [US2] Implement entity correlation by ID in backend/app/agents/query/coordinator_agent.py (correlate_results_by_entity method) (EXISTS from Feature 001)
- [X] T060 [US2] Add conflict resolution logic in backend/app/agents/query/coordinator_agent.py (resolve_conflicts method) (EXISTS from Feature 001)
- [X] T061 [US2] Implement multi-agent response synthesis in backend/app/services/agentic_query_service.py (generate_multi_agent_response method) (EXISTS from Feature 001)
- [X] T062 [US2] Update query API to handle multi-agent responses in backend/app/api/v1/query.py (execution strategy, agent results) (EXISTS from Feature 001)

**Checkpoint**: Coordinator can now orchestrate multiple agents for cross-domain queries ✅

---

## Phase 6: User Story 3 - Intelligent Fallback to OpenSearch (Priority: P3)

**Goal**: Implement confidence-based fallback mechanism with comprehensive logging

**Independent Test**: Submit query that triggers fallback (low confidence or tool failures) and verify OpenSearch is used with proper logging

### Integration Tests for User Story 3

- [X] T063 [P] [US3] Integration test for low confidence fallback in tests/integration/test_fallback_mechanism.py
- [X] T064 [P] [US3] Integration test for tool failure fallback in tests/integration/test_fallback_mechanism.py
- [X] T065 [P] [US3] Integration test for timeout fallback in tests/integration/test_fallback_mechanism.py
- [X] T066 [P] [US3] Integration test for fallback trigger logging in tests/integration/test_fallback_mechanism.py

### Implementation for User Story 3

- [X] T067 [US3] Implement confidence-based fallback detection in backend/app/services/fallback_manager.py (threshold: 0.6) (EXISTS from Feature 001)
- [X] T068 [US3] Implement tool failure rate detection in backend/app/services/fallback_manager.py (threshold: 50%) (EXISTS from Feature 001)
- [X] T069 [US3] Implement timeout detection in backend/app/services/fallback_manager.py (threshold: 10 seconds) (EXISTS from Feature 001)
- [X] T070 [US3] Add fallback trigger logging to OpenSearch in backend/app/services/fallback_manager.py
- [X] T071 [US3] Integrate fallback manager with agentic query service in backend/app/services/agentic_query_service.py (EXISTS from Feature 001)
- [X] T072 [US3] Add fallback metadata to query responses in backend/app/api/v1/query.py (reason, metrics, opensearch query) (EXISTS from Feature 001)
- [X] T073 [US3] Create fallback metrics endpoint in backend/app/api/v1/query.py (fallback rate, reasons breakdown) (EXISTS from Feature 001)

**Checkpoint**: System gracefully falls back to OpenSearch when agentic approach fails ✅

---

## Phase 7: User Story 4 - Conversational Context Awareness (Priority: P2)

**Goal**: Enable multi-turn conversations with reference resolution and entity tracking

**Independent Test**: Submit "Show me all APIs" then "Which of those have vulnerabilities?" and verify context resolution

### E2E Tests for User Story 4

- [X] T074 [P] [US4] E2E test for multi-turn conversation in tests/e2e/test_conversational_context.py
- [X] T075 [P] [US4] E2E test for reference resolution ("those", "them") in tests/e2e/test_conversational_context.py
- [X] T076 [P] [US4] E2E test for entity tracking across queries in tests/e2e/test_conversational_context.py
- [X] T077 [P] [US4] E2E test for context expiration (1-hour TTL) in tests/e2e/test_conversational_context.py

### Implementation for User Story 4

- [X] T078 [US4] Implement session-based context storage in backend/app/services/context_manager.py (in-memory with TTL) (EXISTS from Feature 001)
- [X] T079 [US4] Add query history tracking in backend/app/services/context_manager.py (max 10 queries) (EXISTS from Feature 001)
- [X] T080 [US4] Implement entity mention tracking in backend/app/services/context_manager.py (entity_type → [entity_ids]) (EXISTS from Feature 001)
- [X] T081 [US4] Add LLM-based reference resolution in backend/app/services/context_manager.py (resolve "those", "them", "it") (EXISTS from Feature 001)
- [X] T082 [US4] Implement context cleanup (TTL expiration) in backend/app/services/context_manager.py (EXISTS from Feature 001)
- [X] T083 [US4] Integrate context manager with agentic query service in backend/app/services/agentic_query_service.py (EXISTS from Feature 001)
- [X] T084 [US4] Add session_id to query API request/response in backend/app/api/v1/query.py (EXISTS from Feature 001)
- [X] T085 [US4] Update frontend to maintain session_id in frontend/src/services/query-service.ts
- [X] T086 [US4] Add query history display in frontend/src/components/query/QueryHistory.tsx

**Checkpoint**: Users can now have natural multi-turn conversations with context

---

## Phase 8: User Story 5 - Enhanced Search APIs for Flexible Querying (Priority: P2)

**Goal**: Implement search API endpoints and register as tools for complex filtering

**Independent Test**: Submit "Find APIs created last week with names containing 'payment'" and verify search_apis tool is used

### Integration Tests for User Story 5

- [X] T087 [P] [US5] Integration test for search_apis tool in tests/integration/test_search_apis.py
- [X] T088 [P] [US5] Integration test for search_gateways tool in tests/integration/test_search_apis.py
- [X] T089 [P] [US5] Integration test for search_vulnerabilities tool in tests/integration/test_search_apis.py
- [X] T090 [P] [US5] Integration test for agent preferring search over list tools in tests/integration/test_search_apis.py

### Implementation for User Story 5

- [X] T091 [P] [US5] Implement search_apis endpoint in backend/app/api/v1/apis.py (name pattern, date range, status filters) (EXISTS from Feature 001)
- [X] T092 [P] [US5] Implement search_gateways endpoint in backend/app/api/v1/gateways.py (name pattern, status filters) (EXISTS from Feature 001)
- [X] T093 [P] [US5] Implement search_vulnerabilities endpoint in backend/app/api/v1/security.py (severity, date range, API name filters) (EXISTS from Feature 001)
- [X] T094 [P] [US5] Implement search_compliance_violations endpoint in backend/app/api/v1/compliance.py (standard, severity, date filters) (EXISTS from Feature 001)
- [X] T095 [P] [US5] Implement search_recommendations endpoint in backend/app/api/v1/optimization.py (type, priority, status filters) (EXISTS from Feature 001)
- [X] T096 [P] [US5] Implement search_predictions endpoint in backend/app/api/v1/predictions.py (confidence threshold, gateway filters) (EXISTS from Feature 001)
- [X] T097 [US5] Register search tools in tool registry in backend/app/tools/__init__.py (map to appropriate agent domains) (EXISTS from Feature 001)
- [X] T098 [US5] Update agent system prompts to prefer search tools for complex filtering in backend/app/agents/query/*.py (EXISTS from Feature 001)
- [X] T099 [US5] Add search tool usage tracking in backend/app/tools/tracked_tool.py (EXISTS from Feature 001)

**Checkpoint**: Agents can now use flexible search APIs for complex filtering queries

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T100 [P] Add performance profiling for agent workflows in backend/scripts/profile_agentic_query.py
- [X] T101 [P] Implement LLM response caching with 5-minute TTL in backend/app/services/llm_cache.py (EXISTS from Feature 001)
- [X] T102 [P] Implement tool result caching with 60-second TTL in backend/app/services/llm_cache.py (EXISTS from Feature 001)
- [X] T103 [P] Add connection pooling for LLM requests (max 10 concurrent) in backend/app/services/llm_service.py (EXISTS from Feature 001)
- [X] T104 [P] Add retry logic with exponential backoff for tool invocations in backend/app/tools/tracked_tool.py (EXISTS from Feature 001)
- [X] T105 [P] Implement circuit breaker for LLM service in backend/app/services/llm_service.py (EXISTS from Feature 001)
- [X] T106 [P] Add comprehensive error handling across all agents in backend/app/agents/query/*.py (EXISTS from Feature 001)
- [X] T107 [P] Add agent decision logging to OpenSearch in backend/app/services/agentic_query_service.py (EXISTS from Feature 001)
- [X] T108 [P] Create monitoring dashboard for agentic metrics in frontend/src/pages/AgenticMetrics.tsx
- [X] T109 [P] Update API documentation in specs/002-agentic-query/contracts/query-api.md (COMPLETE)
- [X] T110 [P] Add example queries to quickstart guide in specs/002-agentic-query/quickstart.md (COMPLETE)
- [ ] T111 Run full integration test suite from quickstart.md
- [ ] T112 Run E2E test suite for all user stories
- [ ] T113 Performance validation: verify <5s single-agent, <10s multi-agent
- [ ] T114 Validate 90%+ agentic success rate (10% fallback)
- [ ] T115 Code quality: run black, isort, flake8, mypy on backend/app/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 6 (Phase 3)**: Depends on Foundational - CORE MVP (iterative reasoning)
- **User Story 1 (Phase 4)**: Depends on Foundational + US6 - MVP (specialized agents)
- **User Story 2 (Phase 5)**: Depends on US1 (needs specialized agents)
- **User Story 3 (Phase 6)**: Depends on US1 (needs agentic workflow to fallback from)
- **User Story 4 (Phase 7)**: Depends on US1 (needs basic query execution)
- **User Story 5 (Phase 8)**: Depends on US1 (needs agents to use search tools)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 6 (P1)**: CORE - Iterative coordinator reasoning (no dependencies on other stories)
- **User Story 1 (P1)**: MVP - Basic agentic execution (depends on US6 for coordinator)
- **User Story 2 (P2)**: Multi-agent collaboration (depends on US1 for specialized agents)
- **User Story 3 (P3)**: Fallback mechanism (depends on US1 for agentic workflow)
- **User Story 4 (P2)**: Context awareness (depends on US1 for basic execution)
- **User Story 5 (P2)**: Search APIs (depends on US1 for agents to use them)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before agents
- Agents before API endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes:
  - US6 must complete first (coordinator is core)
  - After US6: US1 can start
  - After US1: US2, US3, US4, US5 can all run in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members (after dependencies met)

---

## Parallel Example: User Story 1

```bash
# Launch all integration tests for User Story 1 together:
Task T036: "Integration test for discovery agent workflow"
Task T037: "Integration test for security agent workflow"
Task T038: "Integration test for metrics agent workflow"
Task T039: "Integration test for agent tool selection"
Task T040: "Integration test for agent synthesis with entity grouping"

# Launch all specialized agents together:
Task T041: "Implement DiscoveryAgent"
Task T042: "Implement SecurityAgent"
Task T043: "Implement MetricsAgent"
Task T044: "Implement ComplianceAgent"
Task T045: "Implement OptimizationAgent"
Task T046: "Implement PredictionAgent"
```

---

## Implementation Strategy

### MVP First (User Stories 6 + 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 6 (Iterative coordinator - CORE)
4. Complete Phase 4: User Story 1 (Specialized agents - MVP)
5. **STOP and VALIDATE**: Test US6 + US1 independently
6. Deploy/demo if ready

**MVP Delivers**:
- Iterative coordinator that evaluates after each step
- 6 specialized agents with LLM synthesis
- Single-domain and multi-step queries
- Entity grouping (e.g., 40 vulnerabilities → 8 APIs)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 6 → Test independently → Core reasoning works
3. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
4. Add User Story 2 → Test independently → Deploy/Demo (Multi-agent)
5. Add User Story 3 → Test independently → Deploy/Demo (Fallback)
6. Add User Story 4 → Test independently → Deploy/Demo (Context)
7. Add User Story 5 → Test independently → Deploy/Demo (Search)
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Team completes User Story 6 together (coordinator is core)
3. Once US6 done, team completes User Story 1 together (6 agents)
4. Once US1 done:
   - Developer A: User Story 2 (multi-agent)
   - Developer B: User Story 3 (fallback)
   - Developer C: User Story 4 (context)
   - Developer D: User Story 5 (search APIs)
5. Stories complete and integrate independently

---

## Task Summary

- **Total Tasks**: 115
- **Setup Phase**: 6 tasks
- **Foundational Phase**: 14 tasks (BLOCKING)
- **User Story 6 (P1)**: 15 tasks (Iterative reasoning - CORE)
- **User Story 1 (P1)**: 16 tasks (Specialized agents - MVP)
- **User Story 2 (P2)**: 11 tasks (Multi-agent collaboration)
- **User Story 3 (P3)**: 11 tasks (Fallback mechanism)
- **User Story 4 (P2)**: 13 tasks (Context awareness)
- **User Story 5 (P2)**: 13 tasks (Search APIs)
- **Polish Phase**: 16 tasks

**Parallel Opportunities**: 67 tasks marked [P] can run in parallel within their phase

**MVP Scope**: Phases 1-4 (Setup + Foundational + US6 + US1) = 51 tasks

**Independent Test Criteria**:
- US6: Multi-step queries iterate correctly
- US1: Single-domain queries with synthesis
- US2: Cross-domain queries with correlation
- US3: Fallback triggers and logs correctly
- US4: Multi-turn conversations resolve context
- US5: Complex filtering uses search tools

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Focus on US6 + US1 for MVP (iterative reasoning + specialized agents)