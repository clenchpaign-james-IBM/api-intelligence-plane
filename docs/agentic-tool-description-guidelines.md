# Agentic Tool Description Guidelines

## Overview

This document provides guidelines for writing effective tool descriptions that enable LLM agents to correctly understand and invoke tools with appropriate parameters.

**Last Updated:** 2026-05-01  
**Feature:** 001-agentic-query

## Why Tool Descriptions Matter

LLM agents rely entirely on tool descriptions to:
1. **Understand** what the tool does
2. **Decide** when to use the tool
3. **Determine** what parameter values to pass
4. **Interpret** the results

Poor tool descriptions lead to:
- ❌ Agents calling wrong tools
- ❌ Agents passing incorrect parameter values (e.g., `None` instead of `"connected"`)
- ❌ Agents misinterpreting results
- ❌ Increased fallback to OpenSearch queries

## Tool Description Template

```python
registry.create_tool_from_method(
    method=module.function_name,
    name="tool_name",
    description="""[One-line summary of what the tool does]
    
    [Detailed description explaining the tool's purpose and when to use it]
    
    IMPORTANT: [Critical guidance for parameter interpretation]
    - [Natural language phrase] → parameter_name="value"
    - [Another phrase] → parameter_name="other_value"
    
    Args:
        param1: [Type] [Description]. Valid values:
            - "value1": [When to use this value]
            - "value2": [When to use this value]
            - None (default): [When to use None]
        param2: [Type] [Description with examples]
        param3: [Type] [Description]
    
    Returns:
        dict: [Description of return structure] with:
            - field1: [Description]
            - field2: [Description]
            - field3: [Description]
    
    Example for [common use case]:
        >>> result = await tool_name(param1="value1", param2=10)
        >>> print(f"Found {result['count']} items")
    
    Example for [another use case]:
        >>> result = await tool_name(param1="value2")
        >>> print(result['summary'])
    """,
    agent_domains=["domain1", "domain2"]
)
```

## Key Principles

### 1. Be Explicit About Parameter Mapping

**❌ Bad:**
```python
description="""List gateways.

Args:
    status: Optional status filter
"""
```

**✅ Good:**
```python
description="""List gateways with optional status filtering.

IMPORTANT: When user asks for "connected gateways", "active gateways", or "online gateways",
you MUST set status_filter="connected". When they ask for "disconnected" or "offline" gateways,
set status_filter="disconnected".

Args:
    status_filter: Optional status filter. Valid values:
        - "connected": Only return connected gateways
        - "disconnected": Only return disconnected gateways
        - None (default): Return all gateways
"""
```

### 2. Document All Valid Parameter Values

**❌ Bad:**
```python
Args:
    severity: Severity level
```

**✅ Good:**
```python
Args:
    severity: Vulnerability severity level. Valid values:
        - "critical": Critical vulnerabilities (CVSS 9.0-10.0)
        - "high": High severity (CVSS 7.0-8.9)
        - "medium": Medium severity (CVSS 4.0-6.9)
        - "low": Low severity (CVSS 0.1-3.9)
        - None (default): All severity levels
```

### 3. Provide Multiple Examples

Include examples for:
- Most common use case
- Edge cases
- Different parameter combinations

```python
Example for critical vulnerabilities:
    >>> result = await list_vulnerabilities(severity="critical", status="open")
    >>> print(f"Found {result['total']} critical open vulnerabilities")

Example for all vulnerabilities:
    >>> result = await list_vulnerabilities()
    >>> print(f"Total vulnerabilities: {result['total']}")
```

### 4. Use Natural Language Mappings

Map common user phrases to parameter values:

```python
IMPORTANT: Natural language to parameter mapping:
- "slow APIs", "high latency APIs", "performance issues" → Use get_api_metrics with latency filters
- "fast APIs", "low latency APIs", "good performance" → Use get_api_metrics with latency < 100ms
- "APIs with errors", "failing APIs", "broken APIs" → Use get_api_metrics with error_rate > 0
```

### 5. Explain Return Structure

**❌ Bad:**
```python
Returns:
    dict: Results
```

**✅ Good:**
```python
Returns:
    dict: Paginated vulnerability list with:
        - items: List of vulnerability objects, each containing:
            - id: Vulnerability UUID
            - title: Vulnerability title
            - severity: Severity level (critical/high/medium/low)
            - status: Current status (open/in_progress/resolved)
            - api_id: Affected API identifier
        - total: Total count of vulnerabilities matching filters
        - page: Current page number
        - page_size: Items per page
```

## Common Parameter Patterns

### Status/State Parameters

