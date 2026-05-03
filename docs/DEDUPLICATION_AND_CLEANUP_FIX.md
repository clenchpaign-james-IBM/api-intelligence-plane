# Deduplication and Cleanup Fix for Background Jobs

## Problem Analysis

The background jobs for Security, Compliance, Prediction, and Optimization features are creating duplicate and stale items because:

### 1. **Security Service** (`security_service.py`)
- ❌ **No deduplication**: Creates new vulnerabilities on every scan without checking for existing ones
- ❌ **No cleanup**: Old/resolved vulnerabilities remain in the database indefinitely
- ❌ **No status updates**: Doesn't update status of previously detected vulnerabilities that are now fixed

### 2. **Compliance Service** (`compliance_service.py`)
- ✅ **Has deduplication**: `find_existing_violation()` method exists in repository
- ❌ **Not used**: Service doesn't call this method before creating violations
- ❌ **No cleanup**: Old violations remain even after APIs are fixed
- ❌ **No status updates**: Doesn't mark violations as resolved when fixed

### 3. **Prediction Service** (`prediction_service.py`)
- ✅ **Has deduplication**: `upsert_prediction()` method exists in repository
- ❌ **Not used**: Service calls `_store_predictions()` which uses `create()` instead of `upsert_prediction()`
- ✅ **Has cleanup**: `expire_old_predictions()` exists but needs verification
- ❌ **No status updates**: Doesn't update predictions when conditions change

### 4. **Optimization Service** (`optimization_service.py`)
- ✅ **Has deduplication**: `check_duplicate_recommendation()` method exists in repository
- ❌ **Not used**: Service doesn't check for duplicates before creating recommendations
- ✅ **Has cleanup**: `_expire_old_recommendations()` exists in scheduler job
- ❌ **No status updates**: Doesn't update recommendations when metrics improve

## Root Causes

1. **Services create items without checking for existing ones**
2. **Repository deduplication methods exist but are not called**
3. **No cleanup of resolved/fixed items**
4. **No status updates when conditions change**
5. **Scheduler jobs run without deduplication logic**

## Solution Strategy

### Phase 1: Add Deduplication to Services
- Security: Check for existing vulnerabilities before creating
- Compliance: Use `find_existing_violation()` before creating
- Prediction: Use `upsert_prediction()` instead of `create()`
- Optimization: Use `check_duplicate_recommendation()` before creating

### Phase 2: Add Cleanup Logic
- Security: Mark vulnerabilities as resolved when no longer detected
- Compliance: Mark violations as resolved when fixed
- Prediction: Expire predictions that didn't materialize
- Optimization: Expire recommendations that are no longer relevant

### Phase 3: Add Status Update Logic
- Update existing items instead of creating duplicates
- Mark items as resolved/expired when conditions change
- Track resolution timestamps

### Phase 4: Enhance Repository Methods
- Add missing deduplication methods where needed
- Add bulk cleanup methods for efficiency
- Add status transition methods

## Implementation Plan

### 1. Security Service Fixes
```python
# Before creating vulnerability, check if it exists
existing = await self.vulnerability_repository.find_existing_vulnerability(
    gateway_id=gateway_id,
    api_id=api_id,
    vulnerability_type=vuln.type,
    configuration_type=vuln.configuration_type
)

if existing:
    # Update existing vulnerability
    existing.severity = vuln.severity
    existing.detected_at = datetime.utcnow()
    existing.status = VulnerabilityStatus.OPEN
    self.vulnerability_repository.update(str(existing.id), existing.dict())
else:
    # Create new vulnerability
    self.vulnerability_repository.create(vuln)

# After scan, mark undetected vulnerabilities as resolved
await self.vulnerability_repository.mark_undetected_as_resolved(
    gateway_id=gateway_id,
    api_id=api_id,
    detected_vulnerability_ids=detected_ids,
    scan_time=datetime.utcnow()
)
```

