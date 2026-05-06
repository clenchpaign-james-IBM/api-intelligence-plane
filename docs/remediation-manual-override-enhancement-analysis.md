# Remediation Manual Override Enhancement Analysis

**Date:** 2026-05-05  
**Status:** Analysis / Proposal  
**Scope:** Security vulnerability remediation and Optimization recommendation application

## Executive Summary

The current remediation flows for both Security and Optimization support automated policy application to gateways, but they rely on hard-coded default policy values embedded in backend services. This makes the feature functional but rigid.

The enhancement opportunity is to let users review the proposed remediation policy, adjust selected values before applying it, and preserve those user-supplied values as part of the remediation audit trail. This is especially useful for cases where the system can identify the correct policy type, but cannot know the right production threshold or security parameters for a given API.

This enhancement should be implemented as a **manual-analysis assisted override layer** on top of the existing automated remediation flows, not as a replacement. The system should continue to generate a safe default policy draft, while allowing users to override supported fields before the gateway adapter applies the policy.

## Current State Analysis

### 1. Optimization remediation currently uses fixed backend defaults

[`OptimizationService.apply_recommendation_to_gateway()`](../backend/app/services/optimization_service.py:1061) constructs a [`PolicyAction`](../backend/app/models/base/api.py) directly in the service layer and embeds static config values.

#### Current caching defaults
In [`backend/app/services/optimization_service.py`](../backend/app/services/optimization_service.py:1171), caching is always applied with:

- `ttl_seconds = 300`
- `cache_key_strategy = "url_headers"`
- `vary_headers = ["Accept", "Accept-Encoding"]`
- `cache_methods = ["GET", "HEAD"]`
- `cache_status_codes = [200, 203, 204, 206, 300, 301]`
- `invalidate_on_methods = ["POST", "PUT", "PATCH", "DELETE"]`

#### Current rate limiting defaults
In [`backend/app/services/optimization_service.py`](../backend/app/services/optimization_service.py:1196), rate limiting is always applied with:

- `requests_per_second = 100`
- `requests_per_minute = 5000`
- `requests_per_hour = 250000`
- `concurrent_requests = 50`
- `rate_limit_key = "ip"`
- `enforcement_action = "throttle"`

These values are not derived from API traffic profile, gateway vendor, tenant-specific baseline, or user input.

### 2. Security remediation also uses fixed backend defaults

[`SecurityService.remediate_vulnerability()`](../backend/app/services/security_service.py:264) eventually calls [`_apply_automated_remediation()`](../backend/app/services/security_service.py:640), where policy payloads are built with fixed defaults based on vulnerability type.

#### Current authentication defaults
In [`backend/app/services/security_service.py`](../backend/app/services/security_service.py:654), authentication remediation always applies:

- `auth_type = "oauth2"`
- `oauth_provider = "default"`
- `oauth_scopes = ["read", "write"]`
- `allow_anonymous = False`
- `cache_credentials = True`
- `cache_ttl_seconds = 300`

#### Current rate limiting defaults for security findings
In [`backend/app/services/security_service.py`](../backend/app/services/security_service.py:738), security rate limiting remediation always applies:

- `requests_per_minute = 100`
- `burst_allowance = 20`
- `rate_limit_key = "ip"`
- `enforcement_action = "reject"`

#### Current TLS defaults
In [`backend/app/services/security_service.py`](../backend/app/services/security_service.py:776), TLS remediation always applies:

- `enforce_tls = True`
- `min_tls_version = "1.2"`
- `allowed_cipher_suites = ["TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384"]`
- `require_client_certificate = False`
- `verify_backend_certificate = True`

### 3. The underlying policy config models already support structured manual input

The good news is the configuration layer is already strongly typed and suitable for controlled overrides:

- [`RateLimitConfig`](../backend/app/models/base/policy_configs.py:33)
- [`AuthenticationConfig`](../backend/app/models/base/policy_configs.py:88)
- [`CachingConfig`](../backend/app/models/base/policy_configs.py:232)
- [`TlsConfig`](../backend/app/models/base/policy_configs.py:466)

This means the system does **not** need a new free-form configuration model. It should reuse these structured Pydantic models as the override contract.

### 4. Adapters already accept vendor-neutral policy actions

Gateway adapters already operate on vendor-neutral [`PolicyAction`](../backend/app/models/base/api.py) inputs:

- [`apply_rate_limit_policy()`](../backend/app/adapters/base.py:118)
- [`apply_caching_policy()`](../backend/app/adapters/base.py:147)

