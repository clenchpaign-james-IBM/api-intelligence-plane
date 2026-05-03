"""Security scanning scheduler jobs for API Intelligence Plane.

Runs periodic security scans and automated remediation workflows.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Settings
from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class SecurityScheduler:
    """Scheduler for security scanning and remediation jobs."""

    def __init__(
        self,
        scheduler: AsyncIOScheduler,
        settings: Settings,
        security_service: SecurityService,
    ):
        """Initialize security scheduler.

        Args:
            scheduler: APScheduler instance
            settings: Application settings
            security_service: Security service instance
        """
        self.scheduler = scheduler
        self.settings = settings
        self.security_service = security_service

    def register_jobs(self) -> None:
        """Register all security-related scheduled jobs."""
        # Security scan job - runs every 1 hour
        self.scheduler.add_job(
            func=self._run_security_scan,
            trigger=IntervalTrigger(minutes=self.settings.SECURITY_SCAN_INTERVAL_MINUTES),
            id="security_scan",
            name="Security Scan - All APIs",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping scans
        )

        # Automated remediation job - runs every 30 minutes
        # self.scheduler.add_job(
        #     func=self._run_automated_remediation,
        #     trigger=IntervalTrigger(minutes=3),
        #     id="automated_remediation",
        #     name="Automated Vulnerability Remediation",
        #     replace_existing=True,
        #     max_instances=1,
        # )

        # Remediation verification job - runs every 2 hours
        # self.scheduler.add_job(
        #     func=self._verify_remediations,
        #     trigger=IntervalTrigger(minutes=6),
        #     id="remediation_verification",
        #     name="Remediation Verification",
        #     replace_existing=True,
        #     max_instances=1,
        # )

        # Security posture report - runs daily at 8 AM
        self.scheduler.add_job(
            func=self._generate_security_report,
            trigger=CronTrigger(hour=8, minute=0),
            id="security_report",
            name="Daily Security Posture Report",
            replace_existing=True,
        )

        logger.info("Security scheduler jobs registered")

    async def _run_security_scan(self) -> None:
        """Run security scan for all APIs across all gateways.
        
        This job:
        1. Iterates over all gateways
        2. Scans each gateway's APIs for security policy coverage
        3. Uses hybrid analysis (rule-based + AI-enhanced) with metrics
        4. Stores detected vulnerabilities
        5. Generates remediation plans
        """
        try:
            logger.info("Starting scheduled security scan (hybrid analysis, gateway-scoped)")
            start_time = datetime.utcnow()

            # Get all gateways
            from app.db.repositories.gateway_repository import GatewayRepository
            gateway_repo = GatewayRepository()
            gateways, _ = gateway_repo.list_all(size=1000)
            
            # Aggregate results across all gateways
            total_apis_scanned = 0
            total_vulnerabilities = 0
            all_scan_results = []
            
            for gateway in gateways:
                try:
                    logger.info(f"Scanning gateway {gateway.id} ({gateway.name})")
                    gateway_result = await self.security_service.scan_gateway_apis(gateway.id)
                    total_apis_scanned += gateway_result["apis_scanned"]
                    total_vulnerabilities += gateway_result["total_vulnerabilities"]
                    all_scan_results.extend(gateway_result.get("scan_results", []))
                except Exception as e:
                    logger.error(f"Failed to scan gateway {gateway.id}: {e}")
            
            result = {
                "total_gateways": len(gateways),
                "apis_scanned": total_apis_scanned,
                "total_vulnerabilities": total_vulnerabilities,
                "scan_results": all_scan_results,
            }

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Security scan completed in {duration:.2f}s. "
                f"Scanned {result['apis_scanned']} APIs, "
                f"found {result['total_vulnerabilities']} vulnerabilities"
            )

            # Log summary by severity
            self._log_scan_summary(result)

        except Exception as e:
            logger.error(f"Security scan job failed: {str(e)}", exc_info=True)

    async def _run_automated_remediation(self) -> None:
        """Run automated remediation for open vulnerabilities.
        
        This job:
        1. Finds all remediable vulnerabilities
        2. Applies automated fixes at gateway level
        3. Verifies remediation success
        4. Updates vulnerability status
        """
        try:
            logger.info("Starting automated remediation job")
            start_time = datetime.utcnow()

            # Get remediable vulnerabilities
            vulnerabilities = await self.security_service.vulnerability_repository.find_remediable_vulnerabilities(
                limit=50  # Process top 50 per run
            )

            if not vulnerabilities:
                logger.info("No remediable vulnerabilities found")
                return

            logger.info(f"Found {len(vulnerabilities)} remediable vulnerabilities")

            # Remediate each vulnerability
            remediated_count = 0
            failed_count = 0

            for vuln in vulnerabilities:
                try:
                    result = await self.security_service.remediate_vulnerability(
                        vuln.id
                    )

                    if result.get("status") == "remediation_applied":
                        remediated_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to remediate vulnerability {vuln.id}: {str(e)}"
                    )
                    failed_count += 1

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Automated remediation completed in {duration:.2f}s. "
                f"Remediated: {remediated_count}, Failed: {failed_count}"
            )

        except Exception as e:
            logger.error(f"Automated remediation job failed: {str(e)}", exc_info=True)

    async def _verify_remediations(self) -> None:
        """Verify that applied remediations are still effective.
        
        This job:
        1. Finds recently remediated vulnerabilities
        2. Re-scans to verify fixes are still in place
        3. Updates verification status
        4. Alerts if remediations have regressed
        """
        try:
            logger.info("Starting remediation verification job")
            start_time = datetime.utcnow()

            # Get recently remediated vulnerabilities (last 7 days)
            from app.models.vulnerability import VulnerabilityStatus
            from datetime import timedelta

            # Query vulnerabilities remediated in last 7 days
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"status": VulnerabilityStatus.REMEDIATED.value}},
                            {
                                "range": {
                                    "remediated_at": {
                                        "gte": (datetime.utcnow() - timedelta(days=7)).isoformat()
                                    }
                                }
                            },
                        ]
                    }
                },
                "size": 100,
            }

            response = self.security_service.vulnerability_repository.client.search(
                index=self.security_service.vulnerability_repository.index_name,
                body=query,
            )

            vulnerabilities = [
                self.security_service.vulnerability_repository.model_class(**hit["_source"])
                for hit in response["hits"]["hits"]
            ]

            if not vulnerabilities:
                logger.info("No recent remediations to verify")
                return

            logger.info(f"Verifying {len(vulnerabilities)} remediations")

            verified_count = 0
            failed_count = 0

            for vuln in vulnerabilities:
                try:
                    result = await self.security_service.verify_remediation(vuln.id)

                    if result.get("is_fixed"):
                        verified_count += 1
                    else:
                        failed_count += 1
                        logger.warning(
                            f"Remediation verification failed for {vuln.id}: "
                            f"{vuln.title}"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to verify remediation {vuln.id}: {str(e)}"
                    )
                    failed_count += 1

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Remediation verification completed in {duration:.2f}s. "
                f"Verified: {verified_count}, Failed: {failed_count}"
            )

        except Exception as e:
            logger.error(f"Remediation verification job failed: {str(e)}", exc_info=True)

    async def _generate_security_report(self) -> None:
        """Generate daily security posture report.
        
        This job:
        1. Aggregates security metrics
        2. Calculates risk scores
        3. Identifies trends
        4. Logs comprehensive security status
        """
        try:
            logger.info("Generating daily security posture report")

            # Get overall security posture
            posture = await self.security_service.get_security_posture()

            # Log comprehensive report
            logger.info("=" * 80)
            logger.info("DAILY SECURITY POSTURE REPORT")
            logger.info(f"Generated: {datetime.utcnow().isoformat()}")
            logger.info("=" * 80)
            logger.info(f"Total Vulnerabilities: {posture['total_vulnerabilities']}")
            logger.info(f"Risk Score: {posture['risk_score']}/100 ({posture['risk_level'].upper()})")
            logger.info(f"Remediation Rate: {posture['remediation_rate']}%")
            logger.info("")
            logger.info("By Severity:")
            for severity, count in posture['by_severity'].items():
                logger.info(f"  {severity.upper()}: {count}")
            logger.info("")
            logger.info("By Status:")
            for status, count in posture['by_status'].items():
                logger.info(f"  {status.upper()}: {count}")
            logger.info("")
            logger.info("By Type:")
            for vuln_type, count in posture['by_type'].items():
                logger.info(f"  {vuln_type.upper()}: {count}")
            logger.info("=" * 80)

            # Alert if risk score is high
            if posture['risk_score'] >= 75:
                logger.warning(
                    f"⚠️  CRITICAL: Security risk score is {posture['risk_score']}/100. "
                    "Immediate attention required!"
                )
            elif posture['risk_score'] >= 50:
                logger.warning(
                    f"⚠️  HIGH: Security risk score is {posture['risk_score']}/100. "
                    "Review and remediate high-priority vulnerabilities."
                )

        except Exception as e:
            logger.error(f"Security report generation failed: {str(e)}", exc_info=True)

    def _log_scan_summary(self, result: Dict[str, Any]) -> None:
        """Log summary of security scan results.

        Args:
            result: Scan result dictionary
        """
        if not result.get("scan_results"):
            return

        # Aggregate severity counts
        severity_totals = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for scan in result["scan_results"]:
            breakdown = scan.get("severity_breakdown", {})
            for severity, count in breakdown.items():
                if severity in severity_totals:
                    severity_totals[severity] += count

        logger.info("Scan Summary by Severity:")
        for severity, count in severity_totals.items():
            if count > 0:
                logger.info(f"  {severity.upper()}: {count}")


def setup_security_scheduler(
    scheduler: AsyncIOScheduler,
    settings: Settings,
    security_service: SecurityService,
) -> SecurityScheduler:
    """Setup and register security scheduler jobs.

    Args:
        scheduler: APScheduler instance
        settings: Application settings
        security_service: Security service instance

    Returns:
        Configured SecurityScheduler instance
    """
    security_scheduler = SecurityScheduler(scheduler, settings, security_service)
    security_scheduler.register_jobs()

    logger.info("Security scheduler setup complete")
    return security_scheduler


# Made with Bob