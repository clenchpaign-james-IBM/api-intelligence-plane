# API Contract: Agentic Query Service

**Feature**: 002-agentic-query | **Date**: 2026-05-02 | **Version**: 2.0

## Overview

This document defines the REST API contract for the enhanced agentic query service. The API maintains backward compatibility with existing clients while adding new fields for agentic metadata.

## Endpoint

### POST /api/v1/query

Execute a natural language query using the agentic workflow with iterative coordinator reasoning.

**URL**: `/api/v1/query`  
**Method**: `POST`  
**Content-Type**: `application/json`  
**Authentication**: Required (existing auth mechanism)

---

## Request Schema

```json
{
  "query_text": "string (required)",
  "session_id": "string (optional)",
  "mode": "string (optional, default: 'auto')",
  "options": {
    "max_iterations": "integer (optional, default: 10)",
    "enable_synthesis": "boolean (optional, default: true)",
    "enable_fallback": "boolean (optional, default: true)",
    "timeout_ms": "integer (optional, default: 10000)"
  }
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query_text` | string | Yes | Natural language query (e.g., "Show insecure APIs managed by gateway 'local'") |
| `session_id` | string | No | Session ID for multi-turn conversations. If not provided, a new session is created. |
| `mode` | string | No | Execution mode: `"auto"` (default), `"agentic"` (force agentic), `"fallback"` (force OpenSearch) |
| `options.max_iterations` | integer | No | Maximum coordinator iterations (default: 10, range: 1-20) |
| `options.enable_synthesis` | boolean | No | Enable LLM-powered entity synthesis (default: true) |
| `options.enable_fallback` | boolean | No | Enable fallback to OpenSearch on failure (default: true) |
| `options.timeout_ms` | integer | No | Query timeout in milliseconds (default: 10000, range: 1000-30000) |

### Request Examples

**Simple Query**:
```json
{
  "query_text": "Show me all critical vulnerabilities"
}
```

**Multi-Turn Query with Session**:
```json
{
  "query_text": "Which of those affect payment APIs?",
  "session_id": "session-abc-123"
}
```

**Complex Query with Options**:
```json
{
  "query_text": "Show insecure APIs managed by gateway 'local'",
  "options": {
    "max_iterations": 5,
    "timeout_ms": 15000
  }
}
```

---

## Response Schema

