# Quickstart Guide: Agentic Query Service

**Feature**: 002-agentic-query | **Date**: 2026-05-02

## Overview

This guide helps developers quickly set up, test, and debug the agentic natural language query service with iterative coordinator reasoning and LLM-powered synthesis.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenSearch 2.11+ running
- LiteLLM configured with API keys
- Unified MCP server running

## Quick Setup

### 1. Install Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in backend directory:

```bash
# LLM Configuration
LITELLM_API_KEY=your_api_key_here
LITELLM_MODEL=gpt-4  # or claude-3-opus, etc.

# OpenSearch Configuration
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=admin

# MCP Server Configuration
MCP_SERVER_URL=http://localhost:8001

# Agentic Query Configuration
AGENTIC_QUERY_MAX_ITERATIONS=10
AGENTIC_QUERY_TIMEOUT_MS=10000
AGENTIC_QUERY_CONFIDENCE_THRESHOLD=0.6
AGENTIC_QUERY_ENABLE_CACHE=true
AGENTIC_QUERY_CACHE_TTL_SECONDS=300
```

### 3. Start Services

```bash
# Start OpenSearch and MCP server
docker-compose up -d opensearch mcp-server

# Start backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify Setup

```bash
# Check backend health
curl http://localhost:8000/health

# Check MCP server health
curl http://localhost:8001/health

# Test simple query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Show me all APIs"}'
```

---

## Running Tests

### Integration Tests

```bash
cd backend

# Run all integration tests
pytest tests/integration/ -v

# Run specific test suites
pytest tests/integration/test_agentic_query_flow.py -v
pytest tests/integration/test_iterative_reasoning.py -v
pytest tests/integration/test_entity_synthesis.py -v
pytest tests/integration/test_multi_agent_collaboration.py -v
pytest tests/integration/test_fallback_mechanism.py -v

# Run with coverage
pytest tests/integration/ --cov=app.agents --cov=app.services --cov-report=html
```

### E2E Tests

```bash
# Run end-to-end tests
pytest tests/e2e/ -v

# Run specific scenarios
pytest tests/e2e/test_query_scenarios.py -v
pytest tests/e2e/test_conversational_context.py -v

# Run with detailed output
pytest tests/e2e/ -v -s
```

### Test with Mock LLM

```python
# tests/integration/test_iterative_reasoning.py
import pytest
from app.agents.query.coordinator_agent import CoordinatorAgent
from tests.mocks.mock_llm import MockLLM

@pytest.mark.asyncio
async def test_multi_step_query_with_mock_llm():
    """Test coordinator iterates to resolve gateway name then fetch APIs."""
    
    # Mock LLM responses
    mock_llm = MockLLM({
        "decide next action": {
            "action": "invoke_discovery_agent",
            "parameters": {"query": "get gateway with name 'local'"}
        },
        "evaluate completion": {
            "is_complete": False,
            "reasoning": "Need to fetch APIs for gateway"
        }
    })
    
    coordinator = CoordinatorAgent(llm=mock_llm, agents=mock_agents)
    result = await coordinator.execute_iterative_workflow(
        "Show APIs managed by gateway 'local'"
    )
    
    assert result["iterations"] == 2
    assert len(result["apis"]) > 0
```

---

## Example Queries

### Simple Single-Agent Queries

```bash
# Discovery queries
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Show me all gateways"}'

curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "List APIs in gateway local"}'

# Security queries
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Show me critical vulnerabilities"}'

# Metrics queries
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Which APIs have high latency?"}'
```

### Multi-Step Iterative Queries

```bash
# Requires coordinator to iterate: resolve gateway name → fetch APIs
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Show APIs managed by gateway local"}'

# Requires coordinator to iterate: resolve gateway → fetch vulnerabilities → group by API
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Show insecure APIs managed by gateway local"}'

# Requires coordinator to iterate: fetch high-latency APIs → check compliance
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "What is the compliance status of my slowest APIs?"}'
```

### Multi-Agent Collaboration Queries

```bash
# Requires metrics + security agents
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Which APIs have both high latency and security vulnerabilities?"}'

# Requires discovery + compliance agents
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Show me APIs in production gateway with compliance violations"}'
```

### Multi-Turn Conversational Queries

```bash
# First query
RESPONSE=$(curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Show me all APIs"}')

# Extract session_id
SESSION_ID=$(echo $RESPONSE | jq -r '.session_id')

# Follow-up query using session context
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d "{\"query_text\": \"Which of those have vulnerabilities?\", \"session_id\": \"$SESSION_ID\"}"

# Another follow-up
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d "{\"query_text\": \"Show me more details about the vulnerable ones\", \"session_id\": \"$SESSION_ID\"}"
```

---

## Debugging

### Enable Debug Logging

```python
# backend/app/main.py
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable agent decision logging
logging.getLogger('app.agents').setLevel(logging.DEBUG)
logging.getLogger('app.services.agentic_query_service').setLevel(logging.DEBUG)
```

### View Agent Decisions

```bash
# Query with verbose output
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Show insecure APIs", "options": {"verbose": true}}'

# Check logs for agent decisions
tail -f backend/logs/agentic_query.log | grep "AgentDecision"
```

### Inspect Coordinator State

```python
# Add breakpoint in coordinator_agent.py
async def iterative_reasoning_loop(self, query: str) -> Dict:
    state = CoordinatorState(query=query)
    
    while not state.is_complete and state.iteration < state.max_iterations:
        # Breakpoint here to inspect state
        import pdb; pdb.set_trace()
        
        next_action = await self.llm_decide_next_action(state)
        # ...
```

### Monitor Tool Invocations

```bash
# Enable tool invocation logging
export AGENTIC_QUERY_LOG_TOOL_INVOCATIONS=true

# View tool calls in real-time
tail -f backend/logs/tool_invocations.log
```

### Check Fallback Triggers

```bash
# Query OpenSearch for fallback events
curl -X GET "http://localhost:9200/fallback_triggers/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "range": {
        "timestamp": {
          "gte": "now-1h"
        }
      }
    }
  }'
