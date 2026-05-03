# Search APIs Implementation Guide

**Feature**: User Story 5 - Enhanced Search APIs for Flexible Querying
**Priority**: P2
**Parent Spec**: [spec.md](./spec.md)
**Implementation Plan**: [plan.md](./plan.md)

## Overview

This document provides detailed implementation guidance for the 6 search API endpoints that extend the agentic query system's capabilities. These search APIs enable agents to perform flexible multi-criteria filtering when simple list operations are insufficient.

## Implementation Checklist

### Phase 1: Repository Layer (6 repositories)

- [ ] **GatewayRepository.search()** - `backend/app/db/repositories/gateway_repository.py`
  - Parameters: name, vendor, status, created_after, created_before, page, page_size
  - Returns: Tuple[List[Gateway], int]
  - OpenSearch query: bool query with must/filter clauses

- [ ] **APIRepository.search()** - `backend/app/db/repositories/api_repository.py`
  - Parameters: name, description, status, authentication_type, is_shadow, health_score_min/max, gateway_id, created_after/before, page, page_size
  - Returns: Tuple[List[API], int]
  - OpenSearch query: bool query with text matching on name/description

- [ ] **VulnerabilityRepository.search()** - `backend/app/db/repositories/vulnerability_repository.py`
  - Parameters: severity, type, status, api_name, gateway_id, discovered_after/before, page, page_size
  - Returns: Tuple[List[Vulnerability], int]
  - OpenSearch query: bool query with nested API name matching

- [ ] **ComplianceRepository.search()** - `backend/app/db/repositories/compliance_repository.py`
  - Parameters: standard, violation_type, severity, status, api_name, gateway_id, discovered_after/before, page, page_size
  - Returns: Tuple[List[ComplianceViolation], int]
  - OpenSearch query: bool query with standard enum matching

- [ ] **RecommendationRepository.search()** - `backend/app/db/repositories/recommendation_repository.py`
  - Parameters: type, priority, status, impact_min/max, api_name, gateway_id, created_after/before, page, page_size
  - Returns: Tuple[List[Recommendation], int]
  - OpenSearch query: bool query with range queries for impact

- [ ] **PredictionRepository.search()** - `backend/app/db/repositories/prediction_repository.py`
  - Parameters: prediction_type, confidence_min/max, severity, status, predicted_after/before, api_name, gateway_id, page, page_size
  - Returns: Tuple[List[Prediction], int]
  - OpenSearch query: bool query with range queries for confidence

### Phase 2: API Endpoints (6 routers)

- [ ] **GET /api/v1/gateways/search** - `backend/app/api/v1/gateways.py`
  - Request model: GatewaySearchRequest (Pydantic)
  - Response model: GatewaySearchResponse
  - Validation: Enum validation for vendor/status, date format validation

- [ ] **GET /api/v1/apis/search** - `backend/app/api/v1/apis.py`
  - Request model: APISearchRequest
  - Response model: APISearchResponse
  - Validation: Health score range (0.0-1.0), enum validation

- [ ] **GET /api/v1/security/vulnerabilities/search** - `backend/app/api/v1/security.py`
  - Request model: VulnerabilitySearchRequest
  - Response model: VulnerabilitySearchResponse
  - Validation: Severity/status enums, date ranges

- [ ] **GET /api/v1/compliance/violations/search** - `backend/app/api/v1/compliance.py`
  - Request model: ComplianceViolationSearchRequest
  - Response model: ComplianceViolationSearchResponse
  - Validation: Standard/severity enums, date ranges

- [ ] **GET /api/v1/optimization/recommendations/search** - `backend/app/api/v1/optimization.py`
  - Request model: RecommendationSearchRequest
  - Response model: RecommendationSearchResponse
  - Validation: Type/priority/status enums, impact range (0-100)

- [ ] **GET /api/v1/predictions/search** - `backend/app/api/v1/predictions.py`
  - Request model: PredictionSearchRequest
  - Response model: PredictionSearchResponse
  - Validation: Type/severity/status enums, confidence range (0.0-1.0)

### Phase 3: Tool Registration (6 tools)

- [ ] **Register search_gateways** - `backend/app/tools/__init__.py`
  - Agent domain: discovery
  - Enhanced description with usage guidance
  - Parameter documentation with examples

- [ ] **Register search_apis** - `backend/app/tools/__init__.py`
  - Agent domain: discovery
  - Guidance on when to prefer over list_all_apis
  - Text search pattern examples

- [ ] **Register search_vulnerabilities** - `backend/app/tools/__init__.py`
  - Agent domain: security
  - Severity/type filtering examples
  - Date range usage patterns

- [ ] **Register search_compliance_violations** - `backend/app/tools/__init__.py`
  - Agent domain: compliance
  - Standard-specific filtering examples
  - Audit reporting use cases

- [ ] **Register search_recommendations** - `backend/app/tools/__init__.py`
  - Agent domain: optimization
  - Priority/impact filtering examples
  - Implementation status tracking

- [ ] **Register search_predictions** - `backend/app/tools/__init__.py`
  - Agent domain: prediction
  - Confidence threshold examples
  - Time range filtering patterns

### Phase 4: Agent Integration

- [ ] **Update DiscoveryAgent system prompt** - `backend/app/agents/query/discovery_agent.py`
  - Add guidance on when to use search_gateways vs list_gateways
  - Add guidance on when to use search_apis vs list_all_apis
  - Include examples of complex filtering scenarios

