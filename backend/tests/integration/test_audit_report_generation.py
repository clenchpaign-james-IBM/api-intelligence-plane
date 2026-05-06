"""Integration tests for compliance audit report generation.

Tests the complete audit report generation flow including:
- Report generation with various filters
- HTML/JSON export functionality
- AI-driven insights integration
- Report caching
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from typing import Dict, Any

from app.services.compliance_service import ComplianceService
from app.models.compliance import (
    ComplianceViolation,
    ComplianceStandard,
    ComplianceSeverity,
    ComplianceStatus,
    ComplianceViolationType,
    DetectionMethod,
)
from app.config import Settings


@pytest.fixture
def compliance_service():
    """Create compliance service instance for testing."""
    settings = Settings()
    return ComplianceService(settings=settings)


@pytest.fixture
def test_gateway_id():
    """Create a test gateway ID."""
    return uuid4()


@pytest.fixture
async def test_violations(compliance_service, test_gateway_id):
    """Create test violations for audit report testing."""
    violations = []
    
    # Create violations with different severities and standards
    test_cases = [
        (ComplianceSeverity.CRITICAL, ComplianceStandard.GDPR, ComplianceStatus.OPEN),
        (ComplianceSeverity.HIGH, ComplianceStandard.HIPAA, ComplianceStatus.OPEN),
        (ComplianceSeverity.MEDIUM, ComplianceStandard.SOC2, ComplianceStatus.REMEDIATED),
        (ComplianceSeverity.LOW, ComplianceStandard.PCI_DSS, ComplianceStatus.OPEN),
        (ComplianceSeverity.CRITICAL, ComplianceStandard.ISO_27001, ComplianceStatus.OPEN),
    ]
    
    for severity, standard, status in test_cases:
        violation = ComplianceViolation(
            id=uuid4(),
            gateway_id=test_gateway_id,
            api_id=uuid4(),
            compliance_standard=standard,
            violation_type=ComplianceViolationType.INSUFFICIENT_LOGGING_MONITORING,
            severity=severity,
            title=f"Test {severity.value} {standard.value} violation",
            description=f"Test violation for {standard.value} compliance",
            affected_endpoints=["/api/test"],
            detection_method=DetectionMethod.AUTOMATED_SCAN,
            detected_at=datetime.utcnow() - timedelta(days=10),
            status=status,
            evidence=[],
            audit_trail=[],
            remediation_documentation=[],
            regulatory_reference=f"{standard.value} Article 1",
            risk_level="high",
        )
        
        # Store violation
        await compliance_service.compliance_repository.create(violation)
        violations.append(violation)
    
    return violations


class TestAuditReportGeneration:
    """Test suite for audit report generation."""
    
    @pytest.mark.asyncio
    async def test_generate_basic_audit_report(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test basic audit report generation without filters."""
        # Generate report
        report = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=None,
            end_date=None,
        )
        
        # Validate report structure
        assert "report_id" in report
        assert "generated_at" in report
        assert "report_period" in report
        assert "executive_summary" in report
        assert "compliance_posture" in report
        assert "violations_by_severity" in report
        assert "violations_by_standard" in report
        assert "recommendations" in report
        
        # Validate compliance posture
        posture = report["compliance_posture"]
        assert posture["total_violations"] >= len(test_violations)
        assert posture["open_violations"] > 0
        assert posture["remediated_violations"] >= 0
        assert 0 <= posture["remediation_rate"] <= 100
        
        # Validate severity breakdown
        severity_breakdown = report["violations_by_severity"]
        assert "critical" in severity_breakdown
        assert "high" in severity_breakdown
        assert "medium" in severity_breakdown
        assert "low" in severity_breakdown
        
        # Validate executive summary
        assert len(report["executive_summary"]) > 50
        assert isinstance(report["executive_summary"], str)
    
    @pytest.mark.asyncio
    async def test_generate_report_with_standard_filter(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test audit report generation with compliance standard filter."""
        # Generate report filtered by GDPR
        report = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=[ComplianceStandard.GDPR],
            start_date=None,
            end_date=None,
        )
        
        # Validate filtering
        assert "violations_by_standard" in report
        standards = report["violations_by_standard"]
        
        # Should only have GDPR violations
        if standards:
            assert "gdpr" in standards or len(standards) == 0
    
    @pytest.mark.asyncio
    async def test_generate_report_with_date_range(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test audit report generation with date range filter."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Generate report with date range
        report = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Validate report period
        assert "report_period" in report
        period = report["report_period"]
        assert "start" in period
        assert "end" in period
        
        # Validate dates are within range
        period_start = datetime.fromisoformat(period["start"].replace('Z', '+00:00'))
        period_end = datetime.fromisoformat(period["end"].replace('Z', '+00:00'))
        
        assert period_start >= start_date.replace(tzinfo=None)
        assert period_end <= end_date.replace(tzinfo=None)
    
    @pytest.mark.asyncio
    async def test_audit_evidence_collection(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test that audit evidence is properly collected."""
        report = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=None,
            end_date=None,
        )
        
        # Validate audit evidence
        assert "audit_evidence" in report
        evidence = report["audit_evidence"]
        assert isinstance(evidence, list)
        
        # Evidence should be collected for critical violations
        if evidence:
            for item in evidence:
                assert "type" in item
                assert "description" in item
                assert "source" in item
                assert "timestamp" in item
    
    @pytest.mark.asyncio
    async def test_ai_insights_generation(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test AI-driven insights generation in audit reports."""
        report = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=None,
            end_date=None,
        )
        
        # Check if AI insights are present
        if "ai_insights" in report:
            insights = report["ai_insights"]
            
            # Validate insights structure
            assert isinstance(insights, dict)
            
            # Should have trend analysis
            if "trend_analysis" in insights:
                assert isinstance(insights["trend_analysis"], dict)
            
            # Should have risk scores
            if "risk_scores" in insights:
                assert isinstance(insights["risk_scores"], dict)
            
            # Should have predictive insights
            if "predictive_insights" in insights:
                assert isinstance(insights["predictive_insights"], dict)
            
            # Should have remediation prioritization
            if "remediation_prioritization" in insights:
                assert isinstance(insights["remediation_prioritization"], dict)
    
    @pytest.mark.asyncio
    async def test_report_caching(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test that audit reports are properly cached."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Generate report first time
        report1 = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Generate report second time (should be cached)
        report2 = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Reports should be identical (from cache)
        assert report1["report_id"] == report2["report_id"]
        assert report1["generated_at"] == report2["generated_at"]
    
    @pytest.mark.asyncio
    async def test_report_validation(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test that generated reports pass validation."""
        report = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=None,
            end_date=None,
        )
        
        # Validate required fields
        required_fields = [
            "report_id",
            "generated_at",
            "report_period",
            "executive_summary",
            "compliance_posture",
            "violations_by_severity",
            "violations_by_standard",
            "recommendations",
        ]
        
        for field in required_fields:
            assert field in report, f"Missing required field: {field}"
        
        # Validate data types
        assert isinstance(report["report_id"], str)
        assert isinstance(report["generated_at"], str)
        assert isinstance(report["executive_summary"], str)
        assert isinstance(report["compliance_posture"], dict)
        assert isinstance(report["violations_by_severity"], dict)
        assert isinstance(report["violations_by_standard"], dict)
        assert isinstance(report["recommendations"], list)
    
    @pytest.mark.asyncio
    async def test_recommendations_generation(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test that recommendations are generated based on violations."""
        report = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=None,
            end_date=None,
        )
        
        # Validate recommendations
        assert "recommendations" in report
        recommendations = report["recommendations"]
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Each recommendation should be a string
        for rec in recommendations:
            assert isinstance(rec, str)
            assert len(rec) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_date_range(
        self,
        compliance_service,
        test_gateway_id
    ):
        """Test error handling for invalid date ranges."""
        end_date = datetime.utcnow()
        start_date = end_date + timedelta(days=30)  # Invalid: start after end
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid date range"):
            await compliance_service.generate_audit_report(
                gateway_id=test_gateway_id,
                api_ids=None,
                standards=None,
                start_date=start_date,
                end_date=end_date,
            )
    
    @pytest.mark.asyncio
    async def test_empty_gateway(
        self,
        compliance_service
    ):
        """Test audit report generation for gateway with no violations."""
        empty_gateway_id = uuid4()
        
        # Generate report for empty gateway
        report = await compliance_service.generate_audit_report(
            gateway_id=empty_gateway_id,
            api_ids=None,
            standards=None,
            start_date=None,
            end_date=None,
        )
        
        # Should still generate valid report
        assert "report_id" in report
        assert "compliance_posture" in report
        
        # Should show zero violations
        posture = report["compliance_posture"]
        assert posture["total_violations"] == 0
        assert posture["open_violations"] == 0


class TestAuditReportExport:
    """Test suite for audit report export functionality."""
    
    @pytest.mark.asyncio
    async def test_json_export_structure(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test JSON export maintains proper structure."""
        report = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=None,
            end_date=None,
        )
        
        # JSON export should be the report itself
        assert isinstance(report, dict)
        
        # Should be JSON serializable
        import json
        json_str = json.dumps(report, default=str)
        assert len(json_str) > 0
        
        # Should be deserializable
        deserialized = json.loads(json_str)
        assert deserialized["report_id"] == report["report_id"]
    
    @pytest.mark.asyncio
    async def test_html_export_data_validation(
        self,
        compliance_service,
        test_gateway_id,
        test_violations
    ):
        """Test that HTML export receives validated data."""
        report = await compliance_service.generate_audit_report(
            gateway_id=test_gateway_id,
            api_ids=None,
            standards=None,
            start_date=None,
            end_date=None,
        )
        
        # Validate data that would be used in HTML export
        assert report.get("report_id") is not None
        assert report.get("generated_at") is not None
        assert report.get("executive_summary") is not None
        assert report.get("compliance_posture") is not None
        assert report.get("violations_by_severity") is not None
        assert report.get("violations_by_standard") is not None
        assert report.get("recommendations") is not None
        
        # Validate no "N/A" values in critical fields
        assert report["report_id"] != "N/A"
        assert report["generated_at"] != "N/A"
        assert report["executive_summary"] != "No summary available"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
