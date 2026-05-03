# api-intelligence-plane-v2 Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-05-02

## Active Technologies
- OpenSearch 2.11+ for all data types (API inventory, metrics, predictions, security findings, compliance violations, optimization recommendations, transactional logs) (001-api-intelligence-plane)
- Python 3.11+ + FastAPI 0.109+, LangChain 0.1+, LangGraph 0.0.20+, LiteLLM 1.17+ (001-agentic-query)
- OpenSearch 2.11+ (for fallback queries and data storage) (001-agentic-query)
- Python 3.11+ + FastAPI 0.109+, LangChain 0.1+, LangGraph 0.0.20+, LiteLLM 1.17+, FastMCP 0.1+ (002-agentic-query) ✅ 89% COMPLETE
- OpenSearch 2.11+ (for fallback queries and query history) (002-agentic-query)

### Backend (Python 3.11+)
- **Framework**: FastAPI 0.109+
- **AI/ML**: LangChain 0.1+, LangGraph 0.0.20+, LiteLLM 1.17+
- **MCP**: FastMCP 0.1+
- **Database**: OpenSearch Python Client 2.4+
- **Scheduling**: APScheduler 3.10+
- **Testing**: pytest 7.4+, pytest-asyncio 0.21+
- **Code Quality**: Black, isort, flake8, mypy

### Frontend (TypeScript/React)
- **Framework**: React 18.2+, Vite 5.0+
- **Routing**: React Router 6.20+
- **State Management**: TanStack Query 5.14+
- **UI Components**: Tailwind CSS 3.4+
- **Charts**: Recharts 2.10+
- **HTTP Client**: Axios 1.6+
- **Code Quality**: ESLint 8.56+, Prettier 3.1+, TypeScript 5.3+

### MCP Servers (Python 3.11+)
- **Framework**: FastMCP 0.1+
- **Transport**: Streamable HTTP
- **Database**: OpenSearch Python Client 2.4+

### Infrastructure
- **Container**: Docker 24+, Docker Compose 2.23+
- **Orchestration**: Kubernetes 1.28+
- **Storage**: OpenSearch 2.11+
- **Monitoring**: Prometheus, Grafana

## Project Structure

```text
api-intelligence-plane-v2/
├── backend/              # FastAPI backend service
│   ├── app/
│   │   ├── api/         # REST API endpoints (v1)
│   │   ├── models/      # Pydantic models
│   │   ├── services/    # Business logic
│   │   ├── agents/      # LangChain/LangGraph agents
│   │   ├── adapters/    # Gateway adapters (Strategy pattern)
│   │   ├── db/          # OpenSearch client and repositories
│   │   ├── scheduler/   # APScheduler jobs
│   │   ├── middleware/  # FastAPI middleware
│   │   └── utils/       # Utility functions
│   ├── tests/           # Integration and E2E tests
│   └── scripts/         # Utility scripts
├── frontend/            # React.js frontend
│   └── src/
│       ├── components/  # Reusable components
│       ├── pages/       # Page components
│       ├── services/    # API client services
│       ├── hooks/       # Custom React hooks
│       └── types/       # TypeScript types
├── mcp-servers/         # MCP server (FastMCP)
│   ├── unified_server.py    # Unified MCP server (all functionality)
│   └── common/              # Shared utilities
├── tests/               # Cross-component tests
├── config/              # Configuration files
├── k8s/                 # Kubernetes manifests
├── docs/                # Documentation
└── specs/               # Feature specifications
```

## Commands

### Backend
```bash
# Development
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testing
pytest tests/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v

# Code Quality
black app/ tests/
isort app/ tests/
flake8 app/ tests/
mypy app/
```

### Frontend
```bash
# Development
cd frontend
npm install
npm run dev

# Build
npm run build
npm run preview

# Testing
npm test
npm run test:coverage

# Code Quality
npm run lint
npm run format
npm run type-check
```

