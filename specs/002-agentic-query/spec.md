# Feature Specification: Agentic Natural Language Query Service

**Feature Branch**: `001-agentic-query`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "Create spec for query feature enhancement. I want to change the natural language query service which is now not fully agentic but rather generates opensearch query, calls the data store and returns the result. It is not stable approach and probabilistic. I would like to have the query service fully agentic. It should leverage the unified MCP server tools in its agentic workflow with multiple agents work together in an autonomous way to generate the query response. Instead, the agentic workflow should figure out the appropriate unified MCP server tools with the use of LLM and invoke the tools to get the appropriate response. Keep the existing design and implementation (opensearch query) as a fallback mechanism."

## Clarifications

### Session 2026-04-29

- Q: Should the agentic query service be deployed as a separate microservice or integrated within the existing backend? → A: Integrated within existing backend to avoid operational complexity
- Q: Should agents invoke backend operations via HTTP calls or direct function calls? → A: Direct function calls to backend router methods to preserve validation logic and avoid network overhead
- Q: Should the query UI be separated into a dedicated frontend service? → A: Keep in main frontend to maintain shared dependencies and consistent UX
- Q: Should we use Micro Frontend (MFE) architecture? → A: No - single SPA is sufficient for current scale

### Session 2026-05-02

- Q: Your first observation highlights that agents return raw tool results without proper aggregation. For "What are the insecure APIs", the system returns "40 vulnerabilities" instead of "8 APIs with vulnerabilities". How should the system synthesize and aggregate results from tool invocations? → A: LLM-powered synthesis with entity grouping - LLM analyzes tool results, groups by entities (e.g., vulnerabilities → APIs), and generates natural language responses matching user intent
- Q: Your second observation highlights that the Coordinator agent makes all decisions upfront in a single pass, rather than iteratively evaluating intermediate results. For "Show APIs managed by gateway 'local'", should the coordinator first resolve the gateway name, then use that result to query APIs? How should the coordinator handle multi-step reasoning? → A: Iterative reasoning loop (RECOMMENDED) - Industry-standard agentic pattern where coordinator evaluates after EACH tool invocation, decides if more information is needed, and dynamically invokes additional agents/tools based on intermediate results. This is how production agentic systems (AutoGPT, LangChain agents) work - they continuously ask "what do I know?" and "what do I need next?" after each step.
- Q: For the iterative reasoning loop, what should be the maximum number of iterations before the coordinator stops to prevent infinite loops? This is critical for production stability. → A: 10 iterations (RECOMMENDED) - Industry standard for agentic systems. Allows complex multi-step queries while preventing runaway loops. Most queries complete in 2-3 iterations.
- Q: When the coordinator invokes a specialized agent and receives results, should the agent itself perform LLM-powered synthesis/grouping before returning to the coordinator, or should the coordinator handle all synthesis after collecting results from multiple agents? → A: Agent-level synthesis (RECOMMENDED) - Each specialized agent uses LLM to synthesize and group its own tool results before returning to coordinator. This distributes the synthesis workload, enables domain-specific grouping logic, and provides cleaner interfaces between agents.
- Q: For the iterative coordinator reasoning, when should the coordinator decide to stop iterating? What completion criteria should trigger the end of the reasoning loop? → A: LLM-based completion decision (RECOMMENDED) - After each iteration, LLM evaluates if sufficient information has been gathered to answer the user's query. Stops when LLM determines answer is complete or max iterations reached.

### Session 2026-05-05

- Q: When remediation or optimization policy application is proposed for a gateway, should users be able to adjust recommended default policy values before execution? → A: Yes - users should be able to review generated default values, manually adjust supported policy fields, and provide manual analysis/rationale before the policy is applied
- Q: Should the system continue to support immediate execution using generated defaults? → A: Yes - retain quick apply/remediate with generated defaults, but add a review-and-customize flow for supported security and optimization actions
- Q: How should user-provided remediation changes be governed? → A: Persist the generated defaults, final applied values, changed fields, and manual analysis notes as part of remediation action history for auditability

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Agentic Query Execution (Priority: P1)

Users can ask natural language questions about their API infrastructure and receive accurate answers through an autonomous agent workflow that intelligently selects and invokes the appropriate MCP server tools.