```python
IMPORTANT: Status parameter mapping:
- "active", "enabled", "running", "online" → status="active"
- "inactive", "disabled", "stopped", "offline" → status="inactive"
- "error", "failed", "broken" → status="error"
- "all", "any" → status=None
```

### Severity Parameters

```python
IMPORTANT: Severity parameter mapping:
- "critical", "severe", "urgent" → severity="critical"
- "high", "important" → severity="high"
- "medium", "moderate" → severity="medium"
- "low", "minor" → severity="low"
```

### Time Range Parameters

```python
IMPORTANT: Time range interpretation:
- "last hour", "past hour", "recent" → Use time_range with start=now-1h
- "last 24 hours", "today", "past day" → Use time_range with start=now-24h
- "last week", "past week" → Use time_range with start=now-7d
- "last month", "past month" → Use time_range with start=now-30d
```

### Comparison Parameters

```python
IMPORTANT: Comparison operators:
- "greater than X", "more than X", "above X" → Use gt=X
- "less than X", "fewer than X", "below X" → Use lt=X
- "at least X", "minimum X" → Use gte=X
- "at most X", "maximum X" → Use lte=X
```

## Agent-Specific Guidance

### Discovery Agent Tools

Focus on:
- Gateway status (connected/disconnected/error)
- API health status (healthy/degraded/down)
- Connection states

### Security Agent Tools

Focus on:
- Vulnerability severity (critical/high/medium/low)
- Security status (open/in_progress/resolved)
- Risk levels

### Metrics Agent Tools

Focus on:
- Performance thresholds (latency, throughput, error rates)
- Time ranges (last hour, last day, last week)
- Comparison operators (greater than, less than)

### Compliance Agent Tools

Focus on:
- Compliance status (compliant/non_compliant/unknown)
- Regulation types (GDPR, HIPAA, SOC2, PCI, ISO)
- Violation severity

### Optimization Agent Tools

Focus on:
- Recommendation status (pending/applied/rejected)
- Optimization types (caching, rate_limiting, compression)
- Priority levels (high/medium/low)

### Prediction Agent Tools

Focus on:
- Prediction confidence (high/medium/low)
- Failure likelihood (likely/possible/unlikely)
- Time horizons (next hour, next day, next week)

## Testing Tool Descriptions

After writing a tool description, test it by asking:

1. **Can the agent understand when to use this tool?**
   - Test: "Show me connected gateways" → Should select `list_gateways`
   
2. **Can the agent determine correct parameter values?**
   - Test: "Show me connected gateways" → Should pass `status_filter="connected"`
   
3. **Can the agent interpret the results?**
   - Test: Agent should understand the return structure and extract relevant data

4. **Does it handle edge cases?**
   - Test: "Show me all gateways" → Should pass `status_filter=None`

## Common Mistakes to Avoid

### ❌ Mistake 1: Vague Parameter Descriptions
```python
Args:
    filter: Filter value
```

### ✅ Fix:
```python
Args:
    status_filter: Gateway status filter. Valid values:
        - "connected": Only connected gateways
        - "disconnected": Only disconnected gateways
        - None: All gateways
```

### ❌ Mistake 2: Missing Natural Language Mappings
```python
description="""List APIs with optional filters."""
```

### ✅ Fix:
```python
description="""List APIs with optional filters.

IMPORTANT: When user asks for "slow APIs" or "high latency APIs",
set latency_threshold to filter APIs with latency > threshold.
"""
```

### ❌ Mistake 3: Incomplete Examples
```python
Example:
    >>> result = await list_apis()
```

### ✅ Fix:
```python
Example for healthy APIs:
    >>> result = await list_apis(health_status="healthy")
    >>> print(f"Found {result['total']} healthy APIs")

Example for all APIs:
    >>> result = await list_apis()
    >>> print(f"Total APIs: {result['total']}")
```

### ❌ Mistake 4: Unclear Return Structure
```python
Returns:
    dict: API data
```

### ✅ Fix:
```python
Returns:
    dict: Paginated API list with:
        - items: List of API objects with id, name, status, health
        - total: Total API count
        - page: Current page
        - page_size: Items per page
```

## Maintenance

- Review tool descriptions when:
  - Agents consistently pass wrong parameter values
  - Fallback rate increases for specific query types
  - New natural language patterns emerge from user queries
  
- Update descriptions to include:
  - New parameter value mappings
  - Additional examples
  - Clarifications based on agent behavior

## Related Documents

- [Agentic Query Architecture](./agentic-query-architecture-design.md)
- [Agent Development Guide](./AGENTS.md)
- [Tool Registry Implementation](../backend/app/tools/tool_registry.py)

---

**Made with Bob**