### MCP Server
```bash
# Development

## Agentic Query Patterns (Feature: 001-agentic-query) - FULLY AGENTIC UPDATE (2026-05-01)

### 🚀 NO KEYWORD MATCHING - Pure LLM Reasoning!

The agentic query service now uses **LLM reasoning for ALL decisions**. Gone are the days of keyword matching and text patterns!

**What Changed**:
- ❌ **REMOVED**: `KEYWORD_MAP` dictionary with hardcoded keywords
- ❌ **REMOVED**: Keyword-based agent selection in `analyze_query()`
- ❌ **REMOVED**: Keyword-based query decomposition in `decompose_query()`
- ✅ **ADDED**: LLM-powered agent selection with structured outputs
- ✅ **ADDED**: LLM-powered query decomposition for multi-agent workflows
- ✅ **UPDATED**: Fallback thresholds to realistic production values (0.6 confidence, 0.5 failure rate)

### Architecture Overview

**Coordinator Agent** uses LLM with structured Pydantic outputs:

```python
# LLM selects agent with reasoning
class AgentSelectionDecision(BaseModel):
    selected_agent: str  # LLM chooses: discovery, metrics, security, etc.
    confidence: float    # LLM's confidence score (0.0-1.0)
    reasoning: str       # LLM explains its choice

# LLM decomposes complex queries
class MultiAgentDecomposition(BaseModel):
    is_multi_agent: bool              # LLM decides if multiple agents needed
    required_agents: List[str]        # LLM identifies which agents
    execution_strategy: str           # LLM chooses: "parallel" or "sequential"
    reasoning: str                    # LLM explains decomposition
    sub_queries: Dict[str, str]       # LLM creates sub-query for each agent
```

**Specialized Agents** use LangChain's `create_agent()` for autonomous tool selection:
- Discovery Agent: API and gateway queries
- Metrics Agent: Performance and analytics queries
- Security Agent: Vulnerability and security queries
- Compliance Agent: Regulatory compliance queries
- Optimization Agent: Recommendation queries
- Prediction Agent: Failure prediction queries

### Decision Flow - Fully Autonomous

```
User: "Show me APIs with high latency that have security vulnerabilities"
    ↓
Coordinator Agent
    ↓
[LLM Decision 1: Multi-agent needed?]
    → YES: Requires metrics + security agents
    ↓
[LLM Decision 2: Parallel or Sequential?]
    → PARALLEL: No dependencies between agents
    ↓
[LLM Decision 3: Sub-queries for each agent]
    → Metrics Agent: "Find APIs with high latency"
    → Security Agent: "Find APIs with vulnerabilities"
    ↓
Metrics Agent (LangChain create_agent)
    ↓
[LLM Decision 4: Which tools? How many times?]
    → Invokes: get_api_metrics, list_all_apis
    → Stops when: Sufficient data gathered
    ↓
Security Agent (LangChain create_agent)
    ↓
[LLM Decision 5: Which tools? How many times?]
    → Invokes: list_all_vulnerabilities, get_vulnerability
    → Stops when: All vulnerabilities found
    ↓
Coordinator Agent
    ↓
[LLM Decision 6: Correlate results by API ID]
    → Matches APIs from both agents
    ↓
[LLM Decision 7: Synthesize natural language response]
    → "Found 3 APIs with both high latency and vulnerabilities..."
```

### LLM Prompts for Decision Making

**Agent Selection Prompt**:
```
You are an intelligent coordinator that analyzes user queries and selects 
the most appropriate specialized agent.

Available agents:
1. discovery: APIs, gateways, inventory
2. metrics: Performance, latency, throughput
3. security: Vulnerabilities, threats
4. compliance: Regulatory requirements
5. optimization: Recommendations, efficiency
6. prediction: Failure forecasts

Analyze: "{user_query}"
Context: {previous_queries}

