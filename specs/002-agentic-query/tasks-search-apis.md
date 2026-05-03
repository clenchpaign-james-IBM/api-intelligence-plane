# Tasks: Enhanced Search APIs for Agentic Query (User Story 5)

**Feature**: User Story 5 - Enhanced Search APIs for Flexible Querying
**Priority**: P2
**Branch**: `002-agentic-query`
**Prerequisites**: Agentic query system (User Stories 1-4) must be implemented
**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [search-apis-implementation.md](./search-apis-implementation.md)

## Overview

This task list implements 6 search API endpoints that provide flexible multi-criteria filtering for agents. These search APIs complement existing list/get tools by enabling complex queries with multiple filters, text patterns, and date ranges.

## Format: `[ID] [P?] [US5] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US5]**: All tasks belong to User Story 5
- Include exact file paths in descriptions

---

## Phase 1: Repository Layer (6 search methods)

**Purpose**: Implement OpenSearch-based search methods in repository classes

### Gateway Search

- [x] T001 [P] [US5] Implement GatewayRepository.search_gateways() method in backend/app/db/repositories/gateway_repository.py with parameters: name, vendor, status, created_after, created_before, page, page_size

### API Search

- [x] T002 [P] [US5] Implement APIRepository.search_apis() method in backend/app/db/repositories/api_repository.py with parameters: name, description, status, authentication_type, is_shadow, health_score_min/max, gateway_id, created_after/before, page, page_size

### Security Search

- [x] T003 [P] [US5] Implement VulnerabilityRepository.search_vulnerabilities() method in backend/app/db/repositories/vulnerability_repository.py with parameters: severity, type, status, api_name, gateway_id, discovered_after/before, page, page_size

### Compliance Search

- [x] T004 [P] [US5] Implement ComplianceRepository.search_compliance_violations() method in backend/app/db/repositories/compliance_repository.py with parameters: standard, violation_type, severity, status, api_name, gateway_id, discovered_after/before, page, page_size

### Optimization Search

- [x] T005 [P] [US5] Implement RecommendationRepository.search_recommendations() method in backend/app/db/repositories/recommendation_repository.py with parameters: type, priority, status, impact_min/max, api_name, gateway_id, created_after/before, page, page_size

### Prediction Search

- [x] T006 [P] [US5] Implement PredictionRepository.search_predictions() method in backend/app/db/repositories/prediction_repository.py with parameters: prediction_type, confidence_min/max, severity, status, predicted_after/before, api_name, gateway_id, page, page_size

**Checkpoint**: All repository search methods implemented with OpenSearch bool queries

---

## Phase 2: API Endpoints (6 search endpoints)

**Purpose**: Create REST API endpoints that expose search functionality

**Dependencies**: Phase 1 must be complete

### Gateway Search Endpoint

- [X] T007 [US5] Add GET /api/v1/gateways/search endpoint in backend/app/api/v1/gateways.py with GatewaySearchRequest/Response models and parameter validation

### API Search Endpoint

- [X] T008 [US5] Add GET /api/v1/apis/search endpoint in backend/app/api/v1/apis.py with APISearchRequest/Response models and health score validation (0.0-1.0)

### Security Search Endpoint

- [X] T009 [US5] Add GET /api/v1/security/vulnerabilities/search endpoint in backend/app/api/v1/security.py with VulnerabilitySearchRequest/Response models and severity/status enum validation

### Compliance Search Endpoint

- [X] T010 [US5] Add GET /api/v1/compliance/violations/search endpoint in backend/app/api/v1/compliance.py with ComplianceViolationSearchRequest/Response models and standard/severity enum validation

### Optimization Search Endpoint

- [X] T011 [US5] Add GET /api/v1/optimization/recommendations/search endpoint in backend/app/api/v1/optimization.py with RecommendationSearchRequest/Response models and impact range validation (0-100)

### Prediction Search Endpoint