**Why this priority**: This is the core value proposition - transforming the query service from a probabilistic OpenSearch query generator to a reliable, tool-using agent system. This delivers immediate value by improving query accuracy and reliability.

**Independent Test**: Can be fully tested by submitting queries like "Show me all APIs with critical vulnerabilities" and verifying that the agent autonomously selects the correct MCP tools (e.g., `list_vulnerabilities` with severity filter) and returns accurate results without requiring OpenSearch query generation.

**Acceptance Scenarios**:

1. **Given** a user asks "What APIs have critical security vulnerabilities?", **When** the agentic query service processes the request, **Then** the system autonomously invokes the `list_all_vulnerabilities` MCP tool with `severity=critical` filter and returns a natural language response with the results
2. **Given** a user asks "Show me performance metrics for API xyz-123", **When** the query is processed, **Then** the agent identifies the API ID, invokes `get_api_metrics` MCP tool, and presents the metrics in a user-friendly format
3. **Given** a user asks "Which gateways are currently unhealthy?", **When** the query is processed, **Then** the agent invokes `list_gateways` with `status=error` filter and returns the list of unhealthy gateways
4. **Given** a complex query requiring multiple data sources, **When** the agent processes it, **Then** the system orchestrates multiple MCP tool calls in the correct sequence and synthesizes the results

---

### User Story 2 - Multi-Agent Collaboration (Priority: P2)

Users can ask complex questions that require coordination between multiple specialized agents, each responsible for different aspects of the API intelligence platform (discovery, metrics, prediction, security, compliance, optimization).

**Why this priority**: This enables handling sophisticated queries that span multiple domains, significantly expanding the system's capabilities beyond simple single-tool invocations.

**Independent Test**: Can be tested by asking "Show me all APIs with high latency that also have security vulnerabilities" and verifying that multiple agents collaborate - one querying metrics, another querying security findings, and a coordinator synthesizing the results.

**Acceptance Scenarios**:

1. **Given** a user asks "Which APIs have both performance issues and security vulnerabilities?", **When** the query is processed, **Then** a coordinator agent orchestrates calls to both metrics and security agents, correlates results by API ID, and returns the intersection
2. **Given** a user asks "What's the compliance status of my slowest APIs?", **When** processed, **Then** the performance agent identifies slow APIs, the compliance agent checks their status, and results are merged
3. **Given** a user asks for optimization recommendations for vulnerable APIs, **When** processed, **Then** security and optimization agents collaborate to provide targeted recommendations
4. **Given** agents encounter conflicting or incomplete data, **When** synthesizing results, **Then** the coordinator agent handles conflicts gracefully and provides clear explanations

---

### User Story 3 - Intelligent Fallback to OpenSearch (Priority: P3)

When the agentic workflow cannot determine appropriate MCP tools or encounters errors, the system automatically falls back to the existing OpenSearch query generation approach to ensure query continuity.

**Why this priority**: This provides a safety net ensuring the system remains functional even when the agentic approach fails, maintaining backward compatibility and reliability.

**Independent Test**: Can be tested by submitting queries that don't map to available MCP tools (e.g., custom aggregations) and verifying the system gracefully falls back to OpenSearch query generation with appropriate logging.

**Acceptance Scenarios**:

1. **Given** a user asks a query that cannot be mapped to available MCP tools, **When** the agent workflow fails to identify appropriate tools, **Then** the system automatically falls back to OpenSearch query generation and logs the fallback reason
2. **Given** MCP tool invocation fails due to backend unavailability, **When** the error is detected, **Then** the system retries with OpenSearch approach and notifies the user of degraded mode
3. **Given** a query requires custom aggregations not supported by MCP tools, **When** the agent recognizes this limitation, **Then** it proactively chooses the OpenSearch path
4. **Given** fallback occurs, **When** generating the response, **Then** the system includes metadata indicating fallback mode and confidence score

---

### User Story 4 - Conversational Context Awareness (Priority: P2)

Users can have multi-turn conversations where follow-up questions reference previous queries, and the agentic system maintains context to understand references like "those APIs" or "the vulnerable ones".

**Why this priority**: This significantly improves user experience by enabling natural conversations rather than requiring fully-specified queries each time.

**Independent Test**: Can be tested by asking "Show me all APIs" followed by "Which of those have vulnerabilities?" and verifying the agent correctly resolves "those" to the APIs from the previous query.

