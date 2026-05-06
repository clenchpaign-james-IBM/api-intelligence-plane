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


# Helper functions for HTML report generation
def _validate_report_data_for_html(report: dict) -> dict:
    """Validate and normalize report data for HTML export.
    
    Args:
        report: Raw report data from compliance service
        
    Returns:
        Validated and normalized report data with proper defaults
    """
    from uuid import uuid4
    
    return {
        'report_id': str(report.get('report_id', uuid4())),
        'generated_at': report.get('generated_at', datetime.utcnow().isoformat()),
        'report_period': report.get('report_period', {
            'start': (datetime.utcnow() - timedelta(days=90)).isoformat(),
            'end': datetime.utcnow().isoformat()
        }),
        'executive_summary': report.get('executive_summary', 'Executive summary not available'),
        'compliance_posture': report.get('compliance_posture', {
            'total_violations': 0,
            'open_violations': 0,
            'remediated_violations': 0,
            'remediation_rate': 0.0
        }),
        'violations_by_severity': report.get('violations_by_severity', {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }),
        'violations_by_standard': report.get('violations_by_standard', {}),
        'recommendations': report.get('recommendations', [])
    }


def _build_standards_table_rows(violations_by_standard: dict) -> str:
    """Build HTML table rows for violations by standard.
    
    Args:
        violations_by_standard: Dictionary of standard violations
        
    Returns:
        HTML table rows as string
    """
    if not violations_by_standard:
        return '<tr><td colspan="2" class="no-data">No violations by standard</td></tr>'
    
    rows = []
    for std, count in sorted(violations_by_standard.items(), key=lambda x: x[1], reverse=True):
        rows.append(f'<tr><td>{std.upper()}</td><td><strong>{count}</strong></td></tr>')
    
    return '\n'.join(rows)


def _build_recommendations_list(recommendations: list) -> str:
    """Build HTML list items for recommendations.
    
    Args:
        recommendations: List of recommendation strings
        
    Returns:
        HTML list items as string
    """
    if not recommendations:
        return '<li class="no-data">No recommendations available</li>'
    
    items = []
    for rec in recommendations:
        # Escape HTML special characters
        escaped_rec = rec.replace('&', '&').replace('<', '<').replace('>', '>')
        items.append(f'<li>{escaped_rec}</li>')
    
    return '\n'.join(items)


