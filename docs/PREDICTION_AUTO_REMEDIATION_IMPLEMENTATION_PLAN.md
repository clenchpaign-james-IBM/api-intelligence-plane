# Prediction Auto-Remediation Implementation Plan

**Feature**: Auto-remediation support for Prediction feature  
**Scope**: webMethods API Gateway only (no backend service remediation)  
**Date**: 2026-05-06  
**Status**: Implementation Plan

---

## Executive Summary

This document provides a detailed implementation plan for adding auto-remediation capabilities to the Prediction feature, following the same architecture patterns used in Security and Compliance features. The remediation scope is limited to **webMethods API Gateway configurations only** - no backend service modifications.

---

## 1. Architecture Overview

### 1.1 Design Pattern: Prediction-Centric Remediation

Following the vulnerability-centric pattern from Security (see [`docs/vulnerability-centric-remediation-architecture.md`](docs/vulnerability-centric-remediation-architecture.md)), we adopt a **prediction-centric** model where:

- Each [`Prediction`](backend/app/models/prediction.py:175) becomes the primary unit of remediation
- Remediation plans are persisted with the prediction document
- Remediation execution updates the same prediction record
- Verification outcomes are tracked on the prediction

### 1.2 Gateway-Only Remediation Scope

**IN SCOPE** (webMethods Gateway - API-Level Policies):
- Circuit breaker policies (per-API)
- Rate limiting policies (per-API)
- Request throttling (per-API)
- Timeout configurations (per-API)
- Caching policies (per-API)
- Request/response validation (per-API)
- Retry policies (per-API)
- Load balancing algorithms (per-API)

**OUT OF SCOPE**:
- Gateway instance scaling (deployment-level, not API-level)
- Backend service modifications
- Application code changes
- Database optimizations
- Backend service scaling
- Infrastructure provisioning
- Container orchestration

---

## 2. Data Model Changes

### 2.1 New Enums for Prediction Model

Add to [`backend/app/models/prediction.py`](backend/app/models/prediction.py):

```python
class RemediationType(str, Enum):
    """Approach used to remediate the predicted issue.
    
    Categorizes remediation methods for tracking and automation.
    Gateway-scoped only - no backend service modifications.
    """
    AUTOMATED = "automated"
    SEMI_AUTOMATED = "semi_automated"
    MANUAL = "manual"
    PREVENTIVE = "preventive"

class RemediationActionType(str, Enum):
    """Types of API-level gateway remediation actions."""
    CIRCUIT_BREAKER = "circuit_breaker"           # Enable circuit breaker for API
    RATE_LIMITING = "rate_limiting"               # Apply rate limits to API
    THROTTLING = "throttling"                     # Throttle API requests
    TIMEOUT_CONFIG = "timeout_config"             # Modify API timeout settings
    CACHE_CONFIG = "cache_config"                 # Modify API caching policies
    RETRY_POLICY = "retry_policy"                 # Configure retry behavior
    VALIDATION_POLICY = "validation_policy"       # Add request/response validation
    LOAD_BALANCING = "load_balancing"             # Adjust API load balancing

class RemediationStatus(str, Enum):
    """Status of a remediation action."""
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"
```

### 2.2 RemediationAction Model

```python
class RemediationAction(BaseModel):
    """Gateway-level remediation action for a prediction."""
    
    action: str = Field(..., description="Description of the remediation action")
    type: RemediationActionType = Field(..., description="Category of gateway action")
    status: RemediationStatus = Field(..., description="Current status")
    performed_at: Optional[datetime] = Field(None, description="When performed")
    performed_by: Optional[str] = Field(None, description="Who performed")
    gateway_policy_id: Optional[str] = Field(None, description="Gateway policy ID")
    configuration_before: Optional[Dict[str, Any]] = Field(None, description="Config before")
    configuration_after: Optional[Dict[str, Any]] = Field(None, description="Config after")
    effectiveness_score: Optional[float] = Field(None, ge=0, le=1, description="Effectiveness")
    error_message: Optional[str] = Field(None, description="Error details")
    rollback_available: bool = Field(True, description="Can rollback")
    rollback_performed_at: Optional[datetime] = Field(None, description="Rollback time")
```

### 2.3 Updates to Prediction Model

Add to [`Prediction`](backend/app/models/prediction.py:175) class:

```python
remediation_type: Optional[RemediationType] = Field(None, description="Remediation approach")
remediation_actions: Optional[List[RemediationAction]] = Field(None, description="Actions taken")
remediation_effectiveness: Optional[float] = Field(None, ge=0, le=1, description="Overall effectiveness")
recommended_remediation: Optional[Dict[str, Any]] = Field(None, description="Remediation plan")
recommended_priority: Optional[str] = Field(None, description="Priority level")
recommended_verification_steps: Optional[List[str]] = Field(None, description="Verification steps")
recommended_estimated_time_minutes: Optional[float] = Field(None, ge=0, description="Time estimate")
plan_generated_at: Optional[datetime] = Field(None, description="Plan generation time")
plan_source: Optional[str] = Field(None, description="Plan origin")
plan_version: Optional[str] = Field(None, description="Plan version")
plan_status: Optional[str] = Field(None, description="Plan status")
```