**Acceptance Scenarios**:

1. **Given** a user asks "Show me all APIs in gateway xyz", **When** they follow up with "Which ones have high latency?", **Then** the agent resolves "ones" to the APIs from the previous query and filters by latency
2. **Given** a user asks "List critical vulnerabilities", **When** they ask "What APIs are affected?", **Then** the agent maintains context and queries APIs related to those vulnerabilities
3. **Given** a multi-turn conversation, **When** the user asks "Show me more details", **Then** the agent understands the context and provides deeper information about the last discussed entity
4. **Given** context becomes stale or ambiguous, **When** the agent cannot resolve references, **Then** it asks clarifying questions rather than making incorrect assumptions

---

### User Story 5 - Enhanced Search APIs for Flexible Querying (Priority: P2)

Users benefit from comprehensive search capabilities across all feature categories when existing list/get tools are insufficient for complex filtering requirements, enabling agents to perform flexible searches using multiple criteria.

**Why this priority**: Current tools like `list_gateways`, `list_all_apis`, `list_all_vulnerabilities` provide basic filtering, but agents need more flexible search capabilities when users ask complex queries with multiple filter combinations. Search APIs expand agent capabilities without requiring OpenSearch fallback.

**Independent Test**: Can be tested by asking "Find APIs created last week with names containing 'payment' that have authentication enabled" and verifying the agent uses `search_apis` tool with appropriate filters rather than falling back to OpenSearch or using multiple list operations.

**Acceptance Scenarios**:

1. **Given** a user asks "Find all APIs with names containing 'payment' that were created in the last 7 days", **When** the query is processed, **Then** the agent invokes `search_apis` with name pattern and date range filters
2. **Given** a user asks "Show me gateways with 'prod' in their name that are currently connected", **When** processed, **Then** the agent uses `search_gateways` with name filter and status filter
3. **Given** a user asks "Find critical vulnerabilities discovered this month affecting APIs with 'user' in the name", **When** processed, **Then** the agent uses `search_vulnerabilities` with severity, date range, and API name filters
4. **Given** a user asks "Show me compliance violations for GDPR standard with high severity from last quarter", **When** processed, **Then** the agent uses `search_compliance_violations` with standard, severity, and date filters
5. **Given** a user asks "Find optimization recommendations for caching with high priority that are still pending", **When** processed, **Then** the agent uses `search_recommendations` with type, priority, and status filters
6. **Given** a user asks "Show me failure predictions with confidence above 80% for APIs in production gateway", **When** processed, **Then** the agent uses `search_predictions` with confidence threshold and gateway filters

---

### User Story 6 - Iterative Multi-Step Coordinator Reasoning (Priority: P1)

Users benefit from a coordinator agent that iteratively reasons about which agents and tools to invoke, checking after each step whether additional information is needed, rather than making all decisions upfront in a single pass.

**Why this priority**: This is fundamental to achieving true agentic behavior. Industry-standard agentic systems use iterative reasoning loops where the coordinator continuously evaluates "what do I know now?" and "what do I need next?" after each tool invocation, enabling dynamic adaptation to intermediate results.

**Independent Test**: Can be tested by asking "Show the APIs managed by gateway 'local'" and verifying the coordinator first invokes discovery agent to get gateway ID, then uses that ID to invoke discovery agent again for APIs. Similarly, "Show insecure APIs managed by gateway 'local'" should show coordinator chaining discovery → security agents.

**Acceptance Scenarios**:

1. **Given** a user asks "Show the APIs managed by gateway 'local'", **When** the coordinator processes this, **Then** it first invokes discovery agent to resolve gateway name to ID, evaluates the result, then invokes discovery agent again with gateway_id to fetch APIs
2. **Given** a user asks "Show the insecure APIs managed by gateway 'local'", **When** processed, **Then** the coordinator first resolves gateway name to ID, then invokes security agent with that gateway_id to fetch vulnerabilities, groups by API, and returns affected APIs
3. **Given** a user asks "What are the compliance violations for APIs with high latency?", **When** processed, **Then** the coordinator first invokes metrics agent to identify high-latency APIs, evaluates which APIs were found, then invokes compliance agent with those specific API IDs
4. **Given** intermediate tool results are insufficient, **When** the coordinator evaluates them, **Then** it autonomously decides to invoke additional tools with refined parameters based on what was learned
5. **Given** a multi-step query where early steps fail, **When** the coordinator detects the failure, **Then** it adapts its strategy by trying alternative tools or agents rather than proceeding with incomplete information

