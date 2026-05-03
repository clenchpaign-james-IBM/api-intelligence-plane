# API Reference: API Intelligence Plane

**Version**: 2.0.0
**Last Updated**: 2026-04-14
**Base URL**: `http://localhost:8000` (Development) | `https://api.yourdomain.com` (Production)

**Architecture**: Gateway-First with Vendor-Neutral Data Models

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Common Patterns](#common-patterns)
4. [API Endpoints](#api-endpoints)
   - [APIs](#apis)
   - [Gateways](#gateways)
   - [Metrics](#metrics)
   - [Analytics](#analytics)
   - [Predictions](#predictions)
   - [Optimization](#optimization)
   - [Query](#query)
5. [Response Codes](#response-codes)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Examples](#examples)

---

## Overview

The API Intelligence Plane provides a RESTful API for managing **gateway-first, vendor-neutral** API discovery, monitoring, predictions, security, optimization, and natural language queries. The system uses vendor-neutral data models with vendor-specific adapters, ensuring consistent intelligence capabilities regardless of the underlying API Gateway vendor.

### Key Architecture Features

- **Gateway-First Design**: All operations use Gateway as primary scope dimension, API as secondary
- **Vendor-Neutral Models**: All API data stored in vendor-neutral format with vendor-specific fields in `vendor_metadata`
- **Time-Bucketed Metrics**: Metrics stored separately from API entities in time-bucketed indices (1m, 5m, 1h, 1d)
- **Separated Intelligence**: Intelligence fields (`health_score`, `risk_score`, `security_score`) in `intelligence_metadata` wrapper
- **Policy Actions**: Vendor-neutral policy representation with `vendor_config` for vendor-specific settings
- **Drill-Down Pattern**: Query aggregated metrics, then drill down to raw transactional logs
- **Multi-Gateway Support**: Proper isolation and scoping for multi-gateway deployments

All endpoints return JSON responses and follow REST conventions.

### Gateway-First Query Pattern

**IMPORTANT**: Most endpoints require `gateway_id` as a query parameter (primary dimension). This ensures proper data scoping in multi-gateway deployments.

```http
# Correct: Gateway-scoped query
GET /api/v1/apis?gateway_id=<uuid>

# Correct: Gateway and API scoped query
GET /api/v1/metrics?gateway_id=<uuid>&api_id=<uuid>

# Incorrect: Missing gateway context
GET /api/v1/apis?api_id=<uuid>
```

### API Versioning

All endpoints are versioned under `/api/v1/`. Future versions will be available at `/api/v2/`, etc.

### Content Type

All requests and responses use `application/json` content type unless otherwise specified.

---

## Authentication

**MVP**: No authentication required for development.

**Production** (Future): OAuth 2.0 / OpenID Connect with Bearer tokens.

```http
Authorization: Bearer <token>
```

---

## Common Patterns

### Pagination

List endpoints support pagination with the following query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-based) |
| `page_size` | integer | 20 | Items per page (max: 100) |

**Response Format**:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

### Filtering

Many list endpoints support filtering via query parameters. **Gateway-scoped filtering is required** for most endpoints:

```http
# Gateway-scoped filtering (required)
GET /api/v1/apis?gateway_id=<uuid>&status=active&is_shadow=false
GET /api/v1/predictions?gateway_id=<uuid>&severity=critical&status=active

# Cross-gateway filtering (explicit)
GET /api/v1/metrics/cross-gateway?gateway_ids=<uuid1>&gateway_ids=<uuid2>
```

### Timestamps

All timestamps are in ISO 8601 format (UTC):

```json
{
  "created_at": "2026-03-12T10:30:00Z",
  "updated_at": "2026-03-12T15:45:00Z"
}
```

### UUIDs

All resource IDs are UUIDs in standard format:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## API Endpoints

### APIs

Manage discovered APIs and their metadata.

#### List APIs

```http
GET /api/v1/apis
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20, max: 100) |
| `gateway_id` | UUID | No | Filter by gateway ID |
| `status` | string | No | Filter by status (active, inactive, deprecated, failed) |
| `is_shadow` | boolean | No | Filter shadow APIs |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "gateway_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "User Service API",
      "version": "1.2.3",
      "base_path": "/api/users",
      "endpoints": [
        {
          "path": "/users/{id}",
          "method": "GET",
          "description": "Get user by ID"
        }
      ],
      "methods": ["GET", "POST", "PUT", "DELETE"],
      "authentication_type": "bearer",
      "is_shadow": false,
      "discovery_method": "registered",
      "status": "active",
      "health_score": 95.5,
      "created_at": "2026-03-01T10:00:00Z",
      "updated_at": "2026-03-12T15:30:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

#### Get API Details

```http
GET /api/v1/apis/{api_id}
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | Yes | API identifier |

**Response**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "gateway_id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "User Service API",
  "version_info": {
    "version": "1.2.3",
    "maturity_state": "production"
  },
  "base_path": "/api/users",
  "endpoints": [
    {
      "path": "/users/{id}",
      "method": "GET",
      "description": "Get user by ID",
      "parameters": [
        {
          "name": "id",
          "type": "path",
          "data_type": "string",
          "required": true
        }
      ]
    }
  ],
  "methods": ["GET", "POST", "PUT", "DELETE"],
  "api_definition": {
    "type": "openapi",
    "version": "3.0.0",
    "content": {
      "openapi": "3.0.0",
      "info": {
        "title": "User Service API",
        "version": "1.2.3"
      }
    }
  },
  "ownership": {
    "team": "Platform Team",
    "contact": "platform@example.com",
    "repository": "https://github.com/example/user-service"
  },
  "tags": ["user-management", "core-service"],
  "policy_actions": [
    {
      "action_type": "AUTHENTICATION",
      "enabled": true,
      "stage": "request",
      "description": "Require bearer token validation",
      "vendor_config": {
        "auth_type": "jwt",
        "issuer": "https://auth.example.com"
      }
    },
    {
      "action_type": "RATE_LIMITING",
      "enabled": true,
      "stage": "request",
      "description": "Rate limit to 1000 requests per minute",
      "vendor_config": {
        "requests_per_minute": 1000,
        "burst_size": 100
      }
    }
  ],
  "intelligence_metadata": {
    "is_shadow": false,
    "discovery_method": "registered",
    "discovered_at": "2026-03-01T10:00:00Z",
    "last_seen_at": "2026-03-12T15:30:00Z",
    "health_score": 95.5,
    "risk_score": 18,
    "security_score": 91,
    "usage_trend": "stable"
  },
  "vendor_metadata": {
    "vendor": "webmethods",
    "native_id": "wm-api-123",
    "maturity_state": "Active",
    "owner": "platform-team"
  },
  "status": "active",
  "created_at": "2026-03-01T10:00:00Z",
  "updated_at": "2026-03-12T15:30:00Z"
}
```

**Note**: This response shows the vendor-neutral API structure. Metrics are NOT embedded in the API response - use the `/api/v1/apis/{api_id}/metrics` endpoint to retrieve time-bucketed metrics separately.

**Error Responses**:
- `404 Not Found`: API not found
- `500 Internal Server Error`: Server error
#### Search APIs

```http
GET /api/v1/apis/search
```

**Purpose**: Perform flexible multi-criteria search across APIs with text pattern matching, health score ranges, and date filters. Use this endpoint when you need to combine multiple filters or search by text patterns.

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Text pattern to match in API name (case-insensitive wildcard) |
| `description` | string | No | Text pattern to match in API description |
| `status` | string | No | Filter by status (active, inactive, deprecated, failed) |
| `authentication_type` | string | No | Filter by authentication type (none, basic, bearer, oauth2, api_key) |
| `is_shadow` | boolean | No | Filter shadow APIs |
| `health_score_min` | float | No | Minimum health score (0.0-1.0) |
| `health_score_max` | float | No | Maximum health score (0.0-1.0) |
| `gateway_id` | UUID | No | Filter by gateway ID |
| `created_after` | ISO 8601 datetime | No | Filter APIs created after this date |
| `created_before` | ISO 8601 datetime | No | Filter APIs created before this date |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20, max: 100) |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "gateway_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Payment Service API",
      "version": "2.1.0",
      "base_path": "/api/payments",
      "authentication_type": "bearer",
      "is_shadow": false,
      "status": "active",
      "health_score": 92.5,
      "created_at": "2026-02-15T10:00:00Z",
      "updated_at": "2026-03-12T15:30:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

**Example Queries**:

```http
# Find APIs with "payment" in name created in last 7 days
GET /api/v1/apis/search?name=payment&created_after=2026-03-05T00:00:00Z

# Find active APIs with authentication and high health scores
GET /api/v1/apis/search?status=active&authentication_type=bearer&health_score_min=0.8

# Find shadow APIs with low health scores
GET /api/v1/apis/search?is_shadow=true&health_score_max=0.5
```

**Error Responses**:
- `400 Bad Request`: Invalid parameters (e.g., health_score out of range)
- `500 Internal Server Error`: Server error


#### Get Derived Security Policies

```http
GET /api/v1/apis/{api_id}/security-policies
```

**Purpose**: Returns a derived security-policy view based on normalized `policy_actions`. Filters for security-related policy types: AUTHENTICATION, AUTHORIZATION, TLS, CORS, VALIDATION, DATA_MASKING.

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | Yes | API identifier |

**Response**: `200 OK`

```json
{
  "api_id": "550e8400-e29b-41d4-a716-446655440000",
  "security_policies": [
    {
      "action_type": "AUTHENTICATION",
      "enabled": true,
      "stage": "request",
      "description": "Require bearer token validation",
      "vendor_config": {
        "auth_type": "jwt",
        "issuer": "https://auth.example.com"
      }
    },
    {
      "action_type": "TLS",
      "enabled": true,
      "stage": "transport",
      "description": "Enforce TLS 1.3",
      "vendor_config": {
        "min_version": "1.3",
        "cipher_suites": ["TLS_AES_256_GCM_SHA384"]
      }
    }
  ],
  "total_policies": 2
}
```

---

### Analytics

Query aggregated analytics metrics and drill down into raw transactional logs.

**Architecture**: Three-tier data model
1. **API Metadata**: Vendor-neutral API structure (from `/api/v1/apis`)
2. **Aggregated Metrics**: Time-bucketed metrics (from `/api/v1/analytics/metrics`)
3. **Raw Logs**: Transactional events (from `/api/v1/analytics/logs`)

### Metrics

Metrics are exposed as vendor-neutral, time-bucketed records stored separately from API entities. The frontend should:
1. Fetch API metadata from `/api/v1/apis/{api_id}`
2. Fetch time-bucketed metrics from `/api/v1/apis/{api_id}/metrics` or `/api/v1/analytics/metrics`
3. Drill down to raw logs from `/api/v1/analytics/logs` or `/api/v1/analytics/metrics/{metric_id}/logs`

**Time Buckets**:
- `1m`: 1-minute buckets (24-hour retention)
- `5m`: 5-minute buckets (7-day retention)
- `1h`: 1-hour buckets (30-day retention)
- `1d`: 1-day buckets (90-day retention)

#### Get API Metrics

```http
GET /api/v1/apis/{api_id}/metrics
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | Yes | API identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `time_bucket` | string | No | Bucket size: `1m`, `5m`, `1h`, `1d` |
| `start_time` | ISO 8601 datetime | No | Start of time window |
| `end_time` | ISO 8601 datetime | No | End of time window |
| `limit` | integer | No | Max points to return |

**Response**: `200 OK`

```json
{
  "api_id": "550e8400-e29b-41d4-a716-446655440000",
  "time_bucket": "5m",
  "total_data_points": 2,
  "time_series": [
    {
      "timestamp": "2026-04-11T08:00:00Z",
      "time_bucket": "5m",
      "request_count": 1200,
      "success_count": 1160,
      "status_4xx_count": 25,
      "status_5xx_count": 15,
      "response_time_avg": 145.5,
      "response_time_p50": 110.0,
      "response_time_p95": 220.0,
      "response_time_p99": 310.0,
      "throughput": 4.0
    },
    {
      "timestamp": "2026-04-11T08:05:00Z",
      "time_bucket": "5m",
      "request_count": 980,
      "success_count": 955,
      "status_4xx_count": 18,
      "status_5xx_count": 7,
      "response_time_avg": 132.2,
      "response_time_p50": 102.0,
      "response_time_p95": 205.0,
      "response_time_p99": 290.0,
      "throughput": 3.3
    }
  ],
  "aggregated": {
    "request_count": 2180,
    "success_count": 2115,
    "status_4xx_count": 43,
    "status_5xx_count": 22
  }
}
```

#### Get Derived Security Policies

```http
GET /api/v1/apis/{api_id}/security-policies
```

Returns a derived security-policy view based on normalized `policy_actions`.

#### List Analytics Metrics

```http
GET /api/v1/analytics/metrics
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `gateway_id` | UUID | No | Filter by gateway ID |
| `api_id` | UUID | No | Filter by API ID |
| `application_id` | string | No | Filter by application/client identifier |
| `start_time` | ISO 8601 datetime | No | Start of analytics time window |
| `end_time` | ISO 8601 datetime | No | End of analytics time window |
| `time_bucket` | string | No | Aggregation bucket: `1m`, `5m`, `1h`, `1d` |
| `limit` | integer | No | Max results to return (default: 100) |
| `offset` | integer | No | Result offset for pagination |

**Response**: `200 OK`

```json
{
  "metrics": [
    {
      "id": "9d445dc2-f4cb-4c52-9264-201774db6f5f",
      "gateway_id": "660e8400-e29b-41d4-a716-446655440001",
      "api_id": "orders-api",
      "application_id": "portal-app",
      "operation": "getOrders",
      "timestamp": "2026-04-11T08:00:00",
      "time_bucket": "1h",
      "request_count": 1200,
      "success_count": 1160,
      "failure_count": 40,
      "timeout_count": 5,
      "error_rate": 3.333,
      "availability": 99.2,
      "response_time_avg": 145.5,
      "response_time_min": 35.0,
      "response_time_max": 980.0,
      "response_time_p50": 120.0,
      "response_time_p95": 280.0,
      "response_time_p99": 430.0,
      "gateway_time_avg": 28.0,
      "backend_time_avg": 117.5,
      "throughput": 20.0,
      "total_data_size": 2400000,
      "avg_request_size": 240.0,
      "avg_response_size": 1760.0,
      "cache_hit_count": 300,
      "cache_miss_count": 700,
      "cache_bypass_count": 200,
      "cache_hit_rate": 30.0,
      "status_2xx_count": 1160,
      "status_3xx_count": 0,
      "status_4xx_count": 25,
      "status_5xx_count": 15,
      "status_codes": {
        "200": 1160,
        "400": 10,
        "404": 15,
        "500": 15
      },
      "vendor_metadata": {
        "vendor": "webmethods"
      }
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0,
  "time_bucket": "1h"
}
```

#### Drill Down from Metric to Transactional Logs

```http
GET /api/v1/analytics/metrics/{metric_id}/logs
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metric_id` | UUID | Yes | Metric bucket identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `gateway_id` | UUID | No | Narrow results to a specific gateway |
| `api_id` | UUID | No | Narrow results to a specific API |
| `application_id` | string | No | Narrow results to a specific application |
| `limit` | integer | No | Max logs to return |
| `offset` | integer | No | Result offset |

**Response**: `200 OK`

```json
{
  "metric_id": "9d445dc2-f4cb-4c52-9264-201774db6f5f",
  "logs": [
    {
      "id": "fa2f9634-e4ac-4cd0-9365-bf84c6200ff3",
      "event_type": "transactional",
      "timestamp": 1744360200000,
      "api_id": "orders-api",
      "api_name": "Orders API",
      "api_version": "v1",
      "operation": "getOrders",
      "http_method": "GET",
      "request_path": "/orders/1",
      "request_headers": {
        "accept": "application/json"
      },
      "status_code": 200,
      "response_headers": {
        "content-type": "application/json"
      },
      "client_id": "portal-app",
      "client_name": "Portal App",
      "client_ip": "10.0.0.15",
      "total_time_ms": 120,
      "gateway_time_ms": 20,
      "backend_time_ms": 100,
      "status": "success",
      "correlation_id": "corr-123",
      "cache_status": "miss",
      "backend_url": "http://orders.internal/orders",
      "backend_request_headers": {},
      "backend_response_headers": {},
      "external_calls": [],
      "gateway_id": "660e8400-e29b-41d4-a716-446655440001",
      "created_at": "2026-04-11T08:30:00"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

#### List Raw Transactional Logs

```http
GET /api/v1/analytics/logs
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `gateway_id` | UUID | No | Filter by gateway ID |
| `api_id` | UUID | No | Filter by API ID |
| `application_id` | string | No | Filter by application/client identifier |
| `start_time` | ISO 8601 datetime | No | Start of time window |
| `end_time` | ISO 8601 datetime | No | End of time window |
| `limit` | integer | No | Max logs to return |
| `offset` | integer | No | Result offset |

**Response**: `200 OK`

```json
{
  "logs": [
    {
      "id": "fa2f9634-e4ac-4cd0-9365-bf84c6200ff3",
      "event_type": "transactional",
      "timestamp": 1744360200000,
      "api_id": "orders-api",
      "api_name": "Orders API",
      "api_version": "v1",
      "operation": "getOrders",
      "http_method": "GET",
      "request_path": "/orders/1",
      "status_code": 200,
      "client_id": "portal-app",
      "total_time_ms": 120,
      "gateway_time_ms": 20,
      "backend_time_ms": 100,
      "status": "success",
      "correlation_id": "corr-123",
      "cache_status": "miss",
      "backend_url": "http://orders.internal/orders",
      "backend_request_headers": {},
      "backend_response_headers": {},
      "external_calls": [],
      "gateway_id": "660e8400-e29b-41d4-a716-446655440001",
      "created_at": "2026-04-11T08:30:00"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

---

### Gateways

Manage API Gateway registrations.

#### List Gateways

```http
GET /api/v1/gateways
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20) |
| `vendor` | string | No | Filter by vendor (webmethods, kong, apigee, native) |
| `status` | string | No | Filter by status (active, inactive) |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Production Gateway",
      "vendor": "native",
      "base_url": "http://gateway:8080",
      "status": "active",
      "api_count": 45,
      "last_sync_at": "2026-03-12T15:30:00Z",
      "created_at": "2026-03-01T10:00:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20
}
```
#### Search Gateways

```http
GET /api/v1/gateways/search
```

**Purpose**: Perform flexible multi-criteria search across gateways with text pattern matching and date filters. Use this endpoint when you need to combine multiple filters or search by name patterns.

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Text pattern to match in gateway name (case-insensitive wildcard) |
| `vendor` | string | No | Filter by vendor (webmethods, kong, apigee, native) |
| `status` | string | No | Filter by connection status (connected, disconnected, error) |
| `created_after` | ISO 8601 datetime | No | Filter gateways created after this date |
| `created_before` | ISO 8601 datetime | No | Filter gateways created before this date |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20, max: 100) |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Production Gateway",
      "vendor": "native",
      "base_url": "http://gateway:8080",
      "status": "connected",
      "api_count": 45,
      "last_sync_at": "2026-03-12T15:30:00Z",
      "created_at": "2026-03-01T10:00:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20
}
```

**Example Queries**:

```http
# Find gateways with "prod" in name that are connected
GET /api/v1/gateways/search?name=prod&status=connected

# Find webMethods gateways created in last month
GET /api/v1/gateways/search?vendor=webmethods&created_after=2026-02-12T00:00:00Z

# Find disconnected gateways
GET /api/v1/gateways/search?status=disconnected
```

**Error Responses**:
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error


#### Register Gateway

```http
POST /api/v1/gateways
```

**Request Body**:

```json
{
  "name": "Production Gateway",
  "vendor": "webmethods",
  "base_url": "http://gateway:8080",
  "credentials": {
    "type": "basic",
    "username": "admin",
    "password": "secret"
  },
  "transactional_logs_url": "http://opensearch:9200",
  "transactional_logs_credentials": {
    "type": "basic",
    "username": "admin",
    "password": "admin"
  }
}
```

**Note**: Gateway connections support flexible authentication with separate optional credentials for `base_url` (gateway API) and `transactional_logs_url` (analytics data source).

**Response**: `201 Created`

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "Production Gateway",
  "vendor": "native",
  "base_url": "http://gateway:8080",
  "status": "active",
  "created_at": "2026-03-12T15:30:00Z"
}
```

---

### Metrics

Retrieve API metrics and performance data.

#### Get API Metrics

```http
GET /api/v1/apis/{api_id}/metrics
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | Yes | API identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_time` | datetime | No | Start time (ISO 8601, default: 24h ago) |
| `end_time` | datetime | No | End time (ISO 8601, default: now) |
| `time_bucket` | string | No | Time bucket size: `1m`, `5m`, `1h`, `1d` (default: 5m) |

**Response**: `200 OK`

```json
{
  "api_id": "550e8400-e29b-41d4-a716-446655440000",
  "time_bucket": "5m",
  "total_data_points": 288,
  "time_series": [
    {
      "id": "metric-uuid-1",
      "timestamp": "2026-03-12T15:00:00Z",
      "time_bucket": "5m",
      "request_count": 1500,
      "success_count": 1485,
      "failure_count": 15,
      "error_rate": 1.0,
      "availability": 99.0,
      "response_time_avg": 52.3,
      "response_time_min": 12.5,
      "response_time_max": 450.0,
      "response_time_p50": 45.2,
      "response_time_p95": 120.5,
      "response_time_p99": 250.0,
      "gateway_time_avg": 8.5,
      "backend_time_avg": 43.8,
      "throughput": 5.0,
      "cache_hit_count": 450,
      "cache_miss_count": 1050,
      "cache_hit_rate": 30.0,
      "status_2xx_count": 1485,
      "status_4xx_count": 10,
      "status_5xx_count": 5,
      "vendor_metadata": {
        "vendor": "webmethods"
      }
    }
  ],
  "aggregated": {
    "request_count": 432000,
    "success_count": 427680,
    "failure_count": 4320,
    "avg_response_time": 52.3,
    "avg_error_rate": 1.0,
    "avg_availability": 99.0
  }
}
```

**Note**: Each time series point includes a unique `id` that can be used to drill down to raw transactional logs via `/api/v1/analytics/metrics/{metric_id}/logs`.

**Error Responses**:
- `404 Not Found`: API not found
- `500 Internal Server Error`: Server error

---

### Predictions

Manage API failure predictions.

#### List Predictions

```http
GET /api/v1/predictions
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | No | Filter by API ID |
| `severity` | string | No | Filter by severity (critical, high, medium, low) |
| `status` | string | No | Filter by status (active, resolved, false_positive) |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20) |

**Response**: `200 OK`

```json
{
  "predictions": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "api_id": "550e8400-e29b-41d4-a716-446655440000",
      "prediction_type": "failure",
      "predicted_at": "2026-03-12T15:30:00Z",
      "predicted_time": "2026-03-14T10:00:00Z",
      "confidence_score": 0.85,
      "severity": "high",
      "status": "active",
      "contributing_factors": [
        {
          "factor": "error_rate",
          "current_value": 2.5,
          "threshold": 1.0,
          "trend": "increasing",
          "weight": 0.4
        },
        {
          "factor": "response_time_p95",
          "current_value": 450.0,
          "threshold": 300.0,
          "trend": "increasing",
          "weight": 0.3
        }
      ],
      "recommended_actions": [
        "Scale up service instances",
        "Review recent code changes",
        "Check database connection pool"
      ],
      "model_version": "1.0.0",
      "created_at": "2026-03-12T15:30:00Z",
      "updated_at": "2026-03-12T15:30:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```
#### Search Predictions

```http
GET /api/v1/predictions/search
```

**Purpose**: Perform flexible multi-criteria search across predictions with confidence ranges, prediction types, and time filters. Use this endpoint when you need to combine multiple filters or search by specific criteria.

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prediction_type` | string | No | Filter by prediction type (failure, performance_degradation, capacity_issue) |
| `confidence_min` | float | No | Minimum confidence score (0.0-1.0) |
| `confidence_max` | float | No | Maximum confidence score (0.0-1.0) |
| `severity` | string | No | Filter by severity (critical, high, medium, low) |
| `status` | string | No | Filter by status (active, resolved, false_positive) |
| `predicted_after` | ISO 8601 datetime | No | Filter predictions made after this date |
| `predicted_before` | ISO 8601 datetime | No | Filter predictions made before this date |
| `api_name` | string | No | Text pattern to match in API name |
| `gateway_id` | UUID | No | Filter by gateway ID |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20, max: 100) |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "api_id": "550e8400-e29b-41d4-a716-446655440000",
      "api_name": "Payment Service API",
      "prediction_type": "failure",
      "predicted_at": "2026-03-12T15:30:00Z",
      "predicted_time": "2026-03-14T10:00:00Z",
      "confidence_score": 0.85,
      "severity": "high",
      "status": "active"
    }
  ],
  "total": 8,
  "page": 1,
  "page_size": 20
}
```

**Example Queries**:

```http
# Find high-confidence predictions (>80%) for production gateway
GET /api/v1/predictions/search?confidence_min=0.8&gateway_id=<uuid>

# Find critical failure predictions from last week
GET /api/v1/predictions/search?prediction_type=failure&severity=critical&predicted_after=2026-03-05T00:00:00Z

# Find active predictions with confidence between 70-90%
GET /api/v1/predictions/search?status=active&confidence_min=0.7&confidence_max=0.9
```

**Error Responses**:
- `400 Bad Request`: Invalid parameters (e.g., confidence out of range)
- `500 Internal Server Error`: Server error


#### Get Prediction Details

```http
GET /api/v1/predictions/{prediction_id}
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prediction_id` | UUID | Yes | Prediction identifier |

**Response**: `200 OK`

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "api_id": "550e8400-e29b-41d4-a716-446655440000",
  "prediction_type": "failure",
  "predicted_at": "2026-03-12T15:30:00Z",
  "predicted_time": "2026-03-14T10:00:00Z",
  "confidence_score": 0.85,
  "severity": "high",
  "status": "active",
  "contributing_factors": [...],
  "recommended_actions": [...],
  "actual_outcome": null,
  "actual_time": null,
  "accuracy_score": null,
  "model_version": "1.0.0",
  "created_at": "2026-03-12T15:30:00Z",
  "updated_at": "2026-03-12T15:30:00Z"
}
```

#### Generate Predictions

```http
POST /api/v1/predictions/generate
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | No | Generate for specific API (all if not provided) |
| `min_confidence` | float | No | Minimum confidence threshold (0-1, default: 0.7) |
| `use_ai` | boolean | No | Use AI-enhanced generation (default: false) |

**Response**: `202 Accepted`

```json
{
  "status": "accepted",
  "message": "Generated 3 predictions for API 550e8400-e29b-41d4-a716-446655440000",
  "predictions_generated": 3
}
```

#### Generate AI-Enhanced Predictions

```http
POST /api/v1/predictions/ai-enhanced
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | Yes | API ID to generate predictions for |
| `min_confidence` | float | No | Minimum confidence threshold (0-1, default: 0.7) |

**Response**: `200 OK`

```json
{
  "status": "success",
  "result": {
    "predictions": [...],
    "ai_analysis": {
      "trend_analysis": "Error rate showing exponential growth pattern",
      "risk_assessment": "High probability of service degradation within 48 hours",
      "confidence_factors": [...]
    }
  }
}
```

#### Get Prediction Explanation

```http
GET /api/v1/predictions/{prediction_id}/explanation
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prediction_id` | UUID | Yes | Prediction identifier |

**Response**: `200 OK`

```json
{
  "status": "success",
  "prediction_id": "770e8400-e29b-41d4-a716-446655440002",
  "explanation": "This prediction indicates a high probability of API failure within the next 48 hours. The primary contributing factors are: 1) Error rate has increased by 150% over the past 6 hours, exceeding the threshold of 1%. 2) Response time at 95th percentile has degraded to 450ms, 50% above the normal baseline. 3) Database connection pool utilization is at 85%, indicating potential resource exhaustion. Recommended immediate actions include scaling up service instances and reviewing recent deployments."
}
```

#### Get Prediction Accuracy Statistics

```http
GET /api/v1/predictions/stats/accuracy
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | No | Filter by API ID |
| `days` | integer | No | Days to look back (1-90, default: 30) |

**Response**: `200 OK`

```json
{
  "status": "success",
  "stats": {
    "total_predictions": 150,
    "accurate_predictions": 127,
    "false_positives": 18,
    "false_negatives": 5,
    "accuracy_rate": 0.847,
    "precision": 0.876,
    "recall": 0.962,
    "avg_confidence": 0.82
  },
  "period_days": 30
}
```

---

### Optimization

Manage performance optimization recommendations.

#### List Recommendations

```http
GET /api/v1/recommendations
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | No | Filter by API ID |
| `priority` | string | No | Filter by priority (critical, high, medium, low) |
| `status` | string | No | Filter by status (pending, implemented, rejected, expired) |
| `recommendation_type` | string | No | Filter by type (caching, query_optimization, resource_allocation, etc.) |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20) |

**Response**: `200 OK`

```json
{
  "recommendations": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440003",
      "api_id": "550e8400-e29b-41d4-a716-446655440000",
      "recommendation_type": "caching",
      "title": "Implement Redis caching for user profile endpoints",
      "description": "Analysis shows 85% of requests are for the same user profiles. Implementing Redis caching can significantly reduce database load and improve response times.",
      "priority": "high",
      "estimated_impact": {
        "metric": "response_time_p95",
        "current_value": 450.0,
        "expected_value": 120.0,
        "improvement_percentage": 73.3,
        "confidence": 0.9
      },
      "implementation_effort": "medium",
      "implementation_steps": [
        "Set up Redis cluster",
        "Implement cache-aside pattern",
        "Configure TTL policies",
        "Add cache invalidation logic"
      ],
      "status": "pending",
      "cost_savings": 1200.0,
      "created_at": "2026-03-12T15:30:00Z",
      "updated_at": "2026-03-12T15:30:00Z",
      "expires_at": "2026-03-19T15:30:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 20
}
```
#### Search Recommendations

```http
GET /api/v1/optimization/recommendations/search
```

**Purpose**: Perform flexible multi-criteria search across optimization recommendations with type, priority, status filters, and impact ranges. Use this endpoint when you need to combine multiple filters or search by specific criteria.

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | No | Filter by recommendation type (caching, query_optimization, resource_allocation, rate_limiting, connection_pooling, load_balancing, circuit_breaker, retry_policy, timeout_tuning, compression) |
| `priority` | string | No | Filter by priority (critical, high, medium, low) |
| `status` | string | No | Filter by status (pending, implemented, rejected, expired) |
| `impact_min` | float | No | Minimum expected improvement percentage (0-100) |
| `impact_max` | float | No | Maximum expected improvement percentage (0-100) |
| `api_name` | string | No | Text pattern to match in API name |
| `gateway_id` | UUID | No | Filter by gateway ID |
| `created_after` | ISO 8601 datetime | No | Filter recommendations created after this date |
| `created_before` | ISO 8601 datetime | No | Filter recommendations created before this date |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20, max: 100) |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440003",
      "api_id": "550e8400-e29b-41d4-a716-446655440000",
      "api_name": "User Service API",
      "recommendation_type": "caching",
      "title": "Implement Redis caching for user profile endpoints",
      "priority": "high",
      "estimated_impact": {
        "improvement_percentage": 73.3,
        "confidence": 0.9
      },
      "status": "pending",
      "created_at": "2026-03-12T15:30:00Z"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20
}
```

**Example Queries**:

```http
# Find high-priority caching recommendations that are pending
GET /api/v1/optimization/recommendations/search?type=caching&priority=high&status=pending

# Find recommendations with high impact (>50%) from last week
GET /api/v1/optimization/recommendations/search?impact_min=50&created_after=2026-03-05T00:00:00Z

# Find all pending recommendations for APIs with "payment" in name
GET /api/v1/optimization/recommendations/search?status=pending&api_name=payment
```

**Error Responses**:
- `400 Bad Request`: Invalid parameters (e.g., impact out of range 0-100)
- `500 Internal Server Error`: Server error


#### Get Recommendation Details

```http
GET /api/v1/recommendations/{recommendation_id}
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `recommendation_id` | UUID | Yes | Recommendation identifier |

**Response**: `200 OK`

```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "api_id": "550e8400-e29b-41d4-a716-446655440000",
  "recommendation_type": "caching",
  "title": "Implement Redis caching for user profile endpoints",
  "description": "...",
  "priority": "high",
  "estimated_impact": {...},
  "implementation_effort": "medium",
  "implementation_steps": [...],
  "status": "pending",
  "cost_savings": 1200.0,
  "created_at": "2026-03-12T15:30:00Z",
  "updated_at": "2026-03-12T15:30:00Z",
  "expires_at": "2026-03-19T15:30:00Z"
}
```

#### Generate Recommendations

```http
POST /api/v1/recommendations/generate
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | Yes | API ID to generate recommendations for |
| `min_impact` | float | No | Minimum expected improvement % (0-100, default: 10.0) |
| `use_ai` | boolean | No | Use AI-enhanced generation (default: false) |

**Response**: `200 OK`

```json
{
  "api_id": "550e8400-e29b-41d4-a716-446655440000",
  "recommendations_generated": 5,
  "recommendations": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440003",
      "type": "caching",
      "title": "Implement Redis caching",
      "priority": "high",
      "expected_improvement": 73.3
    }
  ]
}
```

#### Generate AI-Enhanced Recommendations

```http
POST /api/v1/recommendations/ai-enhanced
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | Yes | API ID to generate recommendations for |
| `min_impact` | float | No | Minimum expected improvement % (default: 10.0) |

**Response**: `200 OK`

```json
{
  "status": "success",
  "result": {
    "recommendations": [...],
    "ai_insights": {
      "performance_analysis": "API shows consistent high latency during peak hours",
      "optimization_strategy": "Prioritize caching and query optimization",
      "implementation_guidance": "Start with low-effort, high-impact changes"
    }
  }
}
```

#### Get Recommendation Insights

```http
GET /api/v1/recommendations/{recommendation_id}/insights
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `recommendation_id` | UUID | Yes | Recommendation identifier |

**Response**: `200 OK`

```json
{
  "status": "success",
  "recommendation_id": "880e8400-e29b-41d4-a716-446655440003",
  "insights": {
    "detailed_analysis": "...",
    "implementation_tips": [...],
    "potential_risks": [...],
    "success_metrics": [...]
  }
}
```

#### Get Recommendation Statistics

```http
GET /api/v1/recommendations/stats
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_id` | UUID | No | Filter by API ID |
| `days` | integer | No | Days to look back (1-365, default: 30) |

**Response**: `200 OK`

```json
{
  "total_recommendations": 125,
  "by_status": [
    {"status": "pending", "count": 45},
    {"status": "implemented", "count": 65},
    {"status": "rejected", "count": 10},
    {"status": "expired", "count": 5}
  ],
  "by_priority": [
    {"priority": "critical", "count": 5},
    {"priority": "high", "count": 25},
    {"priority": "medium", "count": 60},
    {"priority": "low", "count": 35}
  ],
  "by_type": [
    {"type": "caching", "count": 30},
    {"type": "query_optimization", "count": 25},
    {"type": "resource_allocation", "count": 20}
  ],
  "avg_improvement": 45.2,
  "total_cost_savings": 15000.0
}
```

---
---

### Security

Manage security vulnerabilities and findings.

#### Search Vulnerabilities

```http
GET /api/v1/security/vulnerabilities/search
```

**Purpose**: Perform flexible multi-criteria search across security vulnerabilities with severity, type, status filters, and date ranges. Use this endpoint when you need to combine multiple filters or search by specific criteria.

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `severity` | string | No | Filter by severity (critical, high, medium, low, informational) |
| `type` | string | No | Filter by vulnerability type (sql_injection, xss, authentication_bypass, sensitive_data_exposure, etc.) |
| `status` | string | No | Filter by status (open, in_progress, resolved, false_positive) |
| `api_name` | string | No | Text pattern to match in API name |
| `gateway_id` | UUID | No | Filter by gateway ID |
| `discovered_after` | ISO 8601 datetime | No | Filter vulnerabilities discovered after this date |
| `discovered_before` | ISO 8601 datetime | No | Filter vulnerabilities discovered before this date |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20, max: 100) |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440004",
      "api_id": "550e8400-e29b-41d4-a716-446655440000",
      "api_name": "Payment Service API",
      "gateway_id": "660e8400-e29b-41d4-a716-446655440001",
      "vulnerability_type": "sql_injection",
      "severity": "critical",
      "status": "open",
      "title": "SQL Injection vulnerability in payment endpoint",
      "description": "Unsanitized user input in payment query parameter",
      "discovered_at": "2026-03-12T10:00:00Z",
      "cvss_score": 9.8
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

**Example Queries**:

```http
# Find critical vulnerabilities this month affecting APIs with "user"
GET /api/v1/security/vulnerabilities/search?severity=critical&discovered_after=2026-03-01T00:00:00Z&api_name=user

# Find open SQL injection vulnerabilities
GET /api/v1/security/vulnerabilities/search?type=sql_injection&status=open

# Find all high/critical vulnerabilities for a specific gateway
GET /api/v1/security/vulnerabilities/search?gateway_id=<uuid>&severity=critical,high
```

**Error Responses**:
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error

---

### Compliance

Manage compliance violations and audit findings.

#### Search Compliance Violations

```http
GET /api/v1/compliance/violations/search
```

**Purpose**: Perform flexible multi-criteria search across compliance violations with standard, violation type, severity filters, and date ranges. Use this endpoint when you need to combine multiple filters or search by specific criteria.

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `standard` | string | No | Filter by compliance standard (GDPR, HIPAA, PCI_DSS, SOC2, ISO27001, CCPA) |
| `violation_type` | string | No | Filter by violation type (data_retention, encryption, access_control, audit_logging, etc.) |
| `severity` | string | No | Filter by severity (critical, high, medium, low) |
| `status` | string | No | Filter by status (open, in_progress, resolved, accepted_risk) |
| `api_name` | string | No | Text pattern to match in API name |
| `gateway_id` | UUID | No | Filter by gateway ID |
| `discovered_after` | ISO 8601 datetime | No | Filter violations discovered after this date |
| `discovered_before` | ISO 8601 datetime | No | Filter violations discovered before this date |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20, max: 100) |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440005",
      "api_id": "550e8400-e29b-41d4-a716-446655440000",
      "api_name": "User Service API",
      "gateway_id": "660e8400-e29b-41d4-a716-446655440001",
      "standard": "GDPR",
      "violation_type": "data_retention",
      "severity": "high",
      "status": "open",
      "title": "User data retained beyond 90-day limit",
      "description": "Personal data is being retained for 180 days, exceeding GDPR requirements",
      "discovered_at": "2026-03-10T14:00:00Z",
      "remediation_deadline": "2026-03-24T14:00:00Z"
    }
  ],
  "total": 8,
  "page": 1,
  "page_size": 20
}
```

**Example Queries**:

```http
# Find GDPR violations with high severity from last quarter
GET /api/v1/compliance/violations/search?standard=GDPR&severity=high&discovered_after=2025-12-01T00:00:00Z

# Find open data retention violations
GET /api/v1/compliance/violations/search?violation_type=data_retention&status=open

# Find all compliance violations for APIs with "payment" in name
GET /api/v1/compliance/violations/search?api_name=payment
```

**Error Responses**:
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error


### Query

Natural language query interface.

#### Execute Query

```http
POST /api/v1/query
```

**Request Body**:

```json
{
  "query_text": "Show me APIs with high error rates in the last 24 hours",
  "session_id": "990e8400-e29b-41d4-a716-446655440004",
  "use_ai_agents": true
}
```

**Response**: `200 OK`

```json
{
  "query_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "query_text": "Show me APIs with high error rates in the last 24 hours",
  "response_text": "I found 3 APIs with elevated error rates in the last 24 hours: User Service API (error rate: 2.5%), Payment API (error rate: 1.8%), and Notification API (error rate: 1.2%). The User Service API shows the most concerning trend with errors increasing by 150% over the past 6 hours.",
  "confidence_score": 0.92,
  "results": {
    "query_type": "health",
    "apis": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "User Service API",
        "error_rate": 2.5,
        "trend": "increasing"
      }
    ],
    "total_count": 3
  },
  "follow_up_queries": [
    "What are the specific errors in User Service API?",
    "Show me predictions for these APIs",
    "What optimizations are recommended?"
  ],
  "execution_time_ms": 1250
}
```

#### Get Query by ID

```http
GET /api/v1/query/{query_id}
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query_id` | UUID | Yes | Query identifier |

**Response**: `200 OK`

```json
{
  "id": "aa0e8400-e29b-41d4-a716-446655440005",
  "session_id": "990e8400-e29b-41d4-a716-446655440004",
  "query_text": "Show me APIs with high error rates",
  "response_text": "...",
  "confidence_score": 0.92,
  "results": {...},
  "follow_up_queries": [...],
  "execution_time_ms": 1250,
  "user_feedback": null,
  "created_at": "2026-03-12T15:30:00Z"
}
```

#### Get Session Queries

```http
GET /api/v1/query/session/{session_id}
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | UUID | Yes | Session identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 50) |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440005",
      "query_text": "Show me APIs with high error rates",
      "response_text": "...",
      "confidence_score": 0.92,
      "created_at": "2026-03-12T15:30:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 50
}
```

#### Get Recent Queries

```http
GET /api/v1/query/recent
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | No | Filter by user ID |
| `hours` | integer | No | Hours to look back (default: 24) |
| `size` | integer | No | Maximum results (default: 20) |

**Response**: `200 OK`

```json
[
  {
    "id": "aa0e8400-e29b-41d4-a716-446655440005",
    "query_text": "Show me APIs with high error rates",
    "confidence_score": 0.92,
    "created_at": "2026-03-12T15:30:00Z"
  }
]
```

#### Submit Query Feedback

```http
POST /api/v1/query/{query_id}/feedback
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query_id` | UUID | Yes | Query identifier |

**Request Body**:

```json
{
  "feedback": "helpful",
  "comment": "Exactly what I needed"
}
```

**Feedback Values**: `helpful`, `not_helpful`, `partially_helpful`

**Response**: `200 OK`

```json
{
  "id": "aa0e8400-e29b-41d4-a716-446655440005",
  "query_text": "Show me APIs with high error rates",
  "user_feedback": "helpful",
  "feedback_comment": "Exactly what I needed",
  "updated_at": "2026-03-12T15:35:00Z"
}
```

#### Get Query Statistics

```http
GET /api/v1/query/statistics
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | UUID | No | Filter by session |
| `hours` | integer | No | Hours to look back (default: 24) |

**Response**: `200 OK`

```json
{
  "total_queries": 150,
  "avg_confidence": 0.87,
  "avg_execution_time_ms": 1350,
  "by_query_type": [
    {"type": "health", "count": 45},
    {"type": "prediction", "count": 35},
    {"type": "performance", "count": 30},
    {"type": "security", "count": 25},
    {"type": "general", "count": 15}
  ],
  "feedback_distribution": [
    {"feedback": "helpful", "count": 120},
    {"feedback": "partially_helpful", "count": 20},
    {"feedback": "not_helpful", "count": 10}
  ]
}
```

---

## Response Codes

| Code | Description |
|------|-------------|
| `200 OK` | Request successful |
| `201 Created` | Resource created successfully |
| `202 Accepted` | Request accepted for processing |
| `400 Bad Request` | Invalid request parameters |
| `401 Unauthorized` | Authentication required |
| `403 Forbidden` | Insufficient permissions |
| `404 Not Found` | Resource not found |
| `422 Unprocessable Entity` | Validation error |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Server error |
| `503 Service Unavailable` | Service temporarily unavailable |

---

## Error Handling

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 404,
  "timestamp": "2026-03-12T15:30:00Z"
}
```

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "query_text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "status_code": 422
}
```

---

## Rate Limiting

**MVP**: No rate limiting

**Production** (Future):
- Rate limits will be enforced per API key
- Headers will indicate rate limit status:
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

---

## Examples

### Example 1: Discover APIs with High Error Rates

```bash
# Execute natural language query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Show me APIs with error rates above 1% in the last hour",
    "use_ai_agents": true
  }'

# Response
{
  "query_id": "...",
  "response_text": "Found 2 APIs with error rates above 1%...",
  "results": {
    "apis": [...]
  }
}
```

### Example 2: Generate AI-Enhanced Predictions

```bash
# Generate predictions with AI analysis
curl -X POST "http://localhost:8000/api/v1/predictions/ai-enhanced?api_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json"

# Response
{
  "status": "success",
  "result": {
    "predictions": [...],
    "ai_analysis": {
      "trend_analysis": "...",
      "risk_assessment": "..."
    }
  }
}
```

### Example 3: Get Optimization Recommendations

```bash
# Generate recommendations for an API
curl -X POST "http://localhost:8000/api/v1/recommendations/generate?api_id=550e8400-e29b-41d4-a716-446655440000&min_impact=20" \
  -H "Content-Type: application/json"

# Response
{
  "api_id": "550e8400-e29b-41d4-a716-446655440000",
  "recommendations_generated": 3,
  "recommendations": [...]
}
```

### Example 4: Monitor API Metrics

```bash
# Get metrics for the last 6 hours with 15-minute intervals
curl "http://localhost:8000/api/v1/apis/550e8400-e29b-41d4-a716-446655440000/metrics?start_time=2026-03-12T09:00:00Z&end_time=2026-03-12T15:00:00Z&interval=15m"

# Response
{
  "api_id": "550e8400-e29b-41d4-a716-446655440000",
  "time_series": [...],
  "aggregated": {...}
}
```

---

## Additional Resources

- [Architecture Documentation](./architecture.md)
- [Deployment Guide](./deployment.md)
- [AI Setup Guide](./ai-setup.md)
- [MCP Integration](./mcp-architecture.md)

---

**Need Help?**

- 📧 Email: support@api-intelligence-plane.com
- 💬 Discord: [Join our community](https://discord.gg/api-intelligence-plane)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/api-intelligence-plane-v2/issues)