---

## 3. Service Layer Implementation

### 3.1 New PredictionService Methods

Add to [`backend/app/services/prediction_service.py`](backend/app/services/prediction_service.py):

```python
async def generate_remediation_plan(
    self,
    prediction_id: UUID,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """Generate AI-powered remediation plan for a prediction."""
    pass

async def remediate_prediction(
    self,
    prediction_id: UUID,
    remediation_strategy: Optional[str] = None,
    auto_approve: bool = False,
    override_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute automated remediation for a prediction."""
    pass

async def verify_remediation(
    self,
    prediction_id: UUID,
    verification_method: str = "automated"
) -> Dict[str, Any]:
    """Verify effectiveness of remediation actions."""
    pass

async def rollback_remediation(
    self,
    prediction_id: UUID,
    action_id: Optional[str] = None
) -> Dict[str, Any]:
    """Rollback remediation actions for a prediction."""
    pass
```

### 3.2 Gateway Adapter Integration

Extend [`backend/app/adapters/webmethods_adapter.py`](backend/app/adapters/webmethods_adapter.py):

```python
async def apply_prediction_remediation(
    self,
    gateway_id: UUID,
    api_id: UUID,
    remediation_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply prediction remediation to webMethods gateway."""
    pass
```

---

## 4. Agent Layer Implementation

### 4.1 New PredictionAgent Methods

Add to [`backend/app/agents/prediction_agent.py`](backend/app/agents/prediction_agent.py):

```python
async def generate_remediation_plan(
    self,
    prediction: Prediction,
    gateway_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate AI-powered remediation plan for a prediction."""
    pass
```

---

## 5. API Endpoints

### 5.1 New REST Endpoints

Add to [`backend/app/api/v1/predictions.py`](backend/app/api/v1/predictions.py):

```python
@router.post("/{prediction_id}/remediation-plan")
async def generate_remediation_plan(
    prediction_id: UUID,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """Generate remediation plan for a prediction."""
    pass
    
@router.post("/{prediction_id}/remediate")
async def remediate_prediction(
    prediction_id: UUID,
    request: RemediationRequest
) -> Dict[str, Any]:
    """Execute automated remediation for a prediction."""
    pass
    
@router.post("/{prediction_id}/verify-remediation")
async def verify_remediation(
    prediction_id: UUID,
    verification_method: str = "automated"
) -> Dict[str, Any]:
    """Verify effectiveness of remediation."""
    pass
    
@router.post("/{prediction_id}/rollback")
async def rollback_remediation(
    prediction_id: UUID,
    action_id: Optional[str] = None
) -> Dict[str, Any]:
    """Rollback remediation actions."""
    pass
```

---

## 6. Frontend Integration

### 6.1 New UI Components

- **PredictionRemediationPanel.tsx**: Display remediation plan and actions
- **RemediationActionCard.tsx**: Display individual remediation action

### 6.2 Service Layer

Add to [`frontend/src/services/prediction-service.ts`](frontend/src/services/prediction-service.ts):

```typescript
export const generateRemediationPlan = async (
  predictionId: string,
  forceRegenerate: boolean = false
): Promise<RemediationPlan> => {
  // Implementation
}

export const remediatePrediction = async (
  predictionId: string,
  request: RemediationRequest
): Promise<RemediationResponse> => {
  // Implementation
}
```

---

## 7. Gateway Policy Mappings

### 7.1 Prediction Type to Gateway Actions

| Prediction Type | Gateway Remediation Actions |
|----------------|----------------------------|
| **FAILURE** | Circuit breaker, Health checks, Traffic routing |
| **DEGRADATION** | Rate limiting, Throttling, Cache config |
| **CAPACITY** | Gateway scaling, Connection pool, Load balancing |
| **SECURITY** | Rate limiting, Request validation, IP filtering |

### 7.2 webMethods Policy Templates

Use existing policy converters from [`backend/app/utils/webmethods/policy_converter.py`](backend/app/utils/webmethods/policy_converter.py):

- `ThrottlePolicy` for rate limiting/throttling
- `ServiceResultCachePolicy` for caching
- `LogInvocationPolicy` for enhanced monitoring
- `ValidateAPISpecPolicy` for request validation

---

## 8. Implementation Phases

### Phase 1: Data Model (Week 1)
- Add enums to prediction.py
- Add RemediationAction model
- Update Prediction model with remediation fields
- Update OpenSearch index templates
- Migration script for existing predictions