- [ ] **Update SecurityAgent system prompt** - `backend/app/agents/query/security_agent.py`
  - Add guidance on search_vulnerabilities usage
  - Include severity + date range examples
  - Document API name pattern matching

- [ ] **Update ComplianceAgent system prompt** - `backend/app/agents/query/compliance_agent.py`
  - Add guidance on search_compliance_violations usage
  - Include standard-specific filtering examples
  - Document audit reporting patterns

- [ ] **Update OptimizationAgent system prompt** - `backend/app/agents/query/optimization_agent.py`
  - Add guidance on search_recommendations usage
  - Include priority + impact filtering examples
  - Document implementation tracking patterns

- [ ] **Update PredictionAgent system prompt** - `backend/app/agents/query/prediction_agent.py`
  - Add guidance on search_predictions usage
  - Include confidence threshold examples
  - Document time range filtering patterns

### Phase 5: Testing

- [ ] **Repository search method tests** - `backend/tests/unit/test_repositories/`
  - Test each search method with various filter combinations
  - Test pagination behavior
  - Test empty result handling
  - Test invalid parameter handling

- [ ] **API endpoint tests** - `backend/tests/integration/test_search_apis.py`
  - Test each endpoint with valid parameters
  - Test parameter validation (400 errors)
  - Test pagination
  - Test response format consistency

- [ ] **Tool invocation tests** - `backend/tests/integration/test_search_tools.py`
  - Test each search tool from agent context
  - Test parameter passing
  - Test result parsing
  - Test error handling

- [ ] **Agent integration tests** - `backend/tests/e2e/test_search_agent_integration.py`
  - Test agents selecting search tools for complex queries
  - Test fallback reduction metrics
  - Test multi-criteria filtering scenarios
  - Test text pattern matching accuracy

## OpenSearch Query Patterns

### Text Pattern Matching (Case-Insensitive)

```python
{
    "bool": {
        "should": [
            {"match": {"name": {"query": pattern, "fuzziness": "AUTO"}}},
            {"wildcard": {"name.keyword": {"value": f"*{pattern}*"}}}
        ],
        "minimum_should_match": 1
    }
}
```

### Multiple Filters (AND Logic)

```python
{
    "bool": {
        "must": [
            {"term": {"status": status_value}},
            {"term": {"vendor": vendor_value}}
        ],
        "filter": [
            {"range": {"created_at": {"gte": start_date, "lte": end_date}}}
        ]
    }
}
```

### Range Queries (Numeric/Date)

```python
{
    "range": {
        "health_score": {
            "gte": min_score,
            "lte": max_score
        }
    }
}
```

### Pagination

```python
{
    "from": (page - 1) * page_size,
    "size": page_size,
    "sort": [{"created_at": {"order": "desc"}}]
}
```

## Request/Response Models

### Common Search Response Format

```python
class SearchResponse(BaseModel):
    """Generic search response model."""
    items: List[T]  # Generic type for entity
    total: int
    page: int
    page_size: int
```

### Example: Gateway Search Request

```python
class GatewaySearchRequest(BaseModel):
    """Request model for gateway search."""
    name: Optional[str] = Field(None, description="Name pattern")
    vendor: Optional[GatewayVendor] = None
    status: Optional[GatewayStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
```

## Tool Description Template

```python
"""Search {entity_type} using flexible multi-criteria filtering.

Use this tool when the user's query requires combining multiple filters
that go beyond simple list operations.

IMPORTANT: Prefer this tool over list_{entity} when the query includes:
- Text pattern matching (name/description contains)
- Multiple filter combinations (status AND type AND severity)
- Date range filtering (created/discovered between dates)
- Numeric range filtering (score/confidence thresholds)

Args:
    {parameter_list_with_descriptions}

Returns:
    dict: Search results with:
        - items: List of {entity} objects
        - total: Total matching count
        - page: Current page number
        - page_size: Items per page

Example:
    >>> result = await search_{entity}(
    ...     {example_parameters}
    ... )
    >>> print(f"Found {result['total']} matching {entities}")
"""
```

## Success Metrics

Track these metrics to measure search API effectiveness:

1. **Fallback Reduction**: % decrease in OpenSearch fallback for complex queries
   - Target: 15%+ reduction
   - Measure: Compare fallback rate before/after search APIs

2. **Agent Adoption**: % of multi-criteria queries using search APIs
   - Target: 80%+ adoption
   - Measure: Tool invocation logs

3. **Performance**: Search query response time
   - Target: <2 seconds
   - Measure: API endpoint metrics

4. **Accuracy**: Text search relevance
   - Target: 85%+ relevant results in top 20
   - Measure: User feedback and result analysis

## Common Pitfalls

1. **Forgetting Case-Insensitive Matching**: Always use `.lower()` for text patterns or OpenSearch `match` query
2. **Not Validating Date Formats**: Use Pydantic datetime validation
3. **Incorrect Pagination Math**: Remember `from = (page - 1) * page_size`
4. **Missing Total Count**: Always return total count for pagination
5. **Not Handling Empty Results**: Return empty list with total=0, not error
6. **Forgetting to Register Tools**: Tools must be registered in `__init__.py`
7. **Inconsistent Response Format**: All search APIs must return same structure

## Next Steps

After implementing search APIs:

1. Monitor fallback rate reduction
2. Collect agent tool selection patterns
3. Analyze search query performance
4. Gather user feedback on search accuracy
5. Iterate on tool descriptions based on agent behavior
6. Consider adding more specialized search endpoints if needed