### 2. Compliance Service Fixes
```python
# Use existing deduplication method
existing = await self.compliance_repository.find_existing_violation(
    gateway_id=gateway_id,
    api_id=api_id,
    violation_type=violation.violation_type,
    compliance_standard=violation.compliance_standard
)

if existing:
    # Update existing violation
    existing.severity = violation.severity
    existing.detected_at = datetime.utcnow()
    existing.status = ComplianceStatus.OPEN
    self.compliance_repository.update(str(existing.id), existing.dict())
else:
    # Create new violation
    self.compliance_repository.create(violation)

# Mark undetected violations as resolved
await self.compliance_repository.mark_undetected_as_resolved(
    gateway_id=gateway_id,
    api_id=api_id,
    detected_violation_ids=detected_ids,
    scan_time=datetime.utcnow()
)
```

### 3. Prediction Service Fixes
```python
# Use upsert instead of create
def _store_predictions(self, api_id: UUID, predictions: List[Prediction]) -> None:
    for prediction in predictions:
        # Use upsert_prediction instead of create
        self.prediction_repo.upsert_prediction(prediction)
```

### 4. Optimization Service Fixes
```python
# Check for duplicates before creating
existing = self.recommendation_repo.check_duplicate_recommendation(
    gateway_id=str(gateway_id),
    api_id=str(api_id),
    recommendation_type=rec.recommendation_type,
    status=RecommendationStatus.PENDING
)

if existing:
    # Update existing recommendation
    existing.estimated_impact = rec.estimated_impact
    existing.priority = rec.priority
    existing.updated_at = datetime.utcnow()
    self.recommendation_repo.update(str(existing.id), existing.dict())
else:
    # Create new recommendation
    self.recommendation_repo.create(rec)

# Mark outdated recommendations as expired
await self.recommendation_repo.mark_outdated_as_expired(
    gateway_id=gateway_id,
    api_id=api_id,
    current_recommendation_ids=current_ids
)
```

### 5. Repository Enhancements

#### VulnerabilityRepository
```python
async def find_existing_vulnerability(
    self, gateway_id: UUID, api_id: UUID, 
    vulnerability_type: str, configuration_type: str
) -> Optional[Vulnerability]:
    """Find existing vulnerability by unique key"""

async def mark_undetected_as_resolved(
    self, gateway_id: UUID, api_id: UUID,
    detected_vulnerability_ids: List[UUID], scan_time: datetime
) -> int:
    """Mark vulnerabilities not in detected list as resolved"""
```

#### ComplianceRepository (already has find_existing_violation)
```python
async def mark_undetected_as_resolved(
    self, gateway_id: UUID, api_id: UUID,
    detected_violation_ids: List[UUID], scan_time: datetime
) -> int:
    """Mark violations not in detected list as resolved"""
```

#### RecommendationRepository (already has check_duplicate_recommendation)
```python
async def mark_outdated_as_expired(
    self, gateway_id: UUID, api_id: UUID,
    current_recommendation_ids: List[UUID]
) -> int:
    """Mark recommendations not in current list as expired"""
```

## Benefits

1. **No Duplicates**: Each unique issue tracked by single record
2. **Accurate Status**: Items marked as resolved when fixed
3. **Clean Database**: Old items automatically cleaned up
4. **Better Performance**: Fewer records to query
5. **Accurate Metrics**: Counts reflect actual state
6. **Audit Trail**: Status transitions tracked with timestamps

## Testing Strategy

1. Run security scan twice - verify no duplicates
2. Fix vulnerability - verify marked as resolved
3. Run compliance scan twice - verify no duplicates
4. Fix violation - verify marked as resolved
5. Generate predictions twice - verify upsert works
6. Generate recommendations twice - verify no duplicates
7. Verify cleanup jobs remove old items

## Rollout Plan

1. Deploy repository enhancements
2. Deploy service fixes
3. Run manual cleanup script for existing duplicates
4. Monitor for 24 hours
5. Verify metrics accuracy