### Phase 2: Service Layer (Week 2)
- Implement PredictionService remediation methods
- Extend webMethods adapter for prediction remediation
- Add policy mapping logic
- Implement rollback mechanism

### Phase 3: Agent Layer (Week 3)
- Implement PredictionAgent.generate_remediation_plan()
- Create LLM prompts for remediation planning
- Add verification logic
- Test with various prediction types

### Phase 4: API Layer (Week 4)
- Add REST endpoints
- Create request/response models
- Add validation and error handling
- Update API documentation

### Phase 5: Frontend (Week 5)
- Create remediation UI components
- Integrate with prediction service
- Add approval workflows
- Implement real-time status updates

### Phase 6: Testing and Documentation (Week 6)
- Integration tests
- E2E tests with webMethods gateway
- Performance testing
- User documentation
- Operator runbooks

---

## 9. Success Metrics

### 9.1 Functional Metrics
- **Remediation Success Rate**: Percentage of predictions successfully remediated
- **Prevention Rate**: Percentage of predicted failures actually prevented
- **Effectiveness Score**: Average effectiveness of remediation actions
- **Time to Remediate**: Average time from prediction to remediation

### 9.2 Operational Metrics
- **Auto-Remediation Rate**: Percentage of predictions remediated automatically
- **Rollback Rate**: Percentage of remediations requiring rollback
- **False Positive Rate**: Percentage of remediations that were unnecessary

---

## 10. Risk Mitigation

### 10.1 Risks
1. **Gateway Instability**: Automated changes could destabilize gateway
2. **Configuration Drift**: Multiple remediations could conflict
3. **False Positives**: Unnecessary remediations waste resources
4. **Rollback Failures**: Rollback might not fully restore state

### 10.2 Mitigations
1. **Approval Workflows**: Require approval for high-impact changes
2. **Configuration Snapshots**: Always capture before/after state
3. **Confidence Thresholds**: Only auto-remediate high-confidence predictions
4. **Gradual Rollout**: Start with manual-only, then semi-automated, then fully automated
5. **Circuit Breakers**: Disable auto-remediation if failure rate exceeds threshold
6. **Audit Trail**: Comprehensive logging of all remediation actions

---

## 11. Dependencies

### 11.1 Existing Components
- [`backend/app/models/prediction.py`](backend/app/models/prediction.py)
- [`backend/app/adapters/webmethods_adapter.py`](backend/app/adapters/webmethods_adapter.py)
- [`backend/app/utils/webmethods/policy_converter.py`](backend/app/utils/webmethods/policy_converter.py)
- [`docs/vulnerability-centric-remediation-architecture.md`](docs/vulnerability-centric-remediation-architecture.md)

### 11.2 New Components
- PredictionAgent remediation methods
- PredictionService remediation methods
- Gateway adapter remediation methods
- Frontend remediation UI components

---

## 12. Future Enhancements

### 12.1 Phase 2 Features (Post-MVP)
- **Multi-Gateway Coordination**: Coordinate remediation across multiple gateways
- **Cost Optimization**: Consider cost implications of scaling actions
- **ML-Based Effectiveness**: Learn from past remediations to improve recommendations
- **Automated Testing**: Test remediation in staging before production
- **Remediation Templates**: Pre-defined remediation playbooks

### 12.2 Advanced Features
- **Predictive Remediation**: Remediate before prediction threshold is reached
- **Cascading Remediation**: Handle dependencies between predictions
- **Self-Healing**: Automatically detect and remediate new prediction patterns
- **Remediation Marketplace**: Share remediation strategies across teams

---

## Appendix A: Example Remediation Flow

```
1. Prediction Created
   - api_id: 550e8400-e29b-41d4-a716-446655440001
   - prediction_type: DEGRADATION
   - severity: HIGH
   - contributing_factors: [increasing_error_rate, degrading_response_time]

2. Generate Remediation Plan (Automatic)
   - LLM analyzes prediction
   - Generates API-scoped actions:
     * Enable circuit breaker on API (effectiveness: 0.85)
     * Apply rate limiting to API (effectiveness: 0.70)
     * Enable response caching on API (effectiveness: 0.60)

3. Approval (Semi-Automated)
   - Operator reviews plan
   - Approves circuit breaker + rate limiting for this API
   - Defers caching for manual review

4. Execute Remediation
   - Apply circuit breaker policy to API 550e8400-e29b-41d4-a716-446655440001
   - Apply rate limiting policy to API 550e8400-e29b-41d4-a716-446655440001
   - Record actions with before/after API policy configs

5. Verify Effectiveness
   - Monitor API error rate for 30 minutes
   - Calculate effectiveness scores for this API
   - Update prediction status to RESOLVED

6. Outcome
   - Predicted degradation prevented for this API
   - Effectiveness: 0.78 (weighted average)
   - Prediction accuracy: 0.92
   - Other APIs on same gateway unaffected
```

---

**End of Implementation Plan**