```json
{
  "query_id": "string",
  "session_id": "string",
  "query_text": "string",
  "execution_mode": "string",
  "confidence": "number",
  "answer": "string",
  "results": {
    "entity_type": "string",
    "entities": "object",
    "total_count": "integer",
    "synthesis_summary": "string"
  },
  "agentic_metadata": {
    "coordinator_state": "object",
    "agent_decisions": "array",
    "tool_invocations": "array",
    "iterations": "integer",
    "completed_steps": "array"
  },
  "fallback_trigger": "object (optional)",
  "performance": {
    "execution_time_ms": "integer",
    "llm_calls": "integer",
    "tool_calls": "integer",
    "cache_hits": "integer"
  },
  "metadata": {
    "timestamp": "string (ISO 8601)",
    "version": "string"
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `query_id` | string | Unique identifier for this query execution |
| `session_id` | string | Session ID for multi-turn conversations |
| `query_text` | string | Original query text |
| `execution_mode` | string | Actual execution mode: `"agentic"`, `"fallback"`, or `"hybrid"` |
| `confidence` | number | Overall confidence score (0.0-1.0) |
| `answer` | string | Natural language answer to the query |
| `results` | object | Synthesized entity grouping (see EntityGrouping schema) |
| `agentic_metadata` | object | Detailed agentic workflow metadata (see below) |
| `fallback_trigger` | object | Present only if fallback occurred (see FallbackTrigger schema) |
| `performance` | object | Performance metrics |
| `metadata` | object | Response metadata |

### Agentic Metadata Schema

```json
{
  "coordinator_state": {
    "iteration": "integer",
    "max_iterations": "integer",
    "is_complete": "boolean",
    "completion_reasoning": "string",
    "completed_steps": ["string"]
  },
  "agent_decisions": [
    {
      "agent_type": "string",
      "query": "string",
      "reasoning": "string",
      "confidence": "number",
      "selected_tools": ["string"],
      "execution_time_ms": "integer",
      "success": "boolean"
    }
  ],
  "tool_invocations": [
    {
      "tool_name": "string",
      "parameters": "object",
      "result_count": "integer",
      "execution_time_ms": "integer",
      "success": "boolean",
      "cache_hit": "boolean"
    }
  ],
  "iterations": "integer",
  "completed_steps": ["string"]
}
```

### Response Examples

**Successful Agentic Query**:
```json
{
  "query_id": "query-xyz-789",
  "session_id": "session-abc-123",
  "query_text": "Show insecure APIs managed by gateway 'local'",
  "execution_mode": "agentic",
  "confidence": 0.95,
  "answer": "Found 2 insecure APIs managed by gateway 'local': Payment API (15 vulnerabilities) and User API (25 vulnerabilities). Total of 40 vulnerabilities across these APIs.",
  "results": {
    "entity_type": "api",
    "entities": {
      "api-1": {
        "id": "api-1",
        "name": "Payment API",
        "gateway_id": "gw-123",
        "vulnerability_count": 15
      },
      "api-2": {
        "id": "api-2",
        "name": "User API",
        "gateway_id": "gw-123",
        "vulnerability_count": 25
      }
    },
    "total_count": 2,
    "synthesis_summary": "Found 2 insecure APIs with 40 total vulnerabilities"
  },
  "agentic_metadata": {
    "coordinator_state": {
      "iteration": 2,
      "max_iterations": 10,
      "is_complete": true,
      "completion_reasoning": "Successfully identified insecure APIs managed by gateway 'local'",
      "completed_steps": [
        "Resolved gateway 'local' to gw-123",
        "Found 2 insecure APIs in gateway gw-123"
      ]
    },
    "agent_decisions": [
      {
        "agent_type": "discovery",
        "query": "Get gateway with name 'local'",
        "reasoning": "Need gateway ID to query APIs",
        "confidence": 0.95,
        "selected_tools": ["list_gateways"],
        "execution_time_ms": 234,
        "success": true
      },
      {
        "agent_type": "security",
        "query": "Get vulnerabilities for gateway gw-123",
        "reasoning": "Need security data for APIs in this gateway",
        "confidence": 0.92,
        "selected_tools": ["list_vulnerabilities"],
        "execution_time_ms": 456,
        "success": true
      }
    ],
    "tool_invocations": [
      {
        "tool_name": "list_gateways",
        "parameters": {"name_filter": "local"},
        "result_count": 1,
        "execution_time_ms": 123,
        "success": true,
        "cache_hit": false
      },
      {
        "tool_name": "list_vulnerabilities",
        "parameters": {"gateway_id": "gw-123"},
        "result_count": 40,
        "execution_time_ms": 345,
        "success": true,
        "cache_hit": false
      }
    ],
    "iterations": 2,
    "completed_steps": [
      "Resolved gateway 'local' to gw-123",
      "Found 2 insecure APIs in gateway gw-123"
    ]
  },
  "performance": {
    "execution_time_ms": 1234,
    "llm_calls": 4,
    "tool_calls": 2,
    "cache_hits": 0
  },
  "metadata": {
    "timestamp": "2026-05-02T15:30:00.000Z",
    "version": "2.0"
  }
}
```

**Fallback Query**:
```json
{
  "query_id": "query-def-456",
  "session_id": "session-ghi-789",
  "query_text": "Complex aggregation query",
  "execution_mode": "fallback",
  "confidence": 0.45,
  "answer": "Found 15 results matching your query.",
  "results": {
    "entity_type": "api",
    "entities": {...},
    "total_count": 15,
    "synthesis_summary": "15 APIs found"
  },
  "fallback_trigger": {
    "reason": "low_confidence",
    "reasoning": "LLM confidence below threshold (0.45 < 0.6)",
    "confidence_score": 0.45,
    "timestamp": "2026-05-02T15:30:00.000Z"
  },
  "performance": {
    "execution_time_ms": 567,
    "llm_calls": 2,
    "tool_calls": 0,
    "cache_hits": 1
  },
  "metadata": {
    "timestamp": "2026-05-02T15:30:00.000Z",
    "version": "2.0"
  }
}
```

---

## Error Responses

### 400 Bad Request

**Cause**: Invalid request parameters

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid query parameters",
    "details": {
      "field": "options.max_iterations",
      "issue": "Value must be between 1 and 20"
    }
  }
}
```