---

### User Story 7 - Remediation Policy Review and Manual Override (Priority: P2)

Users can review generated remediation or optimization policy values before gateway application, adjust supported fields, and provide manual analysis so the final policy matches operational and security requirements without requiring code changes.

**Why this priority**: The system can identify the right policy type, but fixed default values are often not appropriate for every API, gateway, or environment. Allowing human review and targeted overrides improves safety, usability, and governance while preserving automation.

**Independent Test**: Can be tested by selecting a security vulnerability or optimization recommendation, opening a policy review flow, changing one or more generated values, submitting the action, and verifying that the final applied policy and manual analysis are recorded in the remediation history.

**Acceptance Scenarios**:

1. **Given** a user initiates remediation for a rate-limiting security finding, **When** the system presents generated default values, **Then** the user can adjust supported fields such as limits, burst allowance, and enforcement behavior before applying the policy
2. **Given** a user initiates an optimization recommendation for caching, **When** the system presents a review flow, **Then** the user can modify supported cache settings such as TTL and key strategy and submit the revised policy for application
3. **Given** a user accepts the generated defaults without changes, **When** the policy is applied, **Then** the system records that the default configuration was used and completes the action without requiring manual edits
4. **Given** a user overrides one or more generated values, **When** the policy is applied, **Then** the system records the generated defaults, final applied values, changed fields, and manual analysis notes in the remediation history
5. **Given** a user provides an invalid override combination, **When** the system validates the policy before execution, **Then** the user receives clear validation feedback and the policy is not applied until the input is corrected
6. **Given** a gateway vendor does not support one or more editable fields, **When** the review flow is displayed, **Then** unsupported fields are clearly identified and cannot be submitted as editable overrides

---

### Edge Cases