def _build_severity_table_rows(violations_by_severity: dict) -> str:
    """Build HTML table rows for violations by severity.
    
    Args:
        violations_by_severity: Dictionary of severity violations
        
    Returns:
        HTML table rows as string
    """
    severities = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ]
    
    rows = []
    for severity_key, severity_label in severities:
        count = violations_by_severity.get(severity_key, 0)
        rows.append(
            f'<tr class="{severity_key}">'
            f'<td>{severity_label}</td>'
            f'<td><strong>{count}</strong></td>'
            f'</tr>'
        )
    
    return '\n'.join(rows)


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
            # Generate HTML report with proper validation and error handling
            try:
                # Validate and normalize report data
                validated_report = _validate_report_data_for_html(report)
                
                # Extract validated values
                report_id_str = validated_report['report_id']
                generated_at_str = validated_report['generated_at']
                report_period = validated_report['report_period']
                executive_summary = validated_report['executive_summary']
                compliance_posture = validated_report['compliance_posture']
                violations_by_severity = validated_report['violations_by_severity']
                violations_by_standard = validated_report['violations_by_standard']
                recommendations = validated_report['recommendations']
                
                # Build standards table rows
                standards_rows = _build_standards_table_rows(violations_by_standard)
                
                # Build recommendations list
                recommendations_items = _build_recommendations_list(recommendations)
                
                # Build severity rows with proper formatting
                severity_rows = _build_severity_table_rows(violations_by_severity)
                
                # Generate HTML with proper structure
                html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compliance Audit Report - {report_id_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        /* Light mode (default) */
        :root {{
            --bg-primary: #f5f5f5;
            --bg-secondary: white;
            --bg-tertiary: #f8fafc;
            --bg-accent: #eff6ff;
            --text-primary: #1a1a1a;
            --text-secondary: #4a5568;
            --text-muted: #6b7280;
            --border-color: #e2e8f0;
            --accent-color: #2563eb;
            --shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        /* Dark mode */
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-primary: #1a1a1a;
                --bg-secondary: #2d2d2d;
                --bg-tertiary: #3a3a3a;
                --bg-accent: #1e3a5f;
                --text-primary: #f5f5f5;
                --text-secondary: #d1d5db;
                --text-muted: #9ca3af;
                --border-color: #4a4a4a;
                --accent-color: #3b82f6;
                --shadow: 0 2px 4px rgba(0,0,0,0.3);
            }}
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: var(--bg-primary);
        }}
        
        .container {{
            background-color: var(--bg-secondary);
            padding: 40px;
            border-radius: 8px;
            box-shadow: var(--shadow);
        }}
        
        h1 {{
            color: var(--text-primary);
            font-size: 2.5em;
            margin-bottom: 20px;
            border-bottom: 3px solid var(--accent-color);
            padding-bottom: 10px;
        }}
        
        h2 {{
            color: var(--text-secondary);
            font-size: 1.8em;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 8px;
        }}
        
        .metadata {{
            background-color: var(--bg-tertiary);
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 30px;
            border-left: 4px solid var(--accent-color);
        }}
        
        .metadata p {{
            margin: 8px 0;
            font-size: 0.95em;
        }}
        
        .metadata strong {{
            color: var(--text-primary);
            min-width: 120px;
            display: inline-block;
        }}
        
        .summary {{
            background-color: var(--bg-accent);
            padding: 25px;
            border-radius: 8px;
            margin: 30px 0;
            border-left: 4px solid var(--accent-color);
        }}
        
        .summary p {{
            white-space: pre-wrap;
            line-height: 1.8;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            background-color: var(--bg-secondary);
            box-shadow: var(--shadow);
            overflow-x: auto;
            display: block;
        }}
        
        thead, tbody, tr {{
            display: table;
            width: 100%;
            table-layout: fixed;
        }}
        
        th, td {{
            border: 1px solid var(--border-color);
            padding: 14px 16px;
            text-align: left;
        }}
        
        th {{
            background-color: var(--bg-tertiary);
            font-weight: 600;
            color: var(--text-primary);
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        tr:hover {{
            background-color: var(--bg-tertiary);
        }}
        
        .critical {{ color: #dc2626; font-weight: 600; }}
        .high {{ color: #ea580c; font-weight: 600; }}
        .medium {{ color: #ca8a04; font-weight: 600; }}
        .low {{ color: #2563eb; font-weight: 600; }}
        
        ol {{
            margin: 20px 0;
            padding-left: 30px;
        }}
        
        ol li {{
            margin: 12px 0;
            line-height: 1.6;
        }}
        
        .no-data {{
            color: var(--text-muted);
            font-style: italic;
            text-align: center;
            padding: 20px;
        }}
        
        /* Responsive design */
        @media (max-width: 768px) {{
            body {{
                padding: 20px 10px;
            }}
            .container {{
                padding: 20px;
            }}
            h1 {{
                font-size: 1.8em;
            }}
            h2 {{
                font-size: 1.4em;
            }}
            th, td {{
                padding: 10px 8px;
                font-size: 0.9em;
            }}
            .metadata strong {{
                display: block;
                margin-bottom: 4px;
            }}
        }}
        
        @media (max-width: 480px) {{
            h1 {{
                font-size: 1.5em;
            }}
            h2 {{
                font-size: 1.2em;
            }}
            th, td {{
                padding: 8px 6px;
                font-size: 0.85em;
            }}
        }}
        
        /* Print styles */
        @media print {{
            body {{
                background-color: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
            h1 {{
                page-break-after: avoid;
                color: #000;
            }}
            h2 {{
                page-break-after: avoid;
                color: #333;
            }}
            table {{
                page-break-inside: avoid;
            }}
            tr {{
                page-break-inside: avoid;
            }}
            .metadata, .summary {{
                border-left-color: #000;
            }}
        }}
        
        /* Accessibility improvements */
        *:focus {{
            outline: 2px solid var(--accent-color);
            outline-offset: 2px;
        }}
        
        a {{
            color: var(--accent-color);
            text-decoration: underline;
        }}
        
        a:hover {{
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <main class="container" role="main" aria-label="Compliance Audit Report">
        <header>
            <h1 id="report-title">Compliance Audit Report</h1>
        </header>
        
        <section class="metadata" aria-labelledby="metadata-heading">
            <h2 id="metadata-heading" style="position: absolute; left: -10000px;">Report Metadata</h2>
            <p><strong>Report ID:</strong> <span aria-label="Report identifier">{report_id_str}</span></p>
            <p><strong>Generated:</strong> <time datetime="{generated_at_str}">{generated_at_str}</time></p>
            <p><strong>Report Period:</strong> <time datetime="{report_period.get('start', 'N/A')}">{report_period.get('start', 'N/A')}</time> to <time datetime="{report_period.get('end', 'N/A')}">{report_period.get('end', 'N/A')}</time></p>
            <p><strong>Gateway ID:</strong> <span aria-label="Gateway identifier">{gateway_id}</span></p>
        </section>
        
        <section class="summary" aria-labelledby="summary-heading">
            <h2 id="summary-heading">Executive Summary</h2>
            <p>{executive_summary}</p>
        </section>
        
        <section aria-labelledby="posture-heading">
            <h2 id="posture-heading">Compliance Posture</h2>
            <table role="table" aria-label="Compliance posture metrics">
                <thead>
                    <tr>
                        <th scope="col">Metric</th>
                        <th scope="col">Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <th scope="row">Total Violations</th>
                        <td><strong>{compliance_posture.get('total_violations', 0)}</strong></td>
                    </tr>
                    <tr>
                        <th scope="row">Open Violations</th>
                        <td><strong>{compliance_posture.get('open_violations', 0)}</strong></td>
                    </tr>
                    <tr>
                        <th scope="row">Remediated Violations</th>
                        <td><strong>{compliance_posture.get('remediated_violations', 0)}</strong></td>
                    </tr>
                    <tr>
                        <th scope="row">Remediation Rate</th>
                        <td><strong>{compliance_posture.get('remediation_rate', 0):.1f}%</strong></td>
                    </tr>
                </tbody>
            </table>
        </section>
        
        <section aria-labelledby="severity-heading">
            <h2 id="severity-heading">Violations by Severity</h2>
            <table role="table" aria-label="Violations grouped by severity level">
                <thead>
                    <tr>
                        <th scope="col">Severity</th>
                        <th scope="col">Count</th>
                    </tr>
                </thead>
                <tbody>
                    {severity_rows}
                </tbody>
            </table>
        </section>
        
        <section aria-labelledby="standard-heading">
            <h2 id="standard-heading">Violations by Standard</h2>
            <table role="table" aria-label="Violations grouped by compliance standard">
                <thead>
                    <tr>
                        <th scope="col">Standard</th>
                        <th scope="col">Count</th>
                </tr>
            </thead>
            <tbody>
                {standards_rows}
            </tbody>
        </table>
        
        </section>
        
        <section aria-labelledby="recommendations-heading">
            <h2 id="recommendations-heading">Recommendations</h2>
            <ol aria-label="Compliance recommendations">
                {recommendations_items}
            </ol>
        </section>
    </main>
</body>
</html>"""
                
                logger.info(f"HTML report generated successfully for gateway {gateway_id}")
                return HTMLResponse(content=html_content)
                
            except Exception as html_error:
                logger.error(f"Failed to generate HTML report: {str(html_error)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate HTML report: {str(html_error)}",
                )
        
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
