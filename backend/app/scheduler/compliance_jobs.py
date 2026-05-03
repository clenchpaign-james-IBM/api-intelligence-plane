"""Compliance monitoring scheduler jobs for API Intelligence Plane.

Runs periodic compliance scans and audit report generation.
Focuses on scheduled audit preparation (24-hour cycle) distinct from immediate security threat response.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Settings
from app.services.compliance_service import ComplianceService

logger = logging.getLogger(__name__)


class ComplianceScheduler:
    """Scheduler for compliance monitoring and audit reporting jobs."""

    def __init__(
        self,
        scheduler: AsyncIOScheduler,
        settings: Settings,
        compliance_service: ComplianceService,
    ):
        """Initialize compliance scheduler.

        Args:
            scheduler: APScheduler instance
            settings: Application settings
            compliance_service: Compliance service instance
        """
        self.scheduler = scheduler
        self.settings = settings
        self.compliance_service = compliance_service

    def register_jobs(self) -> None:
        """Register all compliance-related scheduled jobs."""
        # Compliance scan job - runs every 24 hours (daily at 2 AM)
        # Scheduled for audit preparation, not immediate threat response
        # self.scheduler.add_job(
        #     func=self._run_compliance_scan,
        #     trigger=CronTrigger(hour=15, minute=8),
        #     id="compliance_scan",
        #     name="Daily Compliance Scan - All APIs",
        #     replace_existing=True,
        #     max_instances=1,  # Prevent overlapping scans
        # )

        self.scheduler.add_job(
            func=self._run_compliance_scan,
            trigger=IntervalTrigger(minutes=self.settings.COMPLIANCE_SCAN_INTERVAL_MINUTES),
            id="compliance_scan",
            name="Daily Compliance Scan - All APIs",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping scans
        )

        # Audit report generation - runs weekly on Monday at 9 AM
        self.scheduler.add_job(
            func=self._generate_audit_report,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="weekly_audit_report",
            name="Weekly Audit Report Generation",
            replace_existing=True,
            max_instances=1,
        )

        # Compliance posture report - runs daily at 9 AM
        self.scheduler.add_job(
            func=self._generate_compliance_posture_report,
            trigger=CronTrigger(hour=9, minute=0),
            id="compliance_posture_report",
            name="Daily Compliance Posture Report",
            replace_existing=True,
        )

        # Audit reminder - runs monthly on 1st at 10 AM
        # Identifies violations needing attention before upcoming audits
        self.scheduler.add_job(
            func=self._send_audit_reminders,
            trigger=CronTrigger(day=1, hour=10, minute=0),
            id="audit_reminders",
            name="Monthly Audit Reminders",
            replace_existing=True,
        )

        logger.info("Compliance scheduler jobs registered")

    async def _run_compliance_scan(self) -> Dict[str, Any]:
        """Run compliance scan for all APIs across all gateways.

        Returns:
            Scan results summary
        """
        try:
            logger.info("Starting scheduled compliance scan (gateway-scoped)")
            start_time = datetime.utcnow()

            # Get all gateways
            from app.db.repositories.gateway_repository import GatewayRepository
            gateway_repo = GatewayRepository()
            gateways, _ = gateway_repo.list_all(size=1000)
            
            # Aggregate results across all gateways
            total_apis_scanned = 0
            total_violations = 0
            all_scan_results = []
            
            for gateway in gateways:
                try:
                    logger.info(f"Scanning gateway {gateway.id} ({gateway.name}) for compliance")
                    gateway_result = await self.compliance_service.scan_gateway_apis(gateway.id)
                    total_apis_scanned += gateway_result["apis_scanned"]
                    total_violations += gateway_result["total_violations"]
                    all_scan_results.extend(gateway_result.get("scan_results", []))
                except Exception as e:
                    logger.error(f"Failed to scan gateway {gateway.id}: {e}")
            
            result = {
                "total_gateways": len(gateways),
                "apis_scanned": total_apis_scanned,
                "total_violations": total_violations,
                "scan_results": all_scan_results,
            }

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Compliance scan completed in {duration:.2f}s. "
                f"Scanned {result['total_gateways']} gateways, "
                f"{result['apis_scanned']} APIs, "
                f"found {result['total_violations']} violations"
            )

            return {
                "status": "success",
                "scan_completed_at": datetime.utcnow().isoformat(),
                "total_gateways": result["total_gateways"],
                "apis_scanned": result["apis_scanned"],
                "total_violations": result["total_violations"],
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"Scheduled compliance scan failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "scan_completed_at": datetime.utcnow().isoformat(),
            }

    async def _generate_audit_report(self) -> Dict[str, Any]:
        """Generate weekly audit report.

        Returns:
            Report generation summary
        """
        try:
            logger.info("Starting weekly audit report generation")
            start_time = datetime.utcnow()

            # Generate comprehensive audit report
            report = await self.compliance_service.generate_audit_report()

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Audit report generated in {duration:.2f}s. "
                f"Report ID: {report['report_id']}"
            )

            # In production, this would:
            # 1. Store report in database
            # 2. Send to compliance officers via email
            # 3. Upload to audit management system
            # 4. Generate PDF for external auditors

            return {
                "status": "success",
                "report_id": report["report_id"],
                "generated_at": report["generated_at"],
                "total_violations": report["compliance_posture"]["total_violations"],
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"Audit report generation failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat(),
            }

    async def _generate_compliance_posture_report(self) -> Dict[str, Any]:
        """Generate daily compliance posture report.

        Returns:
            Posture report summary
        """
        try:
            logger.info("Starting daily compliance posture report")
            start_time = datetime.utcnow()

            # Get current compliance posture
            posture = await self.compliance_service.get_compliance_posture()

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Compliance posture report generated in {duration:.2f}s. "
                f"Compliance score: {posture['compliance_score']}"
            )

            # In production, this would:
            # 1. Store posture metrics in time-series database
            # 2. Send summary to compliance dashboard
            # 3. Alert on significant score changes
            # 4. Update compliance tracking systems

            return {
                "status": "success",
                "generated_at": datetime.utcnow().isoformat(),
                "compliance_score": posture["compliance_score"],
                "total_violations": posture["total_violations"],
                "remediation_rate": posture["remediation_rate"],
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"Compliance posture report failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat(),
            }

    async def _send_audit_reminders(self) -> Dict[str, Any]:
        """Send reminders for violations needing audit attention.

        Returns:
            Reminder summary
        """
        try:
            logger.info("Starting monthly audit reminders")
            start_time = datetime.utcnow()

            # Get violations needing audit attention (next 30 days)
            from app.db.repositories.compliance_repository import ComplianceRepository
            compliance_repo = ComplianceRepository()
            
            violations_needing_audit = await compliance_repo.find_violations_needing_audit(
                days_until_audit=30
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Audit reminders processed in {duration:.2f}s. "
                f"Found {len(violations_needing_audit)} violations needing attention"
            )

            # In production, this would:
            # 1. Send email notifications to compliance team
            # 2. Create tickets in issue tracking system
            # 3. Update audit preparation dashboard
            # 4. Escalate critical violations to management

            return {
                "status": "success",
                "generated_at": datetime.utcnow().isoformat(),
                "violations_needing_attention": len(violations_needing_audit),
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"Audit reminders failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat(),
            }


def setup_compliance_scheduler(
    scheduler: AsyncIOScheduler,
    settings: Settings,
    compliance_service: ComplianceService,
) -> ComplianceScheduler:
    """Setup and register compliance scheduler jobs.

    Args:
        scheduler: APScheduler instance
        settings: Application settings
        compliance_service: Compliance service instance

    Returns:
        Configured ComplianceScheduler instance
    """
    compliance_scheduler = ComplianceScheduler(
        scheduler=scheduler,
        settings=settings,
        compliance_service=compliance_service,
    )
    
    compliance_scheduler.register_jobs()
    
    logger.info("Compliance scheduler setup complete")
    return compliance_scheduler

# Made with Bob