- What happens when multiple MCP tools could satisfy a query but with different trade-offs (e.g., `list_apis` vs `search_apis`)? Agent should prefer search APIs when complex filtering is needed.
- How does the system handle queries that require real-time data when MCP tools return cached results?
- What happens when an agent workflow times out or gets stuck in a loop?
- How does the system handle queries in languages other than English?
- What happens when MCP server tools return partial failures (some succeed, some fail)?
- How does the system handle queries that require data not exposed by any MCP tool?
- What happens when the LLM generates invalid tool parameters or tool names?
- How does the system handle rate limiting from the MCP server or backend?
- What happens when the coordinator needs to invoke the same agent multiple times with different parameters based on intermediate results?
- How does the system prevent infinite loops when the coordinator keeps invoking tools without making progress?
- What happens when generated remediation defaults are too strict or too permissive for a specific API workload?
- What happens when a user overrides only some fields and the remaining fields should continue using generated defaults?
- What happens when user-supplied remediation values are valid in general but not supported by the selected gateway vendor?
- What happens when a user wants fast execution and chooses not to review policy details before remediation?
- What happens when a user submits manual analysis notes but no actual policy changes?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement a multi-agent architecture with specialized agents for different domains (discovery, metrics, security, compliance, optimization, predictions)
- **FR-002**: System MUST use LLM-based reasoning to map natural language queries to appropriate MCP server tool invocations
- **FR-003**: System MUST support autonomous tool selection where agents decide which MCP tools to invoke without hardcoded rules
- **FR-004**: System MUST implement a coordinator agent that orchestrates collaboration between specialized agents
- **FR-005**: System MUST maintain conversational context across multiple query turns within a session
- **FR-006**: System MUST automatically fall back to OpenSearch query generation when agentic workflow fails or is inappropriate
- **FR-007**: System MUST log all agent decisions, tool invocations, and fallback triggers for observability
- **FR-008**: System MUST validate MCP tool parameters before invocation to prevent errors
- **FR-009**: System MUST handle MCP tool failures gracefully with retry logic and error recovery
- **FR-010**: System MUST synthesize results from multiple tool calls into coherent natural language responses
- **FR-011**: System MUST track confidence scores for agent decisions and tool selections
- **FR-012**: System MUST support parallel tool invocation when queries can be decomposed into independent sub-queries
- **FR-013**: System MUST implement timeout mechanisms to prevent infinite agent loops
- **FR-014**: System MUST preserve existing query API endpoints and response formats for backward compatibility
- **FR-015**: System MUST provide metadata in responses indicating whether agentic or fallback mode was used
- **FR-016**: System MUST provide search API endpoints for each feature category (gateways, APIs, vulnerabilities, compliance violations, recommendations, predictions) supporting flexible multi-criteria filtering
- **FR-017**: Search APIs MUST support common search patterns including text matching (name, description), status filtering, date range filtering, severity/priority filtering, and pagination
- **FR-018**: Search APIs MUST return results in the same format as corresponding list endpoints for consistency
- **FR-019**: Agents MUST be able to use search APIs when list/get tools are insufficient for complex filtering requirements
- **FR-020**: Search APIs MUST be registered as tools in the tool registry and made available to appropriate specialized agents
- **FR-021**: Coordinator agent MUST use iterative reasoning loops to evaluate intermediate results and decide next steps, rather than planning all steps upfront
- **FR-022**: Coordinator agent MUST be able to invoke the same specialized agent multiple times with different parameters based on intermediate results
- **FR-023**: Coordinator agent MUST evaluate after each tool invocation whether sufficient information has been gathered or additional tools are needed
- **FR-024**: System MUST implement loop detection to prevent infinite coordinator reasoning cycles (max iterations: 10)
- **FR-025**: Specialized agents MUST use LLM-powered synthesis to aggregate and group tool results by entities (e.g., vulnerabilities → APIs) before returning to coordinator
- **FR-026**: System MUST generate natural language responses that match user intent by understanding entity relationships (e.g., "8 APIs with vulnerabilities" not "40 vulnerabilities")
- **FR-027**: System MUST generate a reviewable policy draft for supported Security and Optimization remediation actions before gateway application
- **FR-028**: System MUST allow users to override supported generated policy fields for remediation and optimization actions before execution
- **FR-029**: System MUST validate user-supplied override values and reject invalid or unsupported combinations before policy application
- **FR-030**: System MUST preserve an immediate execution path that applies generated default values without requiring manual review
- **FR-031**: System MUST support a review-and-customize path that lets users inspect generated defaults, submit manual analysis, and apply a revised policy
- **FR-032**: System MUST record the generated default policy, final applied policy, changed fields, and manual analysis notes in remediation action history for auditability
- **FR-033**: System MUST identify which policy fields are editable, non-editable, or unsupported for the selected remediation type and gateway context
- **FR-034**: System MUST preserve generated default values for all fields not explicitly overridden by the user
- **FR-035**: System MUST prevent submission of override fields that are not applicable to the selected remediation or optimization action type
- **FR-036**: System MUST present clear feedback when gateway-specific support limitations prevent one or more override fields from being applied

### Key Entities