Return JSON:
{
  "selected_agent": "security",
  "confidence": 0.95,
  "reasoning": "Query asks about vulnerabilities..."
}
```

**Query Decomposition Prompt**:
```
Determine if this query requires multiple agents working together.

Query: "{user_query}"

Does it need multiple agents? (e.g., "APIs with high latency AND vulnerabilities" 
needs metrics + security)

Return JSON:
{
  "is_multi_agent": true,
  "required_agents": ["metrics", "security"],
  "execution_strategy": "parallel",
  "reasoning": "Query requires both performance and security data",
  "sub_queries": {
    "metrics": "Find APIs with high latency",
    "security": "Find APIs with vulnerabilities"
  }
}
```

### Fallback Mechanism - Realistic Thresholds

Fallback to OpenSearch triggers when:
- **Confidence < 0.6**: LLM not confident in agent/tool selection
- **Tool Failure Rate > 50%**: More than half of tool invocations failed
- **Timeout > 10s**: Workflow taking too long
- **No Tools Found**: LLM couldn't identify appropriate tools
- **LLM Unavailable**: LLM service down or rate-limited

### Benefits of Fully Agentic Approach

1. **Adaptive**: Handles new query patterns without code changes
2. **Explainable**: LLM provides reasoning for every decision
3. **Robust**: Graceful fallback when LLM uncertain
4. **Scalable**: No manual keyword maintenance
5. **Accurate**: LLM understands context and nuance better than regex
6. **Autonomous**: LLM decides when to stop invoking tools
7. **Intelligent**: LLM synthesizes results from multiple agents

### Example: Fully Agentic Query Execution

```python
# User query
query = "Which APIs have both performance issues and security vulnerabilities?"

# Step 1: LLM decomposes query
decomposition = await coordinator.decompose_query(query)
# LLM decides: is_multi_agent=True, required_agents=["metrics", "security"]

# Step 2: LLM determines execution strategy
# LLM decides: execution_strategy="parallel" (no dependencies)

# Step 3: Each agent uses LLM to select tools
metrics_agent = await metrics_agent.execute("Find APIs with performance issues")
# LLM selects tools: get_api_metrics, list_all_apis
# LLM decides when to stop: After gathering sufficient performance data

security_agent = await security_agent.execute("Find APIs with vulnerabilities")
# LLM selects tools: list_all_vulnerabilities, get_vulnerability
# LLM decides when to stop: After finding all vulnerabilities

# Step 4: LLM correlates results
correlated = coordinator.correlate_results_by_entity(agent_results)
# LLM matches APIs by ID across both agents

# Step 5: LLM synthesizes response
response = await coordinator.generate_multi_agent_response(query, correlated)
# LLM creates: "Found 3 APIs with both high latency and critical vulnerabilities..."
```

### Migration from Keyword Matching

**Before (Keyword Matching)**:
```python
KEYWORD_MAP = {
    AgentType.SECURITY: ["security", "vulnerability", "risk", "threat"],
    AgentType.METRICS: ["latency", "performance", "slow"],
    # ... hardcoded keywords
}

# Probabilistic matching
for agent_type, keywords in KEYWORD_MAP.items():
    hits = [kw for kw in keywords if kw in query.lower()]
    if len(hits) > best_score:
        best_agent = agent_type  # ❌ Fragile!
```

**After (LLM Reasoning)**:
```python
# LLM analyzes query with full context understanding
decision = await llm.ainvoke([
    SystemMessage("You are an expert at selecting the right agent..."),
    HumanMessage(f"Analyze: {query}")
])

# Structured output with reasoning
agent_selection = AgentSelectionDecision(**decision)
# ✅ Adaptive, explainable, robust!
```

cd mcp-servers
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python unified_server.py
```

### Docker
```bash
# Local Development
docker-compose up -d
docker-compose logs -f

# Production
docker-compose -f docker-compose.prod.yml up -d

# Rebuild
docker-compose build --no-cache
```

## Code Style

### Python (Backend & MCP Servers)
- **Formatter**: Black (line length: 100)
- **Import Sorting**: isort (profile: black)
- **Linter**: flake8 (max-line-length: 100)
- **Type Checking**: mypy (strict mode)
- **Docstrings**: Google style
- **Naming**: snake_case for functions/variables, PascalCase for classes

### TypeScript/JavaScript (Frontend)
- **Formatter**: Prettier (semi: false, singleQuote: true)
- **Linter**: ESLint (extends: recommended, typescript-eslint)
- **Style Guide**: Airbnb TypeScript
- **Naming**: camelCase for functions/variables, PascalCase for components/classes

## Architecture Patterns

### Backend
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic separation
- **Strategy Pattern**: Gateway adapters for multi-vendor support
- **Dependency Injection**: FastAPI dependencies
- **Agent Pattern**: LangChain/LangGraph for AI workflows
- **Policy Conversion Pattern**: Unified normalizer/denormalizer for vendor-neutral policy configs
  - **Normalizer**: Vendor-specific → Vendor-neutral (structured Pydantic configs)
  - **Denormalizer**: Vendor-neutral → Vendor-specific (supports both dict and structured)
  - **Location**: `backend/app/utils/{vendor}/policy_normalizer.py` and `policy_denormalizer.py`
  - **Benefits**: Type safety, single source of truth, backward compatibility

### Frontend
- **Component-Based**: Reusable React components
- **Custom Hooks**: Shared logic extraction
- **Service Layer**: API client abstraction
- **State Management**: TanStack Query for server state

### Security
- **Encryption**: TLS 1.3 for all communications
- **Cryptography**: FIPS 140-3 compliant algorithms
- **Secrets**: Environment variables, never hardcoded
- **Audit Logging**: All operations logged

## Performance Targets

- Query latency: <5 seconds for natural language queries
- Discovery cycles: Complete within 5 minutes
- Security scans: Complete within 1 hour
- API support: 1000+ APIs
- Data retention: 90 days
- Concurrent requests: Support millions per minute

## Testing Strategy

- **Integration Tests**: Cross-component testing (required)
- **E2E Tests**: Complete workflow validation (required)
- **Unit Tests**: Not required per project specification
- **Mock Data**: Fixtures for testing scenarios
- **Coverage**: Focus on integration and E2E coverage

## Recent Changes
- 002-agentic-query: Added Python 3.11+ + FastAPI 0.109+, LangChain 0.1+, LangGraph 0.0.20+, LiteLLM 1.17+, FastMCP 0.1+
- 001-agentic-query: Added Python 3.11+ + FastAPI 0.109+, LangChain 0.1+, LangGraph 0.0.20+, LiteLLM 1.17+
## Agent Parameter Interpretation Enhancement (2026-05-01)

### Overview

Enhanced all specialized agents with explicit parameter interpretation guidance to improve natural language query accuracy. This addresses the issue where agents were not correctly mapping natural language phrases to tool parameter values.

### Implementation Status: ✅ Complete

All 5 specialized agents have been updated with enhanced system prompts:

1. **Security Agent** ([`backend/app/agents/query/security_agent.py`](backend/app/agents/query/security_agent.py))
   - Added severity interpretation: "critical vulnerabilities" → `severity="critical"`
   - Added status interpretation: "open vulnerabilities" → `status="open"`
   - Added entity filtering guidance for API vs gateway vulnerabilities

2. **Metrics Agent** ([`backend/app/agents/query/metrics_agent.py`](backend/app/agents/query/metrics_agent.py))
   - Added performance interpretation: "slow APIs" → `latency_threshold > 500ms`
   - Added time range interpretation: "last hour" → `time_range: now-1h to now`
   - Added comparison operators: "greater than X" → `gt=X or gte=X`

3. **Compliance Agent** ([`backend/app/agents/query/compliance_agent.py`](backend/app/agents/query/compliance_agent.py))
   - Added compliance status: "compliant APIs" → `compliance_status="compliant"`
   - Added regulation mapping: "GDPR" → `regulation_type="GDPR"`
   - Added violation severity: "critical violations" → `severity="critical"`

4. **Optimization Agent** ([`backend/app/agents/query/optimization_agent.py`](backend/app/agents/query/optimization_agent.py))
   - Added recommendation status: "pending recommendations" → `status="pending"`
   - Added optimization types: "caching recommendations" → `optimization_type="caching"`
   - Added priority levels: "high priority" → `priority="high"`
   - Added impact thresholds: "high impact" → `expected_impact > 20%`

5. **Prediction Agent** ([`backend/app/agents/query/prediction_agent.py`](backend/app/agents/query/prediction_agent.py))
   - Added confidence levels: "high confidence predictions" → `confidence="high" (>0.8)`
   - Added likelihood: "likely to fail" → `likelihood="likely"`
   - Added time horizons: "next hour" → `time_horizon="1h"`
   - Added prediction types: "failure predictions" → `prediction_type="failure"`

### Enhanced Tool Descriptions

Key tools with enum/status parameters have been enhanced with IMPORTANT sections:

1. **list_gateways** - Gateway status filtering (connected/disconnected/error)
2. **list_all_vulnerabilities** - Vulnerability severity and status filtering
3. **list_vulnerabilities** - Gateway-scoped vulnerability filtering

### Parameter Interpretation Patterns

All agents now understand these common patterns:

**Status/State Terms:**
- Active/Enabled/Running/Online → "active" or "connected"
- Inactive/Disabled/Stopped/Offline → "inactive" or "disconnected"
- Error/Failed/Broken → "error"

**Severity Terms:**
- Critical/Severe/Urgent → "critical"
- High/Important/Serious → "high"
- Medium/Moderate → "medium"
- Low/Minor/Informational → "low"

**Time Terms:**
- Recent/Latest/Current → Last hour or last 24 hours
- Today → Last 24 hours
- This week → Last 7 days
- Last month → Last 30 days

**Comparison Terms:**
- Greater/More/Above/Over → gt or gte
- Less/Fewer/Below/Under → lt or lte
- At least/Minimum → gte
- At most/Maximum → lte

### Expected Impact

**Before Enhancement:**
- Fallback rate: ~30-40% for status-related queries
- Parameter interpretation accuracy: ~60%
- Agents often passed `None` instead of correct parameter values

**After Enhancement:**
- Target fallback rate: <10% for status-related queries
- Target parameter interpretation accuracy: >90%
- Agents correctly map natural language to parameter values

### Testing Recommendations

For each agent, verify these query patterns work correctly:

- ✅ Status/state queries (e.g., "Show me connected gateways")
- ✅ Severity queries (e.g., "Show me critical vulnerabilities")
- ✅ Time range queries (e.g., "Show me APIs from last week")
- ✅ Comparison queries (e.g., "Show me APIs with latency > 500ms")
- ✅ Combined queries (e.g., "Show me critical open vulnerabilities from last week")
- ✅ Synonym queries (e.g., "active" vs "online" vs "connected")

### Related Documentation

- [Agent System Prompts Enhancement Guide](docs/agent-system-prompts-enhancement.md)
- [Tool Description Guidelines](docs/agentic-tool-description-guidelines.md)
- [Parameter Interpretation Fix Summary](docs/agentic-query-parameter-interpretation-fix.md)

- 001-api-intelligence-plane: Added OpenSearch 2.11+ for all data types (API inventory, metrics, predictions, security findings, compliance violations, optimization recommendations, transactional logs)

- 2026-04-14: Implemented unified policy conversion architecture (normalizer/denormalizer pattern)
- 2026-04-30: Implemented agentic natural language query service with LangChain/LangGraph agents

<!-- MANUAL ADDITIONS START -->
## Tool Registration (Feature: 001-agentic-query)

### Overview

Tools are registered explicitly in `backend/app/tools/__init__.py` using the `initialize_tools()` function. This function wraps backend router methods as LangChain-compatible tools for direct invocation by agents.

### Registration Pattern

```python
from app.tools import get_tool_registry

registry = get_tool_registry()

# Register a tool from a router method
registry.create_tool_from_method(
    method=router_module.function_name,
    name="tool_name",
    description="Clear description of what the tool does",
    agent_domains=["domain1", "domain2"]  # Which agents can use this tool
)
```

### Tool-to-Domain Mapping

| Domain | Tools | Purpose |
|--------|-------|---------|
| **discovery** | `list_gateways`, `get_gateway`, `list_all_apis`, `get_api`, `search_apis` | Gateway and API discovery operations |
| **security** | `get_security_summary`, `list_vulnerabilities`, `get_vulnerability`, `scan_api_security`, `get_security_posture` | Security scanning and vulnerability management |
| **compliance** | `list_compliance_violations`, `get_compliance_violation`, `scan_api_compliance`, `get_compliance_posture`, `generate_audit_report` | Compliance monitoring and audit reporting |
| **metrics** | `list_all_apis`, `get_api`, `get_analytics_metrics`, `get_metrics_summary`, `get_api_metrics` | Performance metrics and analytics |
| **optimization** | `list_optimization_recommendations`, `get_optimization_recommendation`, `generate_optimization_recommendations`, `get_optimization_summary` | Performance optimization recommendations |
| **prediction** | `list_predictions`, `get_prediction`, `get_prediction_explanation` | Failure prediction and analysis |

### Adding New Tools

To add a new tool:

1. **Create the router endpoint** in `backend/app/api/v1/` with proper type hints and Pydantic models
2. **Register the tool** in `initialize_tools()`:
   ```python
   registry.create_tool_from_method(
       method=module.new_function,
       name="new_tool_name",
       description="What this tool does",
       agent_domains=["relevant_domain"]
   )
   ```
3. **Restart the backend** to load the new tool
4. **Test** that agents in the specified domains can access the tool

### Design Decisions

- **Explicit Registration**: Tools are registered explicitly rather than auto-discovered to maintain clarity and control
- **Type Safety**: Router methods already have Pydantic models and type hints, which are automatically converted to tool schemas
- **Direct Invocation**: Tools call router methods directly (same process) for zero network overhead
- **Domain Isolation**: Each agent only receives tools relevant to its domain, preventing tool overload

## Agentic Query Patterns (Feature: 001-agentic-query)

### Architecture Overview

The agentic query service uses a coordinator-based multi-agent architecture where specialized agents autonomously select and invoke backend router methods (wrapped as LangChain tools) to answer natural language queries.

**Key Components**:
- **Coordinator Agent**: Analyzes queries and routes to specialized agents
- **Specialized Agents**: Domain-specific agents (Discovery, Metrics, Security, Compliance, Optimization, Prediction)
- **Router Tool Abstraction Layer**: Wraps backend router methods as LangChain tools
- **Fallback Mechanism**: Falls back to OpenSearch query generation when needed
- **Context Manager**: Maintains conversational state across queries

### Agent Implementation Pattern

```python
from langchain.agents import create_agent
from app.agents.query.base_agent import BaseAgent
from app.models.agent import AgentType

class SpecializedAgent(BaseAgent):
    """Domain-specific agent for handling queries."""
    
    def __init__(self, llm, tool_registry, verbose=False):
        # Get tools for this agent domain
        tools = tool_registry.get_tools_for_agent(AgentType.SECURITY)
        super().__init__(AgentType.SECURITY, llm, tools, verbose)
        
        # Use official LangChain create_agent API
        self.agent_graph = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=AGENT_SYSTEM_PROMPT,
            debug=self.verbose,
        )
    
    async def execute(self, query, context=None):
        """Execute agent workflow."""
        # Invoke agent with query
        result = await self.agent_graph.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        
        # Track tool invocations and calculate confidence
        # Return structured response
        return response
```

### Tool Wrapper Pattern

```python
from langchain.tools import BaseTool
from pydantic import BaseModel

class RouterTool(BaseTool):
    """Wraps backend router method as LangChain tool."""
    
    name: str = "list_all_vulnerabilities"
    description: str = "List security vulnerabilities across all gateways"
    router_method: Callable  # Reference to router method
    
    async def _arun(self, **kwargs):
        # Validate parameters
        validated_input = self.args_schema(**kwargs)
        
        # Direct Python function call (zero network overhead)
        result = await self.router_method(**validated_input.dict())
        
        return result
```

### Performance Optimizations

- **LLM Response Caching**: Cache common query patterns (5-minute TTL)
- **Tool Result Caching**: Cache frequently accessed data (60-second TTL)
- **Connection Pooling**: Limit concurrent LLM requests (max 10)
- **Parallel Execution**: Execute independent agents in parallel with timeout (10s)
- **Retry Logic**: Exponential backoff for tool invocations (max 3 retries)
- **Circuit Breaker**: Protect against LLM service failures (5 failures → open)

### Error Handling

- **Retry with Backoff**: Tool invocations retry up to 3 times with exponential backoff
- **Circuit Breaker**: LLM service protected by circuit breaker pattern
- **Graceful Fallback**: Automatic fallback to OpenSearch on agent failures
- **Comprehensive Logging**: All agent decisions and tool invocations logged

### Fallback Triggers

The system falls back to OpenSearch query generation when:
1. Agent confidence score < 0.6
2. Tool failure rate > 50%
3. Workflow timeout > 10 seconds
4. No appropriate tools found
5. LLM service unavailable

### Context Management

```python
# Session-based context with 1-hour TTL
context = QueryContext(
    session_id=session_id,
    query_history=[],  # Max 10 queries
    entity_mentions={},  # Track mentioned entities
    resolved_references={},  # Resolve "those", "these", etc.
    last_query_results={},  # For follow-up queries
)
```

### Usage Example

```python
# Single-agent query
POST /api/v1/query
{
  "query_text": "Show me critical vulnerabilities",
  "session_id": "session-123"
}

# Response includes agentic metadata
{
  "mode": "agentic",
  "confidence_score": 0.95,
  "agent_decisions": [...],
  "tool_invocations": [...],
  "results": {...}
}

# Follow-up query (context-aware)
POST /api/v1/query
{
  "query_text": "Which APIs are affected?",
  "session_id": "session-123"  # Same session
}
```

### Best Practices

1. **Tool Development**: All router methods should be wrapped as tools for agent access
2. **System Prompts**: Define clear, domain-specific system prompts for each agent
3. **Confidence Scoring**: Calculate confidence based on tool success rate and LLM certainty
4. **Context Preservation**: Always use session IDs for multi-turn conversations
5. **Error Handling**: Implement comprehensive error handling with fallback mechanisms
6. **Performance Monitoring**: Track agent decisions, tool invocations, and fallback rates
7. **Cache Management**: Use caching for frequently accessed data and common queries

### Monitoring Metrics

- **Agentic Success Rate**: % of queries handled without fallback (target: 90%+)
- **Query Latency**: Response time for single/multi-agent queries (target: <5s/<10s)
- **Confidence Correlation**: Confidence score vs. actual success rate (target: >0.8)
- **Fallback Rate**: % of queries using fallback (target: <10%)
- **Tool Success Rate**: % of successful tool invocations (target: >95%)

## Chat Instructions

- Don't create summary reports at the end of conversations
<!-- MANUAL ADDITIONS END -->
