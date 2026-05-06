"""Compliance Analytics Service for AI-Driven Insights.

Provides advanced analytics capabilities for compliance audit reports:
- Trend analysis across time periods
- Risk scoring and prioritization
- Predictive insights for future violations
- Remediation prioritization recommendations
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from collections import defaultdict

from app.db.repositories.compliance_repository import ComplianceRepository
from app.models.compliance import (
    ComplianceViolation,
    ComplianceSeverity,
    ComplianceStandard,
    ComplianceStatus,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ComplianceAnalytics:
    """Advanced analytics for compliance violations and audit reports."""

    def __init__(
        self,
        compliance_repository: ComplianceRepository,
        llm_service: Optional[LLMService] = None,
    ):
        """Initialize compliance analytics service.
        
        Args:
            compliance_repository: Repository for compliance data access
            llm_service: Optional LLM service for AI-driven insights
        """
        self.compliance_repository = compliance_repository
        self.llm_service = llm_service

    async def analyze_trends(
        self,
        gateway_id: UUID,
        lookback_days: int = 90,
        interval_days: int = 7,
    ) -> Dict[str, Any]:
        """Analyze compliance violation trends over time.
        
        Args:
            gateway_id: Gateway to analyze
            lookback_days: Number of days to look back
            interval_days: Interval for trend buckets (default: weekly)
            
        Returns:
            Trend analysis with time series data and insights
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get all violations in the period
            violations = await self.compliance_repository.find_by_gateway_and_date_range(
                gateway_id=gateway_id,
                start_date=start_date,
                end_date=end_date,
            )
            
            # Group violations by time intervals
            intervals = []
            current_date = start_date
            while current_date < end_date:
                interval_end = min(current_date + timedelta(days=interval_days), end_date)
                intervals.append({
                    "start": current_date,
                    "end": interval_end,
                    "violations": [],
                })
                current_date = interval_end
            
            # Distribute violations into intervals
            for violation in violations:
                detected_at_raw = violation.detected_at
                if isinstance(detected_at_raw, str):
                    detected_at_str: str = detected_at_raw
                    if 'Z' in detected_at_str:
                        iso_str = detected_at_str.replace('Z', '+00:00')  # type: ignore[arg-type]
                        detected_at = datetime.fromisoformat(iso_str)
                    else:
                        detected_at = datetime.fromisoformat(detected_at_str)
                else:
                    detected_at = detected_at_raw
                
                if hasattr(detected_at, 'tzinfo') and detected_at.tzinfo:
                    detected_at = detected_at.replace(tzinfo=None)
                
                for interval in intervals:
                    if interval["start"] <= detected_at < interval["end"]:
                        interval["violations"].append(violation)
                        break
            
            # Calculate metrics for each interval
            time_series = []
            for interval in intervals:
                interval_violations = interval["violations"]
                by_severity = self._count_by_severity(interval_violations)
                by_standard = self._count_by_standard(interval_violations)
                
                time_series.append({
                    "period_start": interval["start"].isoformat(),
                    "period_end": interval["end"].isoformat(),
                    "total_violations": len(interval_violations),
                    "by_severity": by_severity,
                    "by_standard": by_standard,
                    "new_violations": len([v for v in interval_violations if v.status == ComplianceStatus.OPEN]),
                    "resolved_violations": len([v for v in interval_violations if v.status == ComplianceStatus.REMEDIATED]),
                })
            
            # Calculate trend direction
            if len(time_series) >= 2:
                recent_avg = sum(t["total_violations"] for t in time_series[-3:]) / min(3, len(time_series))
                older_avg = sum(t["total_violations"] for t in time_series[:3]) / min(3, len(time_series))
                trend_direction = "increasing" if recent_avg > older_avg else "decreasing" if recent_avg < older_avg else "stable"
                trend_percentage = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            else:
                trend_direction = "insufficient_data"
                trend_percentage = 0
            
            # Generate AI insights if available
            ai_insights = None
            if self.llm_service:
                ai_insights = await self._generate_trend_insights(time_series, trend_direction, trend_percentage)
            
            return {
                "lookback_days": lookback_days,
                "interval_days": interval_days,
                "time_series": time_series,
                "trend_direction": trend_direction,
                "trend_percentage": round(trend_percentage, 2),
                "total_violations_in_period": len(violations),
                "ai_insights": ai_insights,
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze trends: {e}", exc_info=True)
            raise

    async def calculate_risk_scores(
        self,
        violations: List[ComplianceViolation],
    ) -> Dict[str, Any]:
        """Calculate risk scores for violations and APIs.
        
        Risk scoring considers:
        - Severity of violations
        - Number of violations per API
        - Time since detection
        - Compliance standards affected
        - Remediation status
        
        Args:
            violations: List of violations to score
            
        Returns:
            Risk scores and prioritization data
        """
        try:
            # Severity weights
            severity_weights = {
                ComplianceSeverity.CRITICAL: 10,
                ComplianceSeverity.HIGH: 7,
                ComplianceSeverity.MEDIUM: 4,
                ComplianceSeverity.LOW: 1,
            }
            
            # Calculate risk scores per API
            api_risks: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "total_score": 0.0,
                "violation_count": 0,
                "critical_count": 0,
                "high_count": 0,
                "standards_affected": set(),
                "oldest_violation_days": 0,
                "violations": [],
            })
            
            now = datetime.utcnow()
            
            for violation in violations:
                api_id = str(violation.api_id)
                api_risk = api_risks[api_id]
                
                # Base score from severity
                base_score = severity_weights.get(violation.severity, 1)
                
                # Age multiplier (older violations are riskier)
                detected_at_raw = violation.detected_at
                if isinstance(detected_at_raw, str):
                    # Handle ISO format strings with Z suffix
                    detected_at_str: str = detected_at_raw
                    if 'Z' in detected_at_str:
                        # Replace Z with timezone offset for ISO parsing
                        iso_str = detected_at_str.replace('Z', '+00:00')  # type: ignore[arg-type]
                        detected_at = datetime.fromisoformat(iso_str)
                    else:
                        detected_at = datetime.fromisoformat(detected_at_str)
                else:
                    detected_at = detected_at_raw
                
                if hasattr(detected_at, 'tzinfo') and detected_at.tzinfo:
                    detected_at = detected_at.replace(tzinfo=None)
                
                age_days = (now - detected_at).days
                age_multiplier = 1 + (age_days / 30) * 0.5  # 50% increase per month
                
                # Status multiplier (open violations are riskier)
                status_multiplier = 1.5 if violation.status == ComplianceStatus.OPEN else 0.5
                
                # Calculate final score
                violation_score = base_score * age_multiplier * status_multiplier
                
                # Update API risk data
                api_risk["total_score"] += violation_score
                api_risk["violation_count"] += 1
                api_risk["standards_affected"].add(violation.compliance_standard.value)
                api_risk["oldest_violation_days"] = max(api_risk["oldest_violation_days"], age_days)
                api_risk["violations"].append(violation)
                
                if violation.severity == ComplianceSeverity.CRITICAL:
                    api_risk["critical_count"] += 1
                elif violation.severity == ComplianceSeverity.HIGH:
                    api_risk["high_count"] += 1
            
            # Convert to list and sort by risk score
            api_risk_list = []
            for api_id, risk_data in api_risks.items():
                api_risk_list.append({
                    "api_id": api_id,
                    "risk_score": round(risk_data["total_score"], 2),
                    "risk_level": self._categorize_risk_level(risk_data["total_score"]),
                    "violation_count": risk_data["violation_count"],
                    "critical_violations": risk_data["critical_count"],
                    "high_violations": risk_data["high_count"],
                    "standards_affected": list(risk_data["standards_affected"]),
                    "oldest_violation_days": risk_data["oldest_violation_days"],
                })
            
            api_risk_list.sort(key=lambda x: x["risk_score"], reverse=True)
            
            # Calculate overall risk metrics
            total_risk_score = sum(api["risk_score"] for api in api_risk_list)
            avg_risk_score = total_risk_score / len(api_risk_list) if api_risk_list else 0
            
            high_risk_apis = [api for api in api_risk_list if api["risk_level"] == "high"]
            medium_risk_apis = [api for api in api_risk_list if api["risk_level"] == "medium"]
            low_risk_apis = [api for api in api_risk_list if api["risk_level"] == "low"]
            
            return {
                "total_risk_score": round(total_risk_score, 2),
                "average_risk_score": round(avg_risk_score, 2),
                "high_risk_api_count": len(high_risk_apis),
                "medium_risk_api_count": len(medium_risk_apis),
                "low_risk_api_count": len(low_risk_apis),
                "api_risk_scores": api_risk_list[:20],  # Top 20 riskiest APIs
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate risk scores: {e}", exc_info=True)
            raise

    async def generate_predictive_insights(
        self,
        gateway_id: UUID,
        violations: List[ComplianceViolation],
    ) -> Dict[str, Any]:
        """Generate predictive insights about future compliance risks.
        
        Args:
            gateway_id: Gateway to analyze
            violations: Current violations
            
        Returns:
            Predictive insights and recommendations
        """
        try:
            if not self.llm_service:
                return {
                    "predictions": [],
                    "confidence": "low",
                    "message": "AI-driven predictions require LLM service",
                }
            
            # Analyze patterns
            by_severity = self._count_by_severity(violations)
            by_standard = self._count_by_standard(violations)
            by_status = self._count_by_status(violations)
            
            # Calculate remediation velocity
            resolved_violations = [v for v in violations if v.status == ComplianceStatus.REMEDIATED]
            if resolved_violations:
                resolution_times = []
                for v in resolved_violations:
                    if v.remediated_at and v.detected_at:
                        # Parse detected_at
                        if isinstance(v.detected_at, datetime):
                            detected = v.detected_at
                        else:
                            detected_str = v.detected_at.replace('Z', '+00:00') if 'Z' in v.detected_at else v.detected_at
                            detected = datetime.fromisoformat(detected_str)
                        
                        # Parse remediated_at
                        if isinstance(v.remediated_at, datetime):
                            resolved = v.remediated_at
                        else:
                            resolved_str = v.remediated_at.replace('Z', '+00:00') if 'Z' in v.remediated_at else v.remediated_at
                            resolved = datetime.fromisoformat(resolved_str)
                        if detected.tzinfo:
                            detected = detected.replace(tzinfo=None)
                        if resolved.tzinfo:
                            resolved = resolved.replace(tzinfo=None)
                        resolution_times.append((resolved - detected).days)
                
                avg_resolution_days = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            else:
                avg_resolution_days = 0
            
            # Build context for LLM
            context = f"""
Analyze the following compliance data and provide predictive insights:

Current Violations:
- Total: {len(violations)}
- By Severity: {by_severity}
- By Standard: {by_standard}
- By Status: {by_status}

Remediation Metrics:
- Resolved Violations: {len(resolved_violations)}
- Average Resolution Time: {avg_resolution_days:.1f} days
- Open Violations: {by_status.get('open', 0)}

Based on these patterns, predict:
1. Which compliance standards are likely to have increased violations in the next 30 days
2. Which APIs or areas need immediate attention to prevent future violations
3. Estimated time to achieve 80% remediation rate at current velocity
4. Recommended actions to improve compliance posture

Provide specific, actionable predictions with confidence levels.
"""
            
            messages = [{"role": "user", "content": context}]
            response = await self.llm_service.generate_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=800,
            )
            
            return {
                "predictions": response["content"],
                "confidence": "high" if len(violations) > 20 else "medium",
                "based_on_violations": len(violations),
                "avg_resolution_days": round(avg_resolution_days, 1),
            }
            
        except Exception as e:
            logger.error(f"Failed to generate predictive insights: {e}", exc_info=True)
            return {
                "predictions": "Unable to generate predictions due to error",
                "confidence": "low",
                "error": str(e),
            }

    async def prioritize_remediation(
        self,
        violations: List[ComplianceViolation],
    ) -> Dict[str, Any]:
        """Prioritize violations for remediation based on multiple factors.
        
        Prioritization considers:
        - Severity and risk score
        - Compliance standard requirements
        - Age of violation
        - Remediation complexity
        - Business impact
        
        Args:
            violations: Violations to prioritize
            
        Returns:
            Prioritized remediation plan
        """
        try:
            # Calculate risk scores first
            risk_data = await self.calculate_risk_scores(violations)
            api_risks = {api["api_id"]: api["risk_score"] for api in risk_data["api_risk_scores"]}
            
            # Score each violation for prioritization
            prioritized_violations = []
            
            for violation in violations:
                if violation.status != ComplianceStatus.OPEN:
                    continue  # Only prioritize open violations
                
                # Base priority from severity
                severity_priority = {
                    ComplianceSeverity.CRITICAL: 100,
                    ComplianceSeverity.HIGH: 75,
                    ComplianceSeverity.MEDIUM: 50,
                    ComplianceSeverity.LOW: 25,
                }.get(violation.severity, 25)
                
                # Age factor (older = higher priority)
                detected_at_raw = violation.detected_at
                if isinstance(detected_at_raw, str):
                    # Handle ISO format strings with Z suffix
                    detected_at_str: str = detected_at_raw
                    if 'Z' in detected_at_str:
                        # Replace Z with timezone offset for ISO parsing
                        iso_str = detected_at_str.replace('Z', '+00:00')  # type: ignore[arg-type]
                        detected_at = datetime.fromisoformat(iso_str)
                    else:
                        detected_at = datetime.fromisoformat(detected_at_str)
                else:
                    detected_at = detected_at_raw
                
                if hasattr(detected_at, 'tzinfo') and detected_at.tzinfo:
                    detected_at = detected_at.replace(tzinfo=None)
                
                age_days = (datetime.utcnow() - detected_at).days
                age_factor = min(age_days / 30 * 20, 20)  # Max 20 points for age
                
                # API risk factor
                api_risk_score = api_risks.get(str(violation.api_id), 0)
                risk_factor = min(api_risk_score / 10, 30)  # Max 30 points from API risk
                
                # Standard criticality (some standards have stricter requirements)
                standard_priority = {
                    ComplianceStandard.PCI_DSS: 15,
                    ComplianceStandard.HIPAA: 15,
                    ComplianceStandard.GDPR: 12,
                    ComplianceStandard.SOC2: 10,
                    ComplianceStandard.ISO_27001: 8,
                }.get(violation.compliance_standard, 10)
                
                # Calculate total priority score
                priority_score = severity_priority + age_factor + risk_factor + standard_priority
                
                # Determine priority tier
                if priority_score >= 120:
                    priority_tier = "immediate"
                elif priority_score >= 90:
                    priority_tier = "high"
                elif priority_score >= 60:
                    priority_tier = "medium"
                else:
                    priority_tier = "low"
                
                prioritized_violations.append({
                    "violation_id": str(violation.id),
                    "api_id": str(violation.api_id),
                    "severity": violation.severity.value,
                    "standard": violation.compliance_standard.value,
                    "violation_type": violation.violation_type.value,
                    "priority_score": round(priority_score, 2),
                    "priority_tier": priority_tier,
                    "age_days": age_days,
                    "description": violation.description,
                    "recommended_action": violation.remediation_documentation[0].action if violation.remediation_documentation else "Review and remediate",
                })
            
            # Sort by priority score
            prioritized_violations.sort(key=lambda x: x["priority_score"], reverse=True)
            
            # Group by priority tier
            by_tier = {
                "immediate": [v for v in prioritized_violations if v["priority_tier"] == "immediate"],
                "high": [v for v in prioritized_violations if v["priority_tier"] == "high"],
                "medium": [v for v in prioritized_violations if v["priority_tier"] == "medium"],
                "low": [v for v in prioritized_violations if v["priority_tier"] == "low"],
            }
            
            return {
                "total_open_violations": len(prioritized_violations),
                "immediate_action_required": len(by_tier["immediate"]),
                "high_priority": len(by_tier["high"]),
                "medium_priority": len(by_tier["medium"]),
                "low_priority": len(by_tier["low"]),
                "prioritized_violations": prioritized_violations[:50],  # Top 50
                "by_priority_tier": {
                    "immediate": by_tier["immediate"][:10],
                    "high": by_tier["high"][:10],
                    "medium": by_tier["medium"][:10],
                    "low": by_tier["low"][:10],
                },
            }
            
        except Exception as e:
            logger.error(f"Failed to prioritize remediation: {e}", exc_info=True)
            raise

    # Helper methods
    
    def _count_by_severity(self, violations: List[ComplianceViolation]) -> Dict[str, int]:
        """Count violations by severity."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for v in violations:
            if v.severity.value in counts:
                counts[v.severity.value] += 1
        return counts
    
    def _count_by_standard(self, violations: List[ComplianceViolation]) -> Dict[str, int]:
        """Count violations by standard."""
        counts = defaultdict(int)
        for v in violations:
            counts[v.compliance_standard.value] += 1
        return dict(counts)
    
    def _count_by_status(self, violations: List[ComplianceViolation]) -> Dict[str, int]:
        """Count violations by status."""
        counts = defaultdict(int)
        for v in violations:
            counts[v.status.value] += 1
        return dict(counts)
    
    def _categorize_risk_level(self, risk_score: float) -> str:
        """Categorize risk score into levels."""
        if risk_score >= 50:
            return "high"
        elif risk_score >= 20:
            return "medium"
        else:
            return "low"
    
    async def _generate_trend_insights(
        self,
        time_series: List[Dict[str, Any]],
        trend_direction: str,
        trend_percentage: float,
    ) -> str:
        """Generate AI insights about trends."""
        try:
            if not self.llm_service:
                return "AI insights unavailable"
            
            context = f"""
Analyze the following compliance violation trends and provide insights:

Trend Direction: {trend_direction}
Trend Change: {trend_percentage:+.1f}%

Time Series Data (most recent periods):
{self._format_time_series_for_llm(time_series[-5:])}

Provide:
1. Key observations about the trend
2. Potential causes for the trend
3. Recommended actions based on the trend
4. Risk assessment if trend continues

Keep the response concise (2-3 paragraphs).
"""
            
            messages = [{"role": "user", "content": context}]
            response = await self.llm_service.generate_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=400,
            )
            
            return response["content"]
            
        except Exception as e:
            logger.warning(f"Failed to generate trend insights: {e}")
            return f"Trend is {trend_direction} by {trend_percentage:+.1f}%"
    
    def _format_time_series_for_llm(self, time_series: List[Dict[str, Any]]) -> str:
        """Format time series data for LLM context."""
        lines = []
        for period in time_series:
            lines.append(
                f"Period {period['period_start'][:10]}: "
                f"{period['total_violations']} violations "
                f"(Critical: {period['by_severity'].get('critical', 0)}, "
                f"High: {period['by_severity'].get('high', 0)})"
            )
        return "\n".join(lines)

# Made with Bob