This is important because the enhancement belongs above the adapter layer. The override logic should shape the vendor-neutral config before it reaches the adapter. No fundamental adapter redesign is required.

### 5. Current frontend flows are apply-now, not review-and-edit

The frontend currently exposes direct remediation/apply actions:

- [`api.recommendations.applyToGateway()`](../frontend/src/services/api.ts:213)
- [`remediateVulnerability()`](../frontend/src/services/security.ts:134)
- [`Optimization.tsx`](../frontend/src/pages/Optimization.tsx:148)

This indicates the current UX pattern is immediate execution after user confirmation. There is no policy draft review form and no editable parameter surface.

## Problem Statement

The current implementation answers **what** policy should be applied, but not **what values** should be used in the target environment.

Examples:

- A rate limit of `100 req/min` may be too strict for one API and too lax for another.
- OAuth2 may be correct, but the provider and scopes may differ by domain.
- TLS `1.2` may be acceptable in one environment, but another may require `1.3`.
- A cache TTL of `300s` may be too high for volatile APIs and too low for static ones.

Because defaults are hard-coded in service methods, users cannot tune remediation at the moment of action without code changes.

## Enhancement Goal

Allow users to:

1. Trigger remediation or recommendation apply as they do today.
2. See the proposed default policy configuration before execution.
3. Manually adjust supported fields.
4. Submit the reviewed configuration for application.
5. Persist both the generated default values and the user overrides for auditability.

## Recommended Product Behavior

### Recommended UX pattern: "Review Policy Before Apply"

For both Security and Optimization:

1. User clicks **Remediate** or **Apply to Gateway**
2. System opens a modal/drawer with:
   - remediation type
   - generated default values
   - editable fields
   - vendor-specific warnings if needed
   - optional "manual analysis notes"
3. User can:
   - accept defaults
   - adjust values
   - optionally save rationale/notes
4. User confirms application
5. Backend validates overrides against the structured config model
6. Adapter applies the resulting [`PolicyAction`](../backend/app/models/base/api.py)
7. Audit trail stores:
   - default config snapshot
   - final applied config
   - overridden fields
   - notes / rationale
   - actor identity

### Keep one-click remediation as a fallback

For operational speed, one-click apply should remain available for low-risk environments. The UI can support:

- **Quick Apply** → existing behavior using defaults
- **Review & Customize** → new enhancement flow

This preserves existing efficiency while enabling control where required.

## Recommended Design

## 1. Introduce a policy draft / override contract

The cleanest design is to separate:

- **default recommendation generation**
- **user override capture**
- **final policy construction**

### Proposed request contract

For Optimization:

```json
{
  "override_config": {
    "ttl_seconds": 120,
    "cache_key_strategy": "url_query",
    "vary_headers": ["Accept"]
  },
  "manual_analysis": {
    "reason": "API responses change frequently during business hours",
    "reviewed_by": "ops-user"
  }
}
```

For Security:

```json
{
  "override_config": {
    "requests_per_minute": 500,
    "burst_allowance": 50,
    "enforcement_action": "throttle"
  },
  "manual_analysis": {
    "reason": "Public API requires softer rollout than reject-first policy",
    "reviewed_by": "security-admin"
  }
}
```

The `override_config` should be validated against the correct typed model for the remediation type.

## 2. Add a draft generation layer in the backend

Today, defaults are created inline inside service methods. That is the main maintainability problem.

Instead, introduce a deterministic builder layer, for example:

- `build_optimization_policy_draft(recommendation, api, gateway)`
- `build_security_policy_draft(vulnerability, api, gateway)`

Each builder should return:

- `policy_action_type`
- `default_config`
- `editable_fields`
- `field_descriptions`
- `risk_notes`
- `vendor_constraints`

This improves separation of concerns:

- service layer = orchestration
- draft builder = default selection
- adapter = vendor application

## 3. Merge defaults with overrides before adapter invocation

Proposed execution pattern:

1. Build default typed config
2. Apply validated user overrides
3. Produce final typed config
4. Create [`PolicyAction`](../backend/app/models/base/api.py)
5. Pass to adapter

Pseudo-flow:

```python
default_config = build_default_config(...)
validated_override = ConfigModel(**override_config)
final_config = merge_config(default_config, validated_override, override_fields_only=True)
policy = PolicyAction(..., config=final_config)
await adapter.apply_x_policy(api_id, policy)
```

Important: merge must be partial-field aware. If the user supplies only one field, other fields should remain at generated defaults.

## 4. Persist audit metadata for manual analysis

