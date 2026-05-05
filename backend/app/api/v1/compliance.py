"""Compliance API endpoints for API Intelligence Plane.

Provides REST API for compliance monitoring, violation management, and audit reporting.
Focuses on scheduled audit preparation and regulatory reporting (distinct from immediate security threat response).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_compliance_service
from app.models.compliance import (
    ComplianceViolation,
    ComplianceStandard,
    ComplianceStatus,
    ComplianceSeverity,
)
from app.services.compliance_service import ComplianceService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["compliance"])


# Request/Response Models
class ComplianceScanRequest(BaseModel):
    """Request model for compliance scan."""

    gateway_id: UUID = Field(..., description="Gateway containing the API")
    api_id: UUID = Field(..., description="API to scan")
    standards: Optional[List[ComplianceStandard]] = Field(
        None, description="Specific standards to check (default: all 5)"
    )


class ComplianceScanResponse(BaseModel):
    """Response model for compliance scan."""

    scan_id: str = Field(..., description="Scan identifier")
    api_id: str = Field(..., description="API identifier")
    api_name: str = Field(..., description="API name")
    scan_completed_at: str = Field(..., description="Scan completion timestamp")
    violations_found: int = Field(..., description="Number of violations")
    severity_breakdown: dict = Field(..., description="Violations by severity")
    standard_breakdown: dict = Field(..., description="Violations by standard")
    violations: List[dict] = Field(..., description="List of violations")
    audit_evidence: List[dict] = Field(..., description="Audit evidence collected")


class AuditReportRequest(BaseModel):
    """Request model for audit report generation."""

    api_ids: Optional[List[UUID]] = Field(None, description="Optional API filters (multiple)")
    standards: Optional[List[ComplianceStandard]] = Field(
        None, description="Optional standard filters (multiple)"
    )
    start_date: Optional[datetime] = Field(
        None, description="Report start date (default: 90 days ago)"
    )
    end_date: Optional[datetime] = Field(
        None, description="Report end date (default: now)"
    )


class AuditReportResponse(BaseModel):
    """Response model for audit report."""

    report_id: str = Field(..., description="Report identifier")
    generated_at: str = Field(..., description="Report generation timestamp")
    report_period: dict = Field(..., description="Report time period")
    executive_summary: str = Field(..., description="AI-generated executive summary")
    compliance_posture: dict = Field(..., description="Overall compliance posture")
    violations_by_standard: dict = Field(..., description="Violations by standard")
    violations_by_severity: dict = Field(..., description="Violations by severity")
    remediation_status: dict = Field(..., description="Remediation status breakdown")
    violations_needing_audit: List[dict] = Field(
        ..., description="Violations needing audit attention"
    )
    audit_evidence: List[dict] = Field(..., description="Collected audit evidence")
    recommendations: List[str] = Field(..., description="Audit recommendations")


class CompliancePostureResponse(BaseModel):
    """Response model for compliance posture."""

    total_violations: int = Field(..., description="Total violations")
    by_severity: dict = Field(..., description="Breakdown by severity")
    by_status: dict = Field(..., description="Breakdown by status")
    by_standard: dict = Field(..., description="Breakdown by standard")
    remediation_rate: float = Field(..., description="Remediation rate percentage")
    compliance_score: float = Field(
        ..., description="Overall compliance score (0-100, higher is better)"
    )
    last_scan: Optional[str] = Field(None, description="Last scan timestamp")
    next_audit_date: str = Field(..., description="Next recommended audit date")


class ComplianceViolationListResponse(BaseModel):
    """Response model for listing compliance violations."""
    
    items: List[ComplianceViolation]
    total: int
    page: int
    page_size: int


# API Endpoints
@router.post(
    "/gateways/{gateway_id}/compliance/scan",
    response_model=ComplianceScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan API for compliance violations",
    description="Perform compliance scan on a specific API within a gateway using AI-driven analysis for 5 regulatory standards",
)
async def scan_gateway_api_compliance(
    gateway_id: UUID,
    request: ComplianceScanRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> ComplianceScanResponse:
    """Scan API for compliance violations across regulatory standards within a gateway.

    Checks compliance with:
    - GDPR (General Data Protection Regulation)
    - HIPAA (Health Insurance Portability and Accountability Act)
    - SOC2 (Service Organization Control 2)
    - PCI-DSS (Payment Card Industry Data Security Standard)
    - ISO 27001 (Information Security Management)

    Args:
        gateway_id: Gateway UUID (required, must match request.gateway_id)
        request: Scan request with gateway_id, API ID and optional standards filter
        compliance_service: Compliance service dependency

    Returns:
        Scan results with violations and audit evidence

    Raises:
        HTTPException: If gateway or API not found or scan fails
    """
    try:
        # Verify gateway_id matches path parameter
        if str(request.gateway_id) != str(gateway_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gateway ID in request body must match path parameter",
            )
        
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # Verify API belongs to gateway
        from app.db.repositories.api_repository import APIRepository
        api_repo = APIRepository()
        api = api_repo.get(str(request.api_id))
        
        if not api:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API {request.api_id} not found",
            )
        
        if str(api.gateway_id) != str(gateway_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API {request.api_id} not found in gateway {gateway_id}",
            )
        
        logger.info(f"Scanning API {request.api_id} in gateway {gateway_id} for compliance violations")

        result = await compliance_service.scan_api_compliance(
            api_id=request.api_id,
            gateway_id=gateway_id,
            standards=request.standards,
        )

        return ComplianceScanResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Compliance scan failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance scan failed: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/compliance/violations",
    response_model=List[ComplianceViolation],
    status_code=status.HTTP_200_OK,
    summary="Get compliance violations for a gateway",
    description="Retrieve compliance violations for APIs within a gateway with optional filters",
)
async def get_gateway_violations(
    gateway_id: UUID,
    api_id: Optional[UUID] = Query(None, description="Filter by API ID within gateway"),
    standard: Optional[ComplianceStandard] = Query(
        None, description="Filter by compliance standard"
    ),
    severity: Optional[ComplianceSeverity] = Query(
        None, description="Filter by severity"
    ),
    status_filter: Optional[ComplianceStatus] = Query(
        None, alias="status", description="Filter by status"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> List[ComplianceViolation]:
    """Get compliance violations for APIs within a gateway with optional filters.

    Args:
        gateway_id: Gateway UUID (required)
        api_id: Optional API filter within gateway
        standard: Optional compliance standard filter
        severity: Optional severity filter
        status_filter: Optional status filter
        limit: Maximum results
        compliance_service: Compliance service dependency

    Returns:
        List of compliance violations

    Raises:
        HTTPException: If gateway not found or query fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # If api_id is provided, verify it belongs to the gateway
        if api_id:
            from app.db.repositories.api_repository import APIRepository
            api_repo = APIRepository()
            api = api_repo.get(str(api_id))
            if not api or str(api.gateway_id) != str(gateway_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"API {api_id} not found in gateway {gateway_id}",
                )
        
        from app.db.repositories.compliance_repository import ComplianceRepository

        compliance_repo = ComplianceRepository()

        # Build filters - all methods return List[ComplianceViolation]
        violations: List[ComplianceViolation] = []
        
        if api_id:
            violations = await compliance_repo.find_by_api_id(api_id)
        elif standard:
            violations = await compliance_repo.find_by_standard(standard)
        elif severity:
            violations = await compliance_repo.find_by_severity(severity)
        elif status_filter:
            # Get open violations and filter by status
            open_violations = await compliance_repo.find_open_violations(limit=limit)
            violations = [v for v in open_violations if v.status == status_filter]
        else:
            # Get all open violations by default
            violations = await compliance_repo.find_open_violations(limit=limit)
        
        # Filter violations to only include those from APIs in this gateway
        if not api_id:
            from app.db.repositories.api_repository import APIRepository
            api_repo = APIRepository()
            gateway_apis, _ = api_repo.find_by_gateway(gateway_id=gateway_id, size=10000)
            gateway_api_ids = {str(api.id) for api in gateway_apis}
            
            violations = [
                v for v in violations
                if str(v.api_id) in gateway_api_ids
            ]

        # Apply limit if needed
        if len(violations) > limit:
            violations = violations[:limit]

        return violations

    except Exception as e:
        logger.error(f"Failed to get violations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get violations: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/compliance/posture",
    response_model=CompliancePostureResponse,
    status_code=status.HTTP_200_OK,
    summary="Get compliance posture for a gateway",
    description="Get compliance posture metrics and scores for a gateway's APIs",
)
async def get_gateway_compliance_posture(
    gateway_id: UUID,
    api_id: Optional[UUID] = Query(None, description="Optional API filter within gateway"),
    standard: Optional[ComplianceStandard] = Query(
        None, description="Optional standard filter"
    ),
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> CompliancePostureResponse:
    """Get compliance posture metrics for a gateway's APIs.

    Args:
        gateway_id: Gateway UUID (required)
        api_id: Optional API filter within gateway
        standard: Optional compliance standard filter
        compliance_service: Compliance service dependency

    Returns:
        Compliance posture metrics and scores

    Raises:
        HTTPException: If gateway not found or query fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # If api_id is provided, verify it belongs to the gateway
        if api_id:
            from app.db.repositories.api_repository import APIRepository
            api_repo = APIRepository()
            api = api_repo.get(str(api_id))
            if not api or str(api.gateway_id) != str(gateway_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"API {api_id} not found in gateway {gateway_id}",
                )
        
        logger.info(f"Getting compliance posture for gateway {gateway_id}")

        posture = await compliance_service.get_compliance_posture(
            api_id=api_id,
            standard=standard,
        )

        return CompliancePostureResponse(**posture)

    except Exception as e:
        logger.error(f"Failed to get compliance posture: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get compliance posture: {str(e)}",
        )


@router.post(
    "/gateways/{gateway_id}/compliance/reports/audit",
    response_model=AuditReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate audit report for a gateway",
    description="Generate comprehensive audit report for a gateway's APIs with evidence and recommendations",
)
async def generate_gateway_audit_report(
    gateway_id: UUID,
    request: AuditReportRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> AuditReportResponse:
    """Generate comprehensive audit report for a gateway's APIs.

    Includes:
    - AI-generated executive summary
    - Compliance posture analysis
    - Violations breakdown by standard and severity
    - Remediation status tracking
    - Violations needing audit attention
    - Collected audit evidence
    - Actionable recommendations

    Args:
        gateway_id: Gateway UUID (required)
        request: Audit report request with optional filters
        compliance_service: Compliance service dependency

    Returns:
        Comprehensive audit report

    Raises:
        HTTPException: If gateway not found or report generation fails
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        # If api_ids are provided, verify they belong to the gateway
        if request.api_ids:
            from app.db.repositories.api_repository import APIRepository
            api_repo = APIRepository()
            for api_id in request.api_ids:
                api = api_repo.get(str(api_id))
                if not api or str(api.gateway_id) != str(gateway_id):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"API {api_id} not found in gateway {gateway_id}",
                    )
        
        logger.info(f"Generating audit report for gateway {gateway_id}")

        report = await compliance_service.generate_audit_report(
            gateway_id=gateway_id,
            api_ids=request.api_ids,
            standards=request.standards,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        return AuditReportResponse(**report)

    except Exception as e:
        logger.error(f"Failed to generate audit report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate audit report: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/compliance/reports/audit/{report_id}/export",
    status_code=status.HTTP_200_OK,
    summary="Export audit report",
    description="Export audit report in specified format (JSON, HTML, or PDF)",
)
async def export_gateway_audit_report(
    gateway_id: UUID,
    report_id: str,
    format: str = Query("json", regex="^(json|html|pdf)$", description="Export format"),
    compliance_service: ComplianceService = Depends(get_compliance_service),
):
    """Export audit report in specified format.
    
    Args:
        gateway_id: Gateway UUID (required)
        report_id: Report identifier
        format: Export format (json, html, pdf)
        compliance_service: Compliance service dependency
        
    Returns:
        Report in requested format
        
    Raises:
        HTTPException: If gateway not found or export fails
    """
    try:
        from fastapi.responses import JSONResponse, HTMLResponse, Response
        
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        logger.info(f"Exporting audit report {report_id} for gateway {gateway_id} as {format}")
        
        # For now, we'll generate a new report since we don't store reports
        # In production, you'd retrieve the stored report by report_id
        report = await compliance_service.generate_audit_report(
            gateway_id=gateway_id,
            api_ids=None,
            standards=None,
            start_date=None,
            end_date=None,
        )
        
        if format == "html":
            # Generate HTML report BEFORE converting to JSON-serializable
            # (so we can access the original data structure)
            try:
                # Debug: Log full report
                logger.info(f"=== FULL REPORT ===")
                logger.info(f"Report type: {type(report)}")
                logger.info(f"Report keys: {list(report.keys())}")
                for key, value in report.items():
                    logger.info(f"  {key}: {type(value)} = {value if not isinstance(value, (list, dict)) else f'<{type(value).__name__} with {len(value)} items>'}")
                
                # Extract values with proper defaults and explicit logging
                compliance_posture = report.get('compliance_posture', {})
                logger.info(f"compliance_posture type: {type(compliance_posture)}, value: {compliance_posture}")
                
                violations_by_severity = report.get('violations_by_severity', {})
                logger.info(f"violations_by_severity: {violations_by_severity}")
                
                violations_by_standard = report.get('violations_by_standard', {})
                logger.info(f"violations_by_standard: {violations_by_standard}")
                
                report_period = report.get('report_period', {})
                logger.info(f"report_period: {report_period}")
                
                report_id_str = str(report.get('report_id', 'N/A'))
                logger.info(f"report_id_str: {report_id_str}")
                
                generated_at_str = str(report.get('generated_at', 'N/A'))
                logger.info(f"generated_at_str: {generated_at_str}")
                
                executive_summary = report.get('executive_summary', 'No summary available')
                logger.info(f"executive_summary: {executive_summary}")
                
                # Build standards table rows
                standards_rows = ""
                if violations_by_standard:
                    for std, count in violations_by_standard.items():
                        standards_rows += f"<tr><td>{std.upper()}</td><td>{count}</td></tr>"
                else:
                    standards_rows = "<tr><td colspan='2'>No violations by standard</td></tr>"
                
                # Build recommendations list
                recommendations_items = ""
                recommendations = report.get('recommendations', [])
                if recommendations:
                    for rec in recommendations:
                        recommendations_items += f"<li>{rec}</li>"
                else:
                    recommendations_items = "<li>No recommendations available</li>"
                
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Compliance Audit Report - {report_id_str}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .critical {{ color: #dc2626; font-weight: bold; }}
        .high {{ color: #ea580c; font-weight: bold; }}
        .medium {{ color: #ca8a04; font-weight: bold; }}
        .low {{ color: #2563eb; font-weight: bold; }}
        .summary {{ background-color: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Compliance Audit Report</h1>
    <p><strong>Report ID:</strong> {report_id_str}</p>
    <p><strong>Generated:</strong> {generated_at_str}</p>
    <p><strong>Period:</strong> {report_period.get('start', 'N/A')} to {report_period.get('end', 'N/A')}</p>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        <p>{executive_summary}</p>
    </div>
    
    <h2>Compliance Summary</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Total Violations</td>
            <td>{compliance_posture.get('total_violations', 0)}</td>
        </tr>
        <tr>
            <td>Open Violations</td>
            <td>{compliance_posture.get('open_violations', 0)}</td>
        </tr>
        <tr>
            <td>Remediated Violations</td>
            <td>{compliance_posture.get('remediated_violations', 0)}</td>
        </tr>
        <tr>
            <td>Remediation Rate</td>
            <td>{compliance_posture.get('remediation_rate', 0)}%</td>
        </tr>
    </table>
    
    <h2>Violations by Severity</h2>
    <table>
        <tr>
            <th>Severity</th>
            <th>Count</th>
        </tr>
        <tr class="critical">
            <td>Critical</td>
            <td>{violations_by_severity.get('critical', 0)}</td>
        </tr>
        <tr class="high">
            <td>High</td>
            <td>{violations_by_severity.get('high', 0)}</td>
        </tr>
        <tr class="medium">
            <td>Medium</td>
            <td>{violations_by_severity.get('medium', 0)}</td>
        </tr>
        <tr class="low">
            <td>Low</td>
            <td>{violations_by_severity.get('low', 0)}</td>
        </tr>
    </table>
    
    <h2>Violations by Standard</h2>
    <table>
        <tr>
            <th>Standard</th>
            <th>Count</th>
        </tr>
        {standards_rows}
    </table>
    
    <h2>Recommendations</h2>
    <ol>
        {recommendations_items}
    </ol>
</body>
</html>"""
                return HTMLResponse(content=html_content)
            except Exception as html_error:
                logger.error(f"Failed to generate HTML: {str(html_error)}")
                raise
        
        # Convert UUIDs and datetimes to strings for JSON serialization
        from datetime import datetime
        
        def convert_to_json_serializable(obj):
            """Recursively convert UUID and datetime objects to strings."""
            if isinstance(obj, UUID):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_to_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_json_serializable(item) for item in obj]
            return obj
        
        report_dict: dict = convert_to_json_serializable(report)  # type: ignore
        report = report_dict
        
        if format == "json":
            return JSONResponse(content=report)
        
        elif format == "pdf":
            # For PDF, return HTML with a note that PDF generation requires additional setup
            # In production, you'd use a library like WeasyPrint or ReportLab
            return JSONResponse(
                status_code=501,
                content={
                    "error": "PDF export not yet implemented",
                    "message": "PDF generation requires additional dependencies. Use HTML or JSON export instead.",
                    "alternatives": ["json", "html"]
                }
            )
    
    except Exception as e:
        logger.error(f"Failed to export audit report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export audit report: {str(e)}",
        )


@router.get(
    "/gateways/{gateway_id}/compliance/violations/{violation_id}",
    response_model=ComplianceViolation,
    status_code=status.HTTP_200_OK,
    summary="Get violation by ID",
    description="Retrieve a specific compliance violation within a gateway by ID",
)
async def get_gateway_violation(
    gateway_id: UUID,
    violation_id: UUID,
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> ComplianceViolation:
    """Get a specific compliance violation by ID within a gateway.

    Args:
        gateway_id: Gateway UUID (required)
        violation_id: Violation identifier
        compliance_service: Compliance service dependency

    Returns:
        Compliance violation details

    Raises:
        HTTPException: If gateway or violation not found
    """
    try:
        # Verify gateway exists
        from app.db.repositories.gateway_repository import GatewayRepository
        gateway_repo = GatewayRepository()
        gateway = gateway_repo.get(str(gateway_id))
        
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gateway {gateway_id} not found",
            )
        
        from app.db.repositories.compliance_repository import ComplianceRepository

        compliance_repo = ComplianceRepository()
        violation = compliance_repo.get(str(violation_id))

        if not violation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Violation not found: {violation_id}",
            )
        
        # Verify violation's API belongs to the gateway
        from app.db.repositories.api_repository import APIRepository
        api_repo = APIRepository()
        api = api_repo.get(str(violation.api_id))
        if not api or str(api.gateway_id) != str(gateway_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Violation {violation_id} not found in gateway {gateway_id}",
            )

        return violation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get violation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get violation: {str(e)}",
        )

@router.get(
    "/compliance/violations/search",
    response_model=ComplianceViolationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search compliance violations with multiple filters",
    description="Search compliance violations across all gateways with flexible multi-criteria filtering",
)
async def search_compliance_violations(
    standard: Optional[ComplianceStandard] = Query(None, description="Filter by compliance standard"),
    violation_type: Optional[str] = Query(None, description="Filter by violation type (e.g., 'missing_encryption')"),
    severity: Optional[ComplianceSeverity] = Query(None, description="Filter by severity"),
    compliance_status: Optional[ComplianceStatus] = Query(None, alias="status", description="Filter by status"),
    api_name: Optional[str] = Query(None, description="Filter by API name pattern (case-insensitive wildcard)"),
    gateway_id: Optional[UUID] = Query(None, description="Filter by gateway ID"),
    discovered_after: Optional[datetime] = Query(None, description="Filter violations discovered after this date (ISO 8601)"),
    discovered_before: Optional[datetime] = Query(None, description="Filter violations discovered before this date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> ComplianceViolationListResponse:
    """
    Search compliance violations with multiple filters.
    
    Supports flexible filtering by:
    - Compliance standard (GDPR, HIPAA, PCI_DSS, SOC2, ISO27001)
    - Violation type (e.g., 'missing_encryption', 'inadequate_logging')
    - Severity (critical, high, medium, low)
    - Status (open, in_progress, resolved, accepted)
    - API name pattern (case-insensitive wildcard search)
    - Gateway ID
    - Discovery date range
    
    All filters are optional and combined with AND logic.
    Results are paginated with configurable page size (max 100).
    
    Args:
        standard: Optional compliance standard filter
        violation_type: Optional violation type filter
        severity: Optional severity filter
        compliance_status: Optional status filter
        api_name: Optional API name pattern (case-insensitive)
        gateway_id: Optional gateway ID filter
        discovered_after: Optional start date for discovery range
        discovered_before: Optional end date for discovery range
        page: Page number (1-based)
        page_size: Number of items per page (max 100)
        compliance_service: Compliance service dependency
        
    Returns:
        Paginated list of compliance violations matching filters
        
    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(
            f"Searching compliance violations: standard={standard}, violation_type={violation_type}, "
            f"severity={severity}, status={compliance_status}, api_name={api_name}, "
            f"gateway_id={gateway_id}, discovered_after={discovered_after}, "
            f"discovered_before={discovered_before}, page={page}, page_size={page_size}"
        )
        
        from app.db.repositories.compliance_repository import ComplianceRepository
        
        compliance_repo = ComplianceRepository()
        
        # Call repository search method
        violations, total = compliance_repo.search_compliance_violations(
            standard=standard,
            violation_type=violation_type,
            severity=severity,
            status=compliance_status,
            api_name=api_name,
            gateway_id=gateway_id,
            discovered_after=discovered_after,
            discovered_before=discovered_before,
            page=page,
            page_size=page_size,
        )
        
        logger.info(f"Found {total} compliance violations matching search criteria")
        
        return ComplianceViolationListResponse(
            items=violations,
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error(f"Failed to search compliance violations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search compliance violations: {str(e)}",
        )


# Made with Bob