- **AgenticQueryService**: Orchestrates the agentic workflow, manages agent lifecycle, and coordinates with MCP server
- **SpecializedAgent**: Domain-specific agent (e.g., SecurityAgent, MetricsAgent) that knows which MCP tools to use for its domain and synthesizes tool results using LLM
- **CoordinatorAgent**: Meta-agent that uses iterative reasoning to decompose queries, orchestrate specialized agents, evaluate intermediate results, and decide next steps dynamically
- **MCPToolRegistry**: Registry of available MCP server tools with their schemas and capabilities
- **QueryContext**: Maintains conversational state including previous queries, entities mentioned, and resolved references
- **AgentDecision**: Records agent reasoning, tool selection rationale, and confidence scores
- **ToolInvocation**: Represents a call to an MCP tool with parameters, results, and execution metadata
- **FallbackTrigger**: Records when and why the system fell back to OpenSearch approach
- **SearchCriteria**: Represents flexible search parameters including text patterns, filters, date ranges, and pagination options
- **CoordinatorState**: Tracks coordinator's iterative reasoning state including steps completed, intermediate results, and next actions to evaluate
- **EntityGrouping**: Represents aggregated results grouped by entity type (e.g., APIs, gateways) with associated metadata from multiple tool invocations
- **PolicyDraft**: Represents the generated default remediation or optimization policy proposed for a gateway action, including editable fields, unsupported fields, and validation metadata
- **PolicyOverrideSubmission**: Represents user-supplied policy changes and manual analysis notes submitted before remediation or optimization execution
- **ManualAnalysisRecord**: Represents the user rationale, review context, and change summary associated with a customized remediation action

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Query accuracy improves by at least 40% compared to current OpenSearch generation approach (measured by user feedback and result relevance)
- **SC-002**: 90% of queries are successfully handled by the agentic workflow without fallback to OpenSearch
- **SC-003**: Average query response time remains under 5 seconds for single-agent queries and under 10 seconds for multi-agent queries
- **SC-004**: System maintains 99.5% uptime with graceful degradation to fallback mode when MCP server is unavailable
- **SC-005**: Users can complete 95% of follow-up queries without re-specifying context from previous queries
- **SC-006**: Agent decision confidence scores correlate with actual query success rate (>0.8 confidence = >90% success)
- **SC-007**: System handles 1000+ concurrent query sessions without performance degradation
- **SC-008**: Fallback to OpenSearch occurs in less than 10% of queries under normal operation
- **SC-009**: Multi-agent queries requiring 3+ tool invocations complete successfully 85% of the time
- **SC-010**: User satisfaction with query results increases by at least 50% (measured through feedback ratings)
- **SC-011**: Search APIs reduce fallback rate by at least 15% for queries requiring complex filtering (measured by comparing fallback rates before and after search API implementation)
- **SC-012**: Agents successfully use search APIs for 80%+ of queries requiring multi-criteria filtering without falling back to OpenSearch
- **SC-013**: Coordinator successfully resolves 90%+ of multi-step queries requiring iterative reasoning (e.g., "APIs in gateway X with vulnerabilities") without fallback
- **SC-014**: Entity grouping accuracy reaches 95%+ (e.g., correctly grouping 40 vulnerabilities into 8 affected APIs)
- **SC-015**: Iterative coordinator reasoning completes within 3 iterations for 80%+ of multi-step queries
- **SC-016**: Users can complete review-and-customize remediation for supported security and optimization actions in under 2 minutes in 90% of attempts
- **SC-017**: 100% of customized remediation executions include an auditable record of generated defaults, final applied values, and manual analysis notes
- **SC-018**: 95% of valid partial override submissions apply successfully without requiring users to re-enter unchanged default values
- **SC-019**: Validation prevents 100% of unsupported or invalid override submissions from being applied to gateways

## Assumptions *(mandatory)*

1. **MCP Server Availability**: The unified MCP server is running and accessible at all times, with health checks in place
2. **Tool Schema Stability**: MCP tool schemas remain stable or changes are versioned and backward compatible
3. **LLM Availability**: The LLM service (LiteLLM) is available and responsive for agent reasoning and tool selection
4. **Existing Infrastructure**: Current OpenSearch indices, repositories, and query infrastructure remain functional for fallback
5. **Session Management**: Query sessions are already implemented and can store conversational context
6. **Tool Coverage**: MCP server tools provide sufficient coverage for 90%+ of common query patterns
7. **Performance Budget**: Additional latency from agent reasoning (1-2 seconds) is acceptable for improved accuracy
8. **Error Handling**: Existing error handling and logging infrastructure can be extended for agent workflows
9. **Backward Compatibility**: Existing query API clients can handle new response metadata fields without breaking
10. **Search API Coverage**: Search APIs cover the 6 main feature categories (gateways, APIs, vulnerabilities, compliance, recommendations, predictions)
11. **LLM Synthesis Capability**: LLM can reliably group and aggregate tool results by entity relationships (e.g., vulnerabilities → APIs)
12. **Iterative Reasoning Performance**: Coordinator's iterative reasoning loops complete within acceptable latency budgets (2-3 iterations typical)
13. **Remediation Draft Availability**: Supported security and optimization actions can produce a deterministic default policy draft before execution
14. **User Review Permissions**: Users who can apply remediation are also permitted to review and customize supported policy values for their authorized gateways
15. **Audit Storage Capacity**: Existing remediation and recommendation history storage can retain generated defaults, applied values, and manual analysis notes without requiring a separate retention model

## Dependencies *(mandatory)*

### Internal Dependencies
- **Unified MCP Server**: Must be running with all tools operational (gateway, API, metrics, security, compliance, optimization, predictions, query tools)
- **LLM Service**: LiteLLM service must be configured and accessible for agent reasoning
- **Query Repository**: Existing query history and session management infrastructure
- **OpenSearch Infrastructure**: Must remain operational for fallback mechanism
- **Backend REST API**: All backend endpoints must be accessible to MCP server
- **Search API Endpoints**: New search endpoints must be implemented in backend routers before tool registration

### External Dependencies
- **LangChain/LangGraph**: For agent orchestration and workflow management (already in use)
- **FastMCP**: For MCP client integration to invoke tools (already in use)
- **LiteLLM**: For LLM inference across multiple providers (already in use)

### Technical Constraints
- Must maintain existing REST API contract for `/query` endpoint
- Must support existing query types and response formats
- Must work within current FastAPI async architecture
- Must integrate with existing authentication and authorization
- Must respect existing rate limiting and quota mechanisms

## Out of Scope *(mandatory)*

1. **Custom MCP Tool Creation**: Users cannot define custom MCP tools through the query interface
2. **Query Language Extensions**: No new query syntax or DSL beyond natural language
3. **Real-time Streaming**: Responses are returned as complete messages, not streamed token-by-token
4. **Multi-tenancy**: Agent workflows do not enforce tenant isolation (relies on existing backend authorization)
5. **Agent Training**: Agents use pre-trained LLMs; no custom fine-tuning or reinforcement learning
6. **Visual Query Builder**: No graphical interface for constructing queries
7. **Query Scheduling**: No support for scheduled or recurring queries
8. **External Data Sources**: Agents only access data through MCP server tools, not external APIs
9. **Query Optimization Suggestions**: System does not suggest query rewrites or optimizations
10. **Agent Customization**: Users cannot configure agent behavior or tool selection strategies
11. **Arbitrary Policy Authoring**: Users cannot create entirely new remediation policy types outside the supported Security and Optimization actions
12. **Full Vendor-Specific Authoring**: Users cannot directly edit raw vendor-native gateway payloads; customization is limited to supported reviewable fields
13. **Automated Policy Tuning**: System does not automatically optimize remediation values based on live traffic beyond generating an initial default draft

## Non-Functional Requirements *(mandatory)*

### Performance
- Agent reasoning and tool selection must complete within 2 seconds
- Single MCP tool invocation must complete within 3 seconds
- Multi-agent workflows must complete within 10 seconds
- System must support 100 concurrent agent workflows
- Memory usage per agent workflow must not exceed 100MB
- Coordinator iterative reasoning must complete within 5 seconds for typical multi-step queries
- LLM synthesis for entity grouping must complete within 1 second per agent result

### Reliability
- Agent workflow success rate must exceed 90%
- Fallback mechanism must activate within 1 second of detecting failure
- System must recover from transient MCP server failures automatically
- Agent decisions must be deterministic given the same input and context
- Coordinator loop detection must prevent infinite reasoning cycles (max 10 iterations)
- Entity grouping accuracy must exceed 95% for common entity relationships

### Observability
- All agent decisions must be logged with reasoning traces
- Tool invocations must be logged with parameters and results
- Fallback triggers must be logged with root cause analysis
- Performance metrics must be collected for each agent and tool
- Confidence scores must be tracked and correlated with outcomes
- Coordinator reasoning steps must be logged with intermediate results and decisions
- Entity grouping operations must be logged with input/output entity counts

### Security
- Agent workflows must respect existing authentication and authorization
- Tool parameters must be validated to prevent injection attacks
- Sensitive data in tool responses must be masked in logs
- Agent reasoning must not expose internal system details to users
- Manual analysis notes and remediation override history must respect existing authorization rules and only be visible to authorized users
- Review-and-customize remediation flows must validate all user-entered values before execution and prevent unsupported field injection

### Maintainability
- Agent logic must be modular and independently testable
- Tool registry must support dynamic updates without code changes
- Fallback mechanism must be independently testable
- Agent workflows must be debuggable with detailed trace logs
- Coordinator reasoning logic must be testable with mock intermediate results
- Entity grouping logic must be testable with synthetic tool results
- Policy draft generation, partial override merging, and remediation audit recording must be independently testable for supported security and optimization actions