Current models already contain audit-friendly action structures:

- [`OptimizationAction`](../backend/app/models/recommendation.py:74)
- [`recommended_remediation`](../backend/app/models/vulnerability.py:328)
- remediation action history in both domains

The enhancement should persist:

- `generated_default_config`
- `applied_config`
- `override_fields`
- `manual_analysis.reason`
- `manual_analysis.reviewed_by`
- `manual_analysis.reviewed_at`

### Recommended storage locations

For Optimization:
- store in [`OptimizationAction.metadata`](../backend/app/models/recommendation.py:120)
- optionally also in `vendor_metadata` for applied policy snapshot linkage

For Security:
- store in vulnerability `metadata`
- and/or remediation action metadata for per-attempt traceability

## 5. Add a preview endpoint before apply

Recommended new endpoints:

### Optimization
- `POST /api/v1/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/preview`
- existing apply endpoint enhanced to accept optional override body

### Security
- `POST /api/v1/gateways/{gateway_id}/security/vulnerabilities/{vulnerability_id}/preview-remediation`
- existing remediate endpoint enhanced to accept optional override body

Preview response should include:

```json
{
  "policy_type": "rate_limiting",
  "default_config": { ... },
  "editable_fields": [ ... ],
  "field_metadata": { ... },
  "manual_analysis_required": false,
  "warnings": [ ... ]
}
```

This preview-first pattern is better than forcing the UI to infer form fields from backend types.

## Supported Override Scope

Not every field should be user-editable at first release.

### Phase 1 recommended editable fields

#### Optimization - Caching
From [`CachingConfig`](../backend/app/models/base/policy_configs.py:232):

- `ttl_seconds`
- `cache_key_strategy`
- `vary_headers`
- `vary_query_params`
- `respect_cache_control_headers`
- `cache_methods`
- `cache_status_codes`
- `max_payload_size_bytes`
- `invalidate_on_methods`

#### Optimization - Rate Limiting
From [`RateLimitConfig`](../backend/app/models/base/policy_configs.py:33):

- `requests_per_second`
- `requests_per_minute`
- `requests_per_hour`
- `concurrent_requests`
- `burst_allowance`
- `rate_limit_key`
- `custom_key_header`
- `enforcement_action`
- `include_rate_limit_headers`

#### Security - Authentication
From [`AuthenticationConfig`](../backend/app/models/base/policy_configs.py:88):

- `auth_type`
- `oauth_provider`
- `oauth_scopes`
- `oauth_token_endpoint`
- `jwt_issuer`
- `jwt_audience`
- `jwt_public_key_url`
- `api_key_header`
- `allow_anonymous`
- `cache_credentials`
- `cache_ttl_seconds`

#### Security - TLS
From [`TlsConfig`](../backend/app/models/base/policy_configs.py:466):

- `min_tls_version`
- `allowed_cipher_suites`
- `require_client_certificate`
- `verify_backend_certificate`

#### Security - Rate Limiting
Use the same editable subset as Optimization rate limiting.

### Phase 1 fields that should remain system-controlled

- `action_type`
- `enabled`
- `stage`
- generated names/descriptions
- gateway/vendor identifiers
- remediation status transitions
- adapter selection
- policy linkage IDs

This prevents users from breaking orchestration semantics.

## Manual Analysis Concept

The user mentioned "update/provide different values against the default values with a manual analysis." The most appropriate interpretation is:

- system proposes defaults
- user performs human review
- user changes fields where business/security context requires it
- user records rationale

### Recommended manual analysis model

```json
{
  "reason": "Higher minute limit required for partner traffic burst",
  "risk_acknowledgement": "Using throttle instead of reject for rollout",
  "reviewed_by": "alice@example.com",
  "change_summary": [
    "requests_per_minute: 100 -> 500",
    "burst_allowance: 20 -> 50"
  ]
}
```

This is especially valuable for governance and future explainability.

## Benefits of This Enhancement

### 1. Better production safety
Users can prevent over-restrictive or under-protective policies.

### 2. Better governance
Audit trail will show not just that a remediation happened, but why specific values were chosen.

### 3. Better reusability of current architecture
The typed config models and adapter abstraction already support this enhancement well.

### 4. Reduced hard-coded policy debt
Moving defaults into policy draft builders makes the system easier to evolve.

## Risks and Challenges

### 1. Validation complexity
Partial overrides must still produce valid full configs.

Mitigation:
- use Pydantic typed models
- merge on top of a known-good default config
- reject incompatible combinations early