- [X] T012 [US5] Add GET /api/v1/predictions/search endpoint in backend/app/api/v1/predictions.py with PredictionSearchRequest/Response models and confidence range validation (0.0-1.0)

**Checkpoint**: All 6 search endpoints functional and returning consistent response format

---

## Phase 3: Tool Registration (6 search tools)

**Purpose**: Register search endpoints as LangChain tools for agent use

**Dependencies**: Phase 2 must be complete

### Discovery Agent Tools

- [X] T013 [P] [US5] Register search_gateways tool in backend/app/tools/__init__.py for discovery agent with enhanced description including when to prefer over list_gateways

- [X] T014 [P] [US5] Register search_apis tool in backend/app/tools/__init__.py for discovery agent with guidance on text pattern matching and multi-criteria filtering

### Security Agent Tool

- [X] T015 [P] [US5] Register search_vulnerabilities tool in backend/app/tools/__init__.py for security agent with severity/type filtering examples and date range patterns

### Compliance Agent Tool

- [X] T016 [P] [US5] Register search_compliance_violations tool in backend/app/tools/__init__.py for compliance agent with standard-specific filtering and audit reporting examples

### Optimization Agent Tool

- [X] T017 [P] [US5] Register search_recommendations tool in backend/app/tools/__init__.py for optimization agent with priority/impact filtering and implementation tracking examples

### Prediction Agent Tool

- [X] T018 [P] [US5] Register search_predictions tool in backend/app/tools/__init__.py for prediction agent with confidence threshold and time range filtering examples

**Checkpoint**: All 6 search tools registered and available to appropriate agents

---

## Phase 4: Agent Integration (5 agent updates)

**Purpose**: Update agent system prompts to guide tool selection

**Dependencies**: Phase 3 must be complete

### Discovery Agent Update

- [X] T019 [US5] Update DiscoveryAgent system prompt in backend/app/agents/query/discovery_agent.py with guidance on when to use search_gateways vs list_gateways and search_apis vs list_all_apis

### Security Agent Update

- [X] T020 [US5] Update SecurityAgent system prompt in backend/app/agents/query/security_agent.py with search_vulnerabilities usage guidance including severity + date range examples

### Compliance Agent Update

- [X] T021 [US5] Update ComplianceAgent system prompt in backend/app/agents/query/compliance_agent.py with search_compliance_violations usage guidance including standard-specific filtering patterns

### Optimization Agent Update

- [X] T022 [US5] Update OptimizationAgent system prompt in backend/app/agents/query/optimization_agent.py with search_recommendations usage guidance including priority + impact filtering examples

### Prediction Agent Update

- [X] T023 [US5] Update PredictionAgent system prompt in backend/app/agents/query/prediction_agent.py with search_predictions usage guidance including confidence threshold and time range examples

**Checkpoint**: All agents aware of search tools and when to use them

---

## Phase 5: Integration Testing

**Purpose**: Verify search APIs work end-to-end with agents

**Dependencies**: Phase 4 must be complete

### Repository Tests

- [ ] T024 [P] [US5] Create repository search tests in backend/tests/unit/test_repositories/test_gateway_repository_search.py testing filter combinations, pagination, empty results (DEFERRED)

- [ ] T025 [P] [US5] Create repository search tests in backend/tests/unit/test_repositories/test_api_repository_search.py testing text patterns, health score ranges, date filters (DEFERRED)

- [ ] T026 [P] [US5] Create repository search tests in backend/tests/unit/test_repositories/test_vulnerability_repository_search.py testing severity filters, API name patterns, date ranges (DEFERRED)

- [ ] T027 [P] [US5] Create repository search tests in backend/tests/unit/test_repositories/test_compliance_repository_search.py testing standard filters, violation types, severity combinations (DEFERRED)

- [ ] T028 [P] [US5] Create repository search tests in backend/tests/unit/test_repositories/test_recommendation_repository_search.py testing type/priority/status filters, impact ranges (DEFERRED)

- [ ] T029 [P] [US5] Create repository search tests in backend/tests/unit/test_repositories/test_prediction_repository_search.py testing confidence ranges, prediction types, time filters (DEFERRED)

