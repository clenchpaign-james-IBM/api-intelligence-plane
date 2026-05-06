"""Compliance Violation model for API Intelligence Plane.

Represents a compliance violation with affected API, compliance standard,
violation type, evidence, audit trail, and remediation documentation.

SCOPE: Gateway-level compliance monitoring for proxy APIs. Focuses on compliance
requirements that can be observed and verified at the API Gateway layer.

IMPORTANT: Compliance violations are distinct from security vulnerabilities.
Security focuses on threats and exploits; Compliance focuses on regulatory requirements.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ComplianceStandard(str, Enum):
    """Supported compliance and regulatory standards.
    
    Defines the major compliance frameworks that the API Intelligence Plane
    monitors for gateway-level compliance violations.
    
    Attributes:
        GDPR: General Data Protection Regulation (EU) - Data protection and privacy
        HIPAA: Health Insurance Portability and Accountability Act (US) - Healthcare data security
        SOC2: Service Organization Control 2 - Trust services criteria for service providers
        PCI_DSS: Payment Card Industry Data Security Standard - Payment card data protection
        ISO_27001: ISO/IEC 27001 - Information security management systems
    """

    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"


class ComplianceViolationType(str, Enum):
    """Type of compliance violation mapped to regulatory requirements.
    
    These are compliance-requirement-based, not security-control-based.
    Each violation type maps to specific clauses in compliance standards.
    """
    
    # GDPR-specific (Gateway-observable)
    GDPR_DATA_PROTECTION_BY_DESIGN = "gdpr_data_protection_by_design"  # Art. 25
    GDPR_SECURITY_OF_PROCESSING = "gdpr_security_of_processing"  # Art. 32
    GDPR_RECORDS_OF_PROCESSING = "gdpr_records_of_processing"  # Art. 30
    GDPR_DATA_BREACH_NOTIFICATION = "gdpr_data_breach_notification"  # Art. 33
    
    # HIPAA-specific (Gateway-observable)
    HIPAA_ACCESS_CONTROL = "hipaa_access_control"  # § 164.312(a)(1)
    HIPAA_AUDIT_CONTROLS = "hipaa_audit_controls"  # § 164.312(b)
    HIPAA_TRANSMISSION_SECURITY = "hipaa_transmission_security"  # § 164.312(e)(1)
    HIPAA_INTEGRITY_CONTROLS = "hipaa_integrity_controls"  # § 164.312(c)(1)
    
    # SOC2-specific (Gateway-observable)
    SOC2_SECURITY_AVAILABILITY = "soc2_security_availability"  # CC6.1
    SOC2_SYSTEM_MONITORING = "soc2_system_monitoring"  # CC7.2
    SOC2_LOGICAL_ACCESS = "soc2_logical_access"  # CC6.2
    SOC2_CONFIDENTIALITY = "soc2_confidentiality"  # C1.1
    
    # PCI-DSS-specific (Gateway-observable)
    PCI_DSS_NETWORK_SECURITY = "pci_dss_network_security"  # Req 1
    PCI_DSS_ENCRYPTION_IN_TRANSIT = "pci_dss_encryption_in_transit"  # Req 4
    PCI_DSS_ACCESS_CONTROL = "pci_dss_access_control"  # Req 7
    PCI_DSS_MONITORING_TESTING = "pci_dss_monitoring_testing"  # Req 10, 11
    
    # ISO 27001-specific (Gateway-observable)
    ISO_27001_ACCESS_CONTROL = "iso_27001_access_control"  # A.9
    ISO_27001_CRYPTOGRAPHY = "iso_27001_cryptography"  # A.10
    ISO_27001_OPERATIONS_SECURITY = "iso_27001_operations_security"  # A.12
    ISO_27001_COMMUNICATIONS_SECURITY = "iso_27001_communications_security"  # A.13
    
    # Cross-standard (applicable to multiple standards)
    INSUFFICIENT_LOGGING_MONITORING = "insufficient_logging_monitoring"
    INADEQUATE_ACCESS_CONTROLS = "inadequate_access_controls"
    MISSING_ENCRYPTION_CONTROLS = "missing_encryption_controls"
    INADEQUATE_AVAILABILITY_CONTROLS = "inadequate_availability_controls"


class ComplianceSeverity(str, Enum):
    """Severity level of compliance violation.
    
    Indicates the business and regulatory impact of a compliance violation.
    
    Attributes:
        CRITICAL: Immediate regulatory breach with potential for significant fines or legal action.
                 Requires immediate remediation (e.g., unencrypted PHI transmission).
        HIGH: Serious compliance gap that could lead to regulatory penalties if not addressed
              promptly (e.g., inadequate access controls for sensitive data).
        MEDIUM: Moderate compliance issue that should be addressed but poses lower immediate
                risk (e.g., incomplete audit logging).
        LOW: Minor compliance gap or best practice deviation with minimal regulatory impact
             (e.g., documentation gaps).
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceStatus(str, Enum):
    """Remediation status of compliance violation.
    
    Tracks the lifecycle of a compliance violation from detection to resolution.
    
    Attributes:
        OPEN: Newly detected violation awaiting review and remediation planning.
        IN_PROGRESS: Remediation actions are actively being implemented.
        REMEDIATED: Violation has been fully addressed and verified as resolved.
        ACCEPTED_RISK: Organization has formally accepted the risk after assessment
                      (requires documentation and approval).
        FALSE_POSITIVE: Violation was incorrectly identified and is not a real compliance issue.
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REMEDIATED = "remediated"
    ACCEPTED_RISK = "accepted_risk"
    FALSE_POSITIVE = "false_positive"


class DetectionMethod(str, Enum):
    """Method used to detect the compliance violation.
    
    Identifies the source and approach used to discover the compliance issue.
    
    Attributes:
        AUTOMATED_SCAN: Detected by automated compliance scanning tools or scheduled checks.
        MANUAL_AUDIT: Identified during manual compliance review by internal team.
        EXTERNAL_AUDIT: Found by external auditors or compliance assessors.
        AI_ANALYSIS: Discovered through AI-powered analysis of gateway configurations,
                    traffic patterns, and policy enforcement.
    """

    AUTOMATED_SCAN = "automated_scan"
    MANUAL_AUDIT = "manual_audit"
    EXTERNAL_AUDIT = "external_audit"
    AI_ANALYSIS = "ai_analysis"


class Evidence(BaseModel):
    """Evidence supporting the compliance violation.
    
    Captures specific proof and documentation that demonstrates the compliance
    violation exists, enabling audit trails and remediation verification.
    
    Attributes:
        type: Type of evidence collected (e.g., 'gateway_config', 'traffic_log',
              'policy', 'metrics_snapshot', 'configuration_file').
        description: Human-readable description explaining what the evidence shows
                    and why it's relevant to the violation.
        source: System or component that provided the evidence (e.g., 'gateway_api',
               'metrics_service', 'policy_engine', 'transactional_logs').
        timestamp: UTC timestamp when the evidence was collected.
        data: Structured evidence data containing the actual proof (e.g., configuration
             values, log entries, metric values). Optional for privacy-sensitive data.
    """

    type: str = Field(..., description="Type of evidence (e.g., 'gateway_config', 'traffic_log', 'policy')")
    description: str = Field(..., description="Description of the evidence")
    source: str = Field(..., description="Source of the evidence (e.g., 'gateway_api', 'metrics')")
    timestamp: datetime = Field(..., description="When evidence was collected")
    data: Optional[dict[str, Any]] = Field(None, description="Evidence data")


class AuditTrailEntry(BaseModel):
    """Audit trail entry for compliance violation.
    
    Records all actions taken on a compliance violation for regulatory audit
    requirements and accountability tracking.
    
    Attributes:
        timestamp: UTC timestamp when the action was performed.
        action: Description of the action taken (e.g., 'violation_detected',
               'remediation_started', 'status_changed', 'risk_accepted').
        performed_by: Identifier of the user, system, or agent that performed
                     the action (e.g., 'compliance_agent', 'admin@example.com').
        details: Additional context about the action, including reasons for
                decisions or specific changes made.
        status_before: Compliance status before this action was taken.
        status_after: Compliance status after this action was completed.
    """

    timestamp: datetime = Field(..., description="When action occurred")
    action: str = Field(..., description="Action taken")
    performed_by: str = Field(..., description="Who performed the action")
    details: Optional[str] = Field(None, description="Additional details")
    status_before: Optional[str] = Field(None, description="Status before action")
    status_after: Optional[str] = Field(None, description="Status after action")


class RemediationDocumentation(BaseModel):
    """Documentation of remediation actions (Gateway-level).
    
    Records the specific actions taken to address a compliance violation,
    including implementation details and verification results.
    
    Attributes:
        action: Description of the remediation action taken (e.g., 'Enabled TLS 1.3',
               'Configured audit logging', 'Applied access control policy').
        type: Category of remediation (e.g., 'gateway_policy', 'configuration',
             'policy_update', 'access_control').
        status: Current status of the remediation action (e.g., 'completed',
               'pending', 'failed', 'verified').
        performed_at: UTC timestamp when the remediation was performed.
        performed_by: Identifier of who performed the remediation (user or system).
        gateway_policy_id: ID of the gateway policy that was created or modified
                          to address the violation.
        verification_method: How the remediation was verified (e.g., 'automated_scan',
                           'manual_review', 'compliance_test').
        verification_status: Result of verification (e.g., 'passed', 'failed', 'pending').
        notes: Additional context, observations, or follow-up actions needed.
    """

    action: str = Field(..., description="Remediation action taken")
    type: str = Field(..., description="Type of remediation (e.g., 'gateway_policy', 'configuration')")
    status: str = Field(..., description="Status of remediation")
    performed_at: Optional[datetime] = Field(None, description="When performed")
    performed_by: Optional[str] = Field(None, description="Who performed")
    gateway_policy_id: Optional[str] = Field(None, description="Gateway policy ID if applied")
    verification_method: Optional[str] = Field(None, description="How verified")
    verification_status: Optional[str] = Field(None, description="Verification result")
    notes: Optional[str] = Field(None, description="Additional notes")


class ComplianceViolation(BaseModel):
    """Compliance Violation entity representing a Gateway-level regulatory compliance violation.

    SCOPE: Gateway-level compliance only. Monitors compliance requirements that can be
    observed and verified at the API Gateway layer.

    DISTINCTION: Compliance violations are regulatory requirement failures, distinct from
    security vulnerabilities which are threat-based.

    Attributes:
        id: Unique identifier (UUID v4)
        api_id: Affected API (Gateway proxy endpoint)
        compliance_standard: Compliance standard violated (GDPR, HIPAA, SOC2, PCI-DSS, ISO 27001)
        violation_type: Type of compliance violation (mapped to regulatory requirements)
        severity: Severity level
        title: Violation title (1-255 characters)
        description: Detailed description (1-5000 characters)
        affected_endpoints: Specific Gateway endpoints affected
        detection_method: How detected
        detected_at: Detection timestamp
        status: Remediation status
        evidence: Supporting evidence from Gateway
        audit_trail: Complete audit trail
        remediation_documentation: Gateway-level remediation actions and verification
        regulatory_reference: Reference to specific regulation clause
        risk_level: Business risk level
        remediation_deadline: Deadline for remediation
        remediated_at: Remediation timestamp
        last_audit_date: Last audit date
        next_audit_date: Next scheduled audit date
        metadata: Additional data
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the compliance violation (UUID v4 format). Auto-generated on creation."
    )
    gateway_id: UUID = Field(
        ...,
        description="UUID of the gateway where the API is deployed. Links violation to specific gateway infrastructure."
    )
    api_id: UUID = Field(
        ...,
        description="UUID of the affected API (Gateway proxy endpoint). Identifies which API has the compliance issue."
    )
    compliance_standard: ComplianceStandard = Field(
        ...,
        description="Compliance standard that was violated (GDPR, HIPAA, SOC2, PCI-DSS, ISO 27001). Determines applicable regulations."
    )
    violation_type: ComplianceViolationType = Field(
        ...,
        description="Specific type of compliance violation mapped to regulatory requirements. References exact regulation clauses."
    )
    severity: ComplianceSeverity = Field(
        ...,
        description="Severity level indicating business and regulatory impact (critical, high, medium, low). Guides prioritization."
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Brief, descriptive title of the violation (1-255 characters). Should clearly identify the issue."
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Detailed explanation of the violation (1-5000 characters). Includes what was found, why it's a violation, and potential impact."
    )
    affected_endpoints: Optional[list[str]] = Field(
        None,
        description="List of specific Gateway endpoints affected by this violation. Helps scope remediation efforts."
    )
    detection_method: DetectionMethod = Field(
        ...,
        description="Method used to detect the violation (automated_scan, manual_audit, external_audit, ai_analysis). Tracks detection source."
    )
    detected_at: datetime = Field(
        ...,
        description="UTC timestamp when the violation was first detected. Used for SLA tracking and audit trails."
    )
    status: ComplianceStatus = Field(
        default=ComplianceStatus.OPEN,
        description="Current remediation status (open, in_progress, remediated, accepted_risk, false_positive). Tracks lifecycle."
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="List of evidence items supporting the violation. Includes gateway configs, logs, and metrics that prove the issue."
    )
    audit_trail: list[AuditTrailEntry] = Field(
        default_factory=list,
        description="Complete chronological audit trail of all actions taken on this violation. Required for regulatory compliance."
    )
    remediation_documentation: Optional[list[RemediationDocumentation]] = Field(
        None,
        description="Documentation of gateway-level remediation actions and verification results. Proves compliance restoration."
    )
    regulatory_reference: Optional[str] = Field(
        None,
        description="Reference to specific regulation clause (e.g., 'HIPAA § 164.312(e)(1)'). Links to legal requirements."
    )
    risk_level: Optional[str] = Field(
        None,
        description="Business risk category (e.g., 'financial', 'reputational', 'operational'). Helps prioritize based on business impact."
    )
    remediation_deadline: Optional[datetime] = Field(
        None,
        description="UTC deadline for completing remediation. Based on severity and regulatory requirements. Must be after created_at."
    )
    remediated_at: Optional[datetime] = Field(
        None,
        description="UTC timestamp when remediation was completed. Required when status is 'remediated'. Used for SLA measurement."
    )
    last_audit_date: Optional[datetime] = Field(
        None,
        description="UTC date of the most recent compliance audit that reviewed this violation. Tracks audit frequency."
    )
    next_audit_date: Optional[datetime] = Field(
        None,
        description="UTC date when the next compliance audit is scheduled. Ensures ongoing monitoring."
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Additional flexible metadata for vendor-specific data, custom fields, or integration information."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the violation record was created. Auto-generated. Used for aging and reporting."
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the last update to this violation. Auto-updated on changes. Tracks modification history."
    )

    @field_validator("remediated_at")
    @classmethod
    def validate_remediated_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate if status is remediated, remediated_at must be set."""
        if "status" in info.data:
            status = info.data["status"]
            if status == ComplianceStatus.REMEDIATED and v is None:
                raise ValueError("remediated_at must be set when status is remediated")
        return v

    @field_validator("remediation_deadline")
    @classmethod
    def validate_remediation_deadline(
        cls, v: Optional[datetime], info
    ) -> Optional[datetime]:
        """Validate remediation deadline is in the future."""
        if v is not None and "created_at" in info.data:
            created_at = info.data["created_at"]
            if v < created_at:
                raise ValueError("remediation_deadline must be after created_at")
        return v
    
    def to_llm_dict(self) -> dict[str, Any]:
        """
        Generate LLM-optimized dictionary representation.
        
        Trims large/redundant fields to reduce token count while maintaining
        essential context for natural language response generation.
        
        Estimated reduction: 50-70% for typical compliance entities.
        
        Returns:
            Trimmed dictionary suitable for LLM context
        """
        result = {
            "id": str(self.id),
            "gateway_id": str(self.gateway_id),
            "api_id": str(self.api_id),
            "compliance_standard": self.compliance_standard.value,
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "affected_endpoints": self.affected_endpoints[:3] if self.affected_endpoints else None,
            "detection_method": self.detection_method.value,
            "detected_at": self.detected_at.isoformat(),
            "status": self.status.value,
            "regulatory_reference": self.regulatory_reference,
            "risk_level": self.risk_level,
            "remediation_deadline": self.remediation_deadline.isoformat() if self.remediation_deadline else None,
            "remediated_at": self.remediated_at.isoformat() if self.remediated_at else None,
        }
        
        # Trim evidence - keep count and types
        if self.evidence:
            result["evidence_count"] = len(self.evidence)
            result["evidence_types"] = list(set(e.type for e in self.evidence))
        
        # Trim audit_trail - keep count and latest entry
        if self.audit_trail:
            result["audit_trail_count"] = len(self.audit_trail)
            latest = self.audit_trail[-1]
            result["latest_audit_entry"] = {
                "timestamp": latest.timestamp.isoformat(),
                "action": latest.action,
                "performed_by": latest.performed_by,
            }
        
        # Trim remediation_documentation - keep count and latest action status
        if self.remediation_documentation:
            result["remediation_actions_count"] = len(self.remediation_documentation)
            latest = self.remediation_documentation[-1]
            result["latest_remediation_status"] = latest.status
        
        # Drop: metadata, full evidence data, full audit_trail, full remediation_documentation
        
        return result

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440005",
                "gateway_id": "550e8400-e29b-41d4-a716-446655440000",
                "api_id": "550e8400-e29b-41d4-a716-446655440001",
                "compliance_standard": "hipaa",
                "violation_type": "hipaa_transmission_security",
                "severity": "critical",
                "title": "HIPAA Transmission Security Violation",
                "description": "Gateway API endpoint handling PHI does not enforce TLS 1.3 encryption as required by HIPAA § 164.312(e)(1) for transmission security.",
                "affected_endpoints": ["/api/v1/patients", "/api/v1/medical-records"],
                "detection_method": "ai_analysis",
                "detected_at": "2026-03-09T10:00:00Z",
                "status": "open",
                "evidence": [
                    {
                        "type": "gateway_config",
                        "description": "Gateway TLS policy analysis shows TLS 1.2 allowed",
                        "source": "gateway_api",
                        "timestamp": "2026-03-09T10:00:00Z",
                        "data": {"tls_version": "1.2", "min_tls_version": "1.0"}
                    }
                ],
                "audit_trail": [
                    {
                        "timestamp": "2026-03-09T10:00:00Z",
                        "action": "violation_detected",
                        "performed_by": "compliance_agent",
                        "details": "AI-driven compliance scan detected HIPAA transmission security violation",
                    }
                ],
                "regulatory_reference": "HIPAA Security Rule § 164.312(e)(1) - Transmission Security",
                "risk_level": "financial",
                "remediation_deadline": "2026-03-16T00:00:00Z",
            }
        }


# Made with Bob


# Audit Report Validation Schemas
class AuditReportSummary(BaseModel):
    """Summary statistics for audit report."""
    
    total_violations: int = Field(..., ge=0, description="Total violations")
    open_violations: int = Field(..., ge=0, description="Open violations")
    remediated_violations: int = Field(..., ge=0, description="Remediated violations")
    remediation_rate: float = Field(..., ge=0.0, le=100.0, description="Remediation rate percentage")


class AuditReportPeriod(BaseModel):
    """Time period covered by audit report."""
    
    start: str = Field(..., description="Start date (ISO 8601)")
    end: str = Field(..., description="End date (ISO 8601)")


class AuditReportSchema(BaseModel):
    """Pydantic schema for validating audit reports.
    
    Ensures all audit reports have consistent structure and valid data
    before being returned to clients or exported.
    """
    
    report_id: str = Field(..., description="Unique report identifier")
    generated_at: str = Field(..., description="Report generation timestamp (ISO 8601)")
    report_period: AuditReportPeriod = Field(..., description="Report time period")
    executive_summary: str = Field(..., min_length=1, description="AI-generated executive summary")
    
    # Compliance posture (using summary structure)
    compliance_posture: AuditReportSummary = Field(..., description="Overall compliance posture")
    
    # Violations by severity
    violations_by_severity: dict[str, int] = Field(
        default_factory=dict,
        description="Violations grouped by severity (critical, high, medium, low)"
    )
    
    # Violations by standard
    violations_by_standard: dict[str, int] = Field(
        default_factory=dict,
        description="Violations grouped by compliance standard"
    )
    
    # Remediation status breakdown
    remediation_status: dict[str, int] = Field(
        default_factory=dict,
        description="Violations grouped by remediation status"
    )
    
    # Violations needing audit attention
    violations_needing_audit: list[dict] = Field(
        default_factory=list,
        description="Violations requiring audit attention"
    )
    
    # Audit evidence
    audit_evidence: list[dict] = Field(
        default_factory=list,
        description="Collected audit evidence"
    )
    
    # Recommendations
    recommendations: list[str] = Field(
        default_factory=list,
        description="Audit recommendations"
    )
    
    # Detailed violations (optional for full reports)
    detailed_violations: list[dict] = Field(
        default_factory=list,
        description="Detailed violation information"
    )
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "report_id": "550e8400-e29b-41d4-a716-446655440000",
                "generated_at": "2026-05-06T10:30:00Z",
                "report_period": {
                    "start": "2026-02-06T00:00:00Z",
                    "end": "2026-05-06T23:59:59Z"
                },
                "executive_summary": "Overall compliance posture shows...",
                "compliance_posture": {
                    "total_violations": 45,
                    "open_violations": 12,
                    "remediated_violations": 33,
                    "remediation_rate": 73.3
                },
                "violations_by_severity": {
                    "critical": 3,
                    "high": 9,
                    "medium": 18,
                    "low": 15
                },
                "violations_by_standard": {
                    "gdpr": 15,
                    "hipaa": 10,
                    "soc2": 12,
                    "pci_dss": 5,
                    "iso_27001": 3
                },
                "remediation_status": {
                    "open": 12,
                    "in_progress": 8,
                    "remediated": 25
                },
                "violations_needing_audit": [],
                "audit_evidence": [],
                "recommendations": [
                    "Address critical violations within 30 days",
                    "Implement automated compliance monitoring"
                ],
                "detailed_violations": []
            }
        }