### 2. Vendor capability mismatches
Some vendor adapters may not support every field equally.

Mitigation:
- include vendor capability filtering in preview response
- expose unsupported fields as read-only or hide them
- keep vendor-specific warnings in response

### 3. UX complexity
Large policy forms can overwhelm users.

Mitigation:
- start with a limited editable field set
- use grouped sections
- provide sensible helper text and defaults
- keep Quick Apply for fast path

### 4. Drift between recommendation logic and apply logic
If preview defaults and apply defaults are generated differently, users may see inconsistent values.

Mitigation:
- use a single shared builder for preview and apply

## Recommended Backend Refactor

### Current anti-pattern
Defaults are embedded in procedural service branches:

- [`backend/app/services/optimization_service.py`](../backend/app/services/optimization_service.py:1171)
- [`backend/app/services/security_service.py`](../backend/app/services/security_service.py:654)
- [`backend/app/services/security_service.py`](../backend/app/services/security_service.py:738)
- [`backend/app/services/security_service.py`](../backend/app/services/security_service.py:776)

### Recommended structure

Add a new builder module, for example:

- `backend/app/services/policy_draft_service.py`

Suggested responsibilities:

- map vulnerability/recommendation type to policy action type
- build typed default config
- describe editable fields
- merge override payloads
- produce final [`PolicyAction`](../backend/app/models/base/api.py)

This prevents further duplication between Security and Optimization.

## Recommended API Changes

### Optimization

Enhance existing apply endpoint:
- [`/api/v1/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/apply`](../backend/app/api/v1/optimization.py:945)

New behavior:
- accept optional JSON body with `override_config` and `manual_analysis`

Add preview endpoint:
- `POST /api/v1/gateways/{gateway_id}/optimization/recommendations/{recommendation_id}/preview`

### Security

Enhance existing remediate endpoint:
- [`/api/v1/gateways/{gateway_id}/security/vulnerabilities/{vulnerability_id}/remediate`](../backend/app/api/v1/security.py:554)

New behavior:
- accept optional JSON body with `override_config` and `manual_analysis`

Add preview endpoint:
- `POST /api/v1/gateways/{gateway_id}/security/vulnerabilities/{vulnerability_id}/preview-remediation`

## Recommended Frontend Changes

### Optimization UI
Current entry point:
- [`frontend/src/pages/Optimization.tsx`](../frontend/src/pages/Optimization.tsx:148)

Recommended changes:
- replace simple confirm flow with:
  - Quick Apply
  - Review & Customize
- add policy draft modal
- submit override payload to apply endpoint
- show applied vs overridden values in action history

### Security UI
Current entry points:
- [`frontend/src/components/security/VulnerabilityCard.tsx`](../frontend/src/components/security/VulnerabilityCard.tsx:47)
- [`frontend/src/components/security/VulnerabilityRemediationPlan.tsx`](../frontend/src/components/security/VulnerabilityRemediationPlan.tsx:17)

Recommended changes:
- add remediation review modal
- surface generated defaults from preview endpoint
- allow field edits for supported vulnerability types
- show manual analysis notes in remediation history

## Proposed Rollout Plan

### Phase 1
- Add backend preview endpoints
- Add optional override payloads to apply/remediate
- Support editable fields for:
  - optimization caching
  - optimization rate limiting
  - security rate limiting
  - security TLS
- persist override metadata

### Phase 2
- Support authentication overrides
- add vendor-aware field restrictions
- expose change summary in UI history

### Phase 3
- derive smarter defaults from observed metrics and API metadata
- support reusable remediation profiles/templates
- support policy dry-run / compatibility validation

## Final Recommendation

This enhancement is worth implementing and fits the current architecture well.

### Why it is a good fit
- typed policy configs already exist
- adapters already consume vendor-neutral policy actions
- remediation history models already support metadata/audit extension
- frontend currently has clear apply entry points that can evolve into review workflows

### Recommended implementation direction
Adopt a **preview + override + apply** model:

1. generate a typed default policy draft
2. let the user manually override supported fields
3. validate and merge overrides server-side
4. apply the final policy through existing adapters
5. persist both defaults and overrides for auditability

This approach keeps automation intact while giving users the operational control needed for real gateway environments.

## Key Takeaways

- Current remediation values are hard-coded in service methods, not user-tunable.
- The existing typed config models are already strong enough to support safe overrides.
- The enhancement should be implemented above the adapter layer.
- A preview endpoint plus optional override payload is the cleanest product and API design.
- Manual analysis should be stored as structured audit metadata, not only free text.