### API Endpoint Tests

- [ ] T030 [US5] Create API endpoint tests in backend/tests/integration/test_search_apis.py testing all 6 endpoints with valid parameters, validation errors (400), pagination, response format consistency (DEFERRED)

### Tool Invocation Tests

- [ ] T031 [US5] Create tool invocation tests in backend/tests/integration/test_search_tools.py testing each search tool from agent context, parameter passing, result parsing, error handling (DEFERRED)

### Agent Integration Tests

- [ ] T032 [US5] Create agent integration tests in backend/tests/e2e/test_search_agent_integration.py testing agents selecting search tools for complex queries, fallback reduction, multi-criteria filtering, text pattern accuracy (DEFERRED)

**Checkpoint**: All tests passing, search APIs fully integrated with agentic system

---

## Phase 6: Documentation & Metrics

**Purpose**: Document search APIs and establish monitoring

**Dependencies**: Phase 5 must be complete

- [X] T033 [P] [US5] Update API documentation in docs/api-reference.md with search endpoint specifications, parameter descriptions, example requests/responses

- [X] T034 [P] [US5] Add search API usage examples to specs/002-agentic-query/quickstart.md demonstrating complex filtering scenarios

- [X] T035 [US5] Implement fallback rate tracking in backend/app/services/agentic_query_service.py to measure search API impact on OpenSearch fallback reduction (ALREADY IMPLEMENTED)

- [X] T036 [US5] Add search tool adoption metrics in backend/app/tools/tool_registry.py to track which search tools are used most frequently

**Checkpoint**: Search APIs documented and metrics collection in place

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Repository)**: Can start immediately (no dependencies within agentic query feature)
- **Phase 2 (Endpoints)**: Depends on Phase 1 completion
- **Phase 3 (Tools)**: Depends on Phase 2 completion
- **Phase 4 (Agents)**: Depends on Phase 3 completion
- **Phase 5 (Testing)**: Depends on Phase 4 completion
- **Phase 6 (Docs)**: Depends on Phase 5 completion

### Within Each Phase

- **Phase 1**: All 6 repository methods can be implemented in parallel (T001-T006 marked [P])
- **Phase 2**: Endpoints must be sequential (each depends on corresponding repository method)
- **Phase 3**: All 6 tool registrations can be done in parallel (T013-T018 marked [P])
- **Phase 4**: Agent updates can be done sequentially (different agents, but same pattern)
- **Phase 5**: Repository tests can be parallel (T024-T029 marked [P]), then endpoint/tool/agent tests sequentially
- **Phase 6**: Documentation tasks can be parallel (T033-T034 marked [P])

### Parallel Opportunities

```bash
# Phase 1: Launch all repository search methods together
Task T001: GatewayRepository.search()
Task T002: APIRepository.search()
Task T003: VulnerabilityRepository.search()
Task T004: ComplianceRepository.search()
Task T005: RecommendationRepository.search()
Task T006: PredictionRepository.search()

# Phase 3: Launch all tool registrations together
Task T013: Register search_gateways
Task T014: Register search_apis
Task T015: Register search_vulnerabilities
Task T016: Register search_compliance_violations
Task T017: Register search_recommendations
Task T018: Register search_predictions

# Phase 5: Launch all repository tests together
Task T024: Gateway repository search tests
Task T025: API repository search tests
Task T026: Vulnerability repository search tests
Task T027: Compliance repository search tests
Task T028: Recommendation repository search tests
Task T029: Prediction repository search tests

# Phase 6: Launch documentation tasks together
Task T033: Update API documentation
Task T034: Add quickstart examples
```

---

## Implementation Strategy

### Sequential Approach (Recommended)

1. **Phase 1**: Implement all 6 repository search methods in parallel → Test individually
2. **Phase 2**: Implement endpoints one at a time → Test each endpoint
3. **Phase 3**: Register all 6 tools in parallel → Verify tool availability
4. **Phase 4**: Update agent prompts sequentially → Test agent tool selection
5. **Phase 5**: Run all tests → Fix any issues
6. **Phase 6**: Complete documentation and metrics

### Validation at Each Phase

- **After Phase 1**: Test each repository search method with OpenSearch queries
- **After Phase 2**: Test each endpoint with curl/Postman
- **After Phase 3**: Verify tools appear in tool registry
- **After Phase 4**: Test agent queries that should trigger search tools
- **After Phase 5**: All automated tests passing
- **After Phase 6**: Documentation complete, metrics collecting

---

## Success Criteria (from spec.md)

**Independent Test**: Ask "Find APIs created last week with names containing 'payment' that have authentication enabled" and verify agent uses `search_apis` tool with appropriate filters

**Acceptance Scenarios** (all must pass):

1. ✅ Agent uses `search_apis` with name pattern and date range for "Find APIs with 'payment' created in last 7 days"
2. ✅ Agent uses `search_gateways` with name and status filters for "Show gateways with 'prod' that are connected"
3. ✅ Agent uses `search_vulnerabilities` with severity, date, and API name for "Find critical vulnerabilities this month affecting APIs with 'user'"
4. ✅ Agent uses `search_compliance_violations` with standard, severity, and date for "Show GDPR violations with high severity from last quarter"
5. ✅ Agent uses `search_recommendations` with type, priority, and status for "Find caching recommendations with high priority that are pending"
6. ✅ Agent uses `search_predictions` with confidence and gateway for "Show predictions with confidence >80% for production gateway"

**Metrics** (track after implementation):

- Fallback reduction: 15%+ decrease in OpenSearch fallback for complex queries
- Agent adoption: 80%+ of multi-criteria queries use search APIs
- Performance: <2 second response time for search queries
- Accuracy: 85%+ relevant results in top 20 for text searches

---

## Notes

- All search APIs follow consistent interface (query params, pagination, response format)
- OpenSearch bool queries with must/filter/should clauses for efficient filtering
- Case-insensitive text search using match or wildcard queries
- Multiple filters combined with AND logic
- Standard pagination: page/page_size (default: 20, max: 100)
- Date ranges in ISO 8601 format, UTC timezone
- FastAPI/Pydantic validation for all parameters
- Each search tool has enhanced description guiding agents on when to use it
- Search tools complement (not replace) existing list/get tools

---

## Common Pitfalls to Avoid

1. **Case-sensitive text matching**: Always use `.lower()` or OpenSearch `match` query
2. **Invalid date formats**: Use Pydantic datetime validation
3. **Incorrect pagination math**: `from = (page - 1) * page_size`
4. **Missing total count**: Always return total for pagination
5. **Empty result errors**: Return empty list with total=0, not error
6. **Forgetting tool registration**: Tools must be in `__init__.py`
7. **Inconsistent response format**: All search APIs must return same structure

---

## Task Summary

- **Total Tasks**: 36
- **Phase 1 (Repository)**: 6 tasks (all parallel)
- **Phase 2 (Endpoints)**: 6 tasks (sequential)
- **Phase 3 (Tools)**: 6 tasks (all parallel)
- **Phase 4 (Agents)**: 5 tasks (sequential)
- **Phase 5 (Testing)**: 9 tasks (6 parallel, 3 sequential)
- **Phase 6 (Docs)**: 4 tasks (2 parallel, 2 sequential)

**Parallel Opportunities**: 14 tasks can run in parallel (marked with [P])

**Estimated Effort**: 
- Phase 1: 2-3 days (parallel)
- Phase 2: 2-3 days (sequential)
- Phase 3: 1 day (parallel)
- Phase 4: 1 day (sequential)
- Phase 5: 2-3 days (mixed)
- Phase 6: 1 day (parallel)
- **Total**: 9-12 days with parallel execution

**MVP Scope**: Phases 1-4 deliver functional search APIs that agents can use. Phases 5-6 add testing and documentation.