```

---

## Performance Profiling

### Profile Agent Execution

```python
# backend/scripts/profile_agentic_query.py
import cProfile
import pstats
from app.services.agentic_query_service import AgenticQueryService

async def profile_query():
    service = AgenticQueryService(...)
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = await service.execute_query("Show insecure APIs")
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

# Run profiler
python backend/scripts/profile_agentic_query.py
```

### Monitor LLM Cache Hit Rate

```bash
# Check cache metrics
curl http://localhost:8000/metrics | grep llm_cache

# Expected output:
# llm_cache_hits_total 45
# llm_cache_misses_total 12
# llm_cache_hit_rate 0.789
```

### Measure Iteration Performance

```python
# tests/performance/test_iteration_performance.py
@pytest.mark.asyncio
async def test_iteration_performance():
    """Verify most queries complete in 2-3 iterations."""
    
    queries = [
        "Show APIs managed by gateway local",
        "Show insecure APIs in production",
        "What is the compliance status of slow APIs?"
    ]
    
    iteration_counts = []
    for query in queries:
        result = await service.execute_query(query)
        iteration_counts.append(result["agentic_metadata"]["iterations"])
    
    avg_iterations = sum(iteration_counts) / len(iteration_counts)
    assert avg_iterations <= 3.0, f"Average iterations {avg_iterations} exceeds target of 3"
```

---

## Common Issues & Solutions

### Issue: LLM Timeout

**Symptom**: Queries timeout after 10 seconds

**Solution**:
```bash
# Increase timeout in .env
AGENTIC_QUERY_TIMEOUT_MS=15000

# Or per-query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "...", "options": {"timeout_ms": 15000}}'
```

### Issue: High Fallback Rate

**Symptom**: >10% of queries fall back to OpenSearch

**Solution**:
```bash
# Lower confidence threshold
AGENTIC_QUERY_CONFIDENCE_THRESHOLD=0.5

# Check fallback reasons
curl http://localhost:8000/api/v1/metrics/fallback_reasons

# Tune agent system prompts based on common failures
```

### Issue: Infinite Loop Detection

**Symptom**: Queries hit max iterations (10)

**Solution**:
```python
# Add progress detection in coordinator_agent.py
def detect_no_progress(state: CoordinatorState) -> bool:
    """Stop if last iteration produced no new entities."""
    if state.iteration < 2:
        return False
    
    prev_results = state.intermediate_results.get(f"iteration_{state.iteration-1}", {})
    curr_results = state.intermediate_results.get(f"iteration_{state.iteration}", {})
    
    prev_entities = extract_entity_ids(prev_results)
    curr_entities = extract_entity_ids(curr_results)
    
    return prev_entities == curr_entities  # No new entities
```

### Issue: Poor Entity Grouping

**Symptom**: "40 vulnerabilities" instead of "8 APIs with vulnerabilities"

**Solution**:
```python
# Enhance agent synthesis prompt
SYNTHESIS_PROMPT = """
You are analyzing tool results for a {agent_domain} query.

IMPORTANT: Group results by the PRIMARY ENTITY the user asked about.
- If query asks about "APIs", group by API (not vulnerabilities)
- If query asks about "gateways", group by gateway (not APIs)
- If query asks about "vulnerabilities", group by vulnerability

Query: {query}
Tool Results: {results}

Return entity grouping with natural language summary.
"""
```

---

## Development Workflow

### 1. Add New Agent

```python
# backend/app/agents/query/new_agent.py
from app.agents.query.base_agent import BaseAgent

class NewAgent(BaseAgent):
    """Specialized agent for new domain."""
    
    def __init__(self, llm, tools):
        super().__init__(AgentType.NEW_DOMAIN, llm, tools)
    
    async def execute(self, query: str, context: Dict) -> Dict:
        # Implement agent logic
        pass
```

### 2. Register Agent Tools

```python
# backend/app/tools/__init__.py
def initialize_tools():
    registry = get_tool_registry()
    
    # Register tools for new agent
    registry.create_tool_from_method(
        method=router.new_function,
        name="new_tool",
        description="Tool description",
        agent_domains=["new_domain"]
    )
```

### 3. Add Integration Test

```python
# tests/integration/test_new_agent.py
@pytest.mark.asyncio
async def test_new_agent_workflow():
    """Test new agent with mock LLM."""
    mock_llm = MockLLM({...})
    agent = NewAgent(llm=mock_llm, tools=mock_tools)
    
    result = await agent.execute("Test query")
    
    assert result["success"]
    assert result["synthesis_result"]["entity_type"] == "expected_type"
```

### 4. Update Documentation

- Add agent to `data-model.md` (AgentType enum)
- Add agent to `research.md` (agent capabilities)
- Add example queries to this quickstart

---

## Next Steps

1. **Implement Core Features**: Follow `tasks.md` (generated by `/speckit.tasks`)
2. **Write Integration Tests**: Cover all user stories from `spec.md`
3. **Performance Tuning**: Profile and optimize based on metrics
4. **Production Deployment**: Follow deployment guide in `docs/deployment.md`

## Resources

- **Spec**: [spec.md](./spec.md)
- **Plan**: [plan.md](./plan.md)
- **Research**: [research.md](./research.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contract**: [contracts/query-api.md](./contracts/query-api.md)
- **Tasks**: [tasks.md](./tasks.md) (generated by `/speckit.tasks`)