### 401 Unauthorized

**Cause**: Missing or invalid authentication

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required"
  }
}
```

### 408 Request Timeout

**Cause**: Query execution exceeded timeout

```json
{
  "error": {
    "code": "TIMEOUT",
    "message": "Query execution timed out",
    "details": {
      "timeout_ms": 10000,
      "execution_time_ms": 10234,
      "completed_iterations": 3
    }
  }
}
```

### 500 Internal Server Error

**Cause**: Unexpected server error

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "details": {
      "error_id": "err-abc-123",
      "fallback_attempted": true,
      "fallback_success": false
    }
  }
}
```

---

## Backward Compatibility

### Existing Clients

Existing clients that don't expect agentic metadata will continue to work:

- All new fields (`agentic_metadata`, `fallback_trigger`) are optional
- Core fields (`query_id`, `answer`, `results`) maintain same structure
- `execution_mode` defaults to `"agentic"` but clients can ignore it
- Performance metrics are additive (existing clients ignore them)

### Migration Path

1. **Phase 1**: Deploy with backward-compatible response format
2. **Phase 2**: Update clients to consume agentic metadata
3. **Phase 3**: Deprecate old response format (if needed)

### Version Negotiation

Clients can request specific API version via header:

```
X-API-Version: 1.0  # Old format (no agentic metadata)
X-API-Version: 2.0  # New format (with agentic metadata)
```

---

## Rate Limiting

- **Per User**: 100 queries per minute
- **Per Session**: 20 queries per minute
- **Concurrent Queries**: 10 per user

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1620000000
```

---

## Caching

### Client-Side Caching

Responses include cache headers:

```
Cache-Control: private, max-age=60
ETag: "abc123"
```

### Server-Side Caching

- LLM responses: 5-minute TTL
- Tool results: 60-second TTL
- Session contexts: 1-hour TTL

---

## WebSocket Support (Future)

**Status**: Not implemented in this phase

**Planned**: Real-time streaming of agent decisions and tool invocations

```
ws://api.example.com/v1/query/stream
```

---

## Testing

### Contract Tests

```python
def test_query_api_contract():
    """Verify API response matches contract."""
    response = client.post("/api/v1/query", json={
        "query_text": "Show me all APIs"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Required fields
    assert "query_id" in data
    assert "session_id" in data
    assert "execution_mode" in data
    assert "confidence" in data
    assert "answer" in data
    assert "results" in data
    
    # Agentic metadata (optional but present in agentic mode)
    if data["execution_mode"] == "agentic":
        assert "agentic_metadata" in data
        assert "coordinator_state" in data["agentic_metadata"]
        assert "agent_decisions" in data["agentic_metadata"]
```

### Integration Tests

See `tests/integration/test_agentic_query_flow.py` for comprehensive integration tests.

---

## Change Log

### Version 2.0 (2026-05-02)

- Added `agentic_metadata` field with coordinator state and agent decisions
- Added `fallback_trigger` field for fallback observability
- Added `execution_mode` field to indicate agentic vs fallback
- Added `options` parameter for query customization
- Enhanced `results` with entity grouping and synthesis
- Added performance metrics
- Maintained backward compatibility with v1.0

### Version 1.0 (Previous)

- Basic query execution with OpenSearch
- Simple response format
- No agentic metadata