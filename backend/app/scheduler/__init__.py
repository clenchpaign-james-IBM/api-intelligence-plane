"""
Background Scheduler

APScheduler setup for periodic background jobs including:
- API discovery
- Metrics collection
- Security scanning
- Prediction generation
- Optimization analysis
"""

import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """
    Get the global scheduler instance.
    
    Returns:
        AsyncIOScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def setup_scheduler() -> AsyncIOScheduler:
    """
    Setup and configure the background scheduler.
    
    Registers all periodic jobs based on configuration settings.
    Jobs are only added if scheduler is enabled in settings.
    
    Returns:
        Configured scheduler instance
    """
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler is disabled in settings")
        return None
    
    scheduler = get_scheduler()
    
    # Import job functions (will be implemented in respective modules)
    # These imports are done here to avoid circular dependencies
    try:
        from app.scheduler.apis_discovery_jobs import setup_api_discovery_jobs
        from app.scheduler.transactional_logs_collection_jobs import setup_logs_metrics_collection_jobs
        from app.scheduler.security_jobs import setup_security_scheduler
        from app.scheduler.compliance_jobs import setup_compliance_scheduler
        from app.scheduler.prediction_jobs import run_prediction_job
        from app.scheduler.optimization_jobs import run_optimization_job
        from app.scheduler.intelligence_metadata_jobs import (
            compute_health_scores_job,
            compute_risk_scores_job,
            compute_security_scores_job,
            compute_usage_trends_job,
            detect_shadow_apis_job,
            compute_compliance_status_job,
            update_predictions_status_job,
            run_all_intelligence_jobs,
        )
        from app.api.deps import get_security_service, get_compliance_service
        from app.db.repositories.gateway_repository import GatewayRepository
        
        # Setup API discovery job - single job that discovers all connected gateways dynamically
        gateway_repo = GatewayRepository()
        setup_api_discovery_jobs(scheduler, gateway_repo)
        
        # Setup transactional logs collection job - single job that processes all connected gateways dynamically
        # Note: Metrics are now aggregated from transactional logs, not collected separately
        setup_logs_metrics_collection_jobs(scheduler, gateway_repo)
        
        # Setup security scheduler - registers all 4 security jobs:
        # 1. Security scan (every 1 hour)
        # 2. Automated remediation (every 30 minutes)
        # 3. Remediation verification (every 2 hours)
        # 4. Daily security report (8 AM)
        security_service = get_security_service()
        setup_security_scheduler(scheduler, settings, security_service)
        
        # Setup compliance scheduler - registers all 4 compliance jobs:
        # 1. Daily compliance scan (2 AM)
        # 2. Weekly audit report (Monday 9 AM)
        # 3. Daily posture report (9 AM)
        # 4. Monthly audit reminders (1st at 10 AM)
        compliance_service = get_compliance_service()
        setup_compliance_scheduler(scheduler, settings, compliance_service)
        
        # Add prediction job
        scheduler.add_job(
            run_prediction_job,
            trigger=IntervalTrigger(minutes=settings.PREDICTION_INTERVAL_MINUTES),
            id="prediction_job",
            name="Prediction Generation",
            replace_existing=True,
        )
        logger.info(
            f"Scheduled prediction job: every {settings.PREDICTION_INTERVAL_MINUTES} minutes"
        )
        
        # Add optimization job
        scheduler.add_job(
            run_optimization_job,
            trigger=IntervalTrigger(minutes=settings.OPTIMIZATION_INTERVAL_MINUTES),
            id="optimization_job",
            name="Optimization Analysis",
            replace_existing=True,
        )
        logger.info(
            f"Scheduled optimization job: every {settings.OPTIMIZATION_INTERVAL_MINUTES} minutes"
        )
        
        # ====================================================================
        # Intelligence Metadata Computation Jobs
        # ====================================================================
        
        # Job 1: Compute health scores (every 1 minute - testing)
        scheduler.add_job(
            compute_health_scores_job,
            trigger=IntervalTrigger(minutes=10),
            id="compute_health_scores",
            name="Compute API Health Scores",
            replace_existing=True,
        )
        logger.info("Scheduled health scores computation: every 1 minute")
        
        # Job 2: Compute risk scores (every 1 minute - testing)
        scheduler.add_job(
            compute_risk_scores_job,
            trigger=IntervalTrigger(minutes=10),
            id="compute_risk_scores",
            name="Compute API Risk Scores",
            replace_existing=True,
        )
        logger.info("Scheduled risk scores computation: every 1 minute")
        
        # Job 3: Compute security scores (every 1 minute - testing)
        scheduler.add_job(
            compute_security_scores_job,
            trigger=IntervalTrigger(minutes=10),
            id="compute_security_scores",
            name="Compute API Security Scores",
            replace_existing=True,
        )
        logger.info("Scheduled security scores computation: every 1 minute")
        
        # Job 4: Compute usage trends (every 1 minute - testing)
        scheduler.add_job(
            compute_usage_trends_job,
            trigger=IntervalTrigger(minutes=10),
            id="compute_usage_trends",
            name="Compute API Usage Trends",
            replace_existing=True,
        )
        logger.info("Scheduled usage trends computation: every 1 minute")
        
        # Job 5: Detect shadow APIs (every 1 minute - testing)
        scheduler.add_job(
            detect_shadow_apis_job,
            trigger=IntervalTrigger(minutes=10),
            id="detect_shadow_apis",
            name="Detect Shadow APIs",
            replace_existing=True,
        )
        logger.info("Scheduled shadow API detection: every 1 minute")
        
        # Job 6: Compute compliance status (every 1 minute - testing)
        scheduler.add_job(
            compute_compliance_status_job,
            trigger=IntervalTrigger(minutes=10),
            id="compute_compliance_status",
            name="Compute Compliance Status",
            replace_existing=True,
        )
        logger.info("Scheduled compliance status computation: every 1 minute")
        
        # Job 7: Update predictions status (every 1 minute - testing)
        scheduler.add_job(
            update_predictions_status_job,
            trigger=IntervalTrigger(minutes=10),
            id="update_predictions_status",
            name="Update Predictions Status",
            replace_existing=True,
        )
        logger.info("Scheduled predictions status update: every 1 minute")
        
        logger.info("✅ All intelligence metadata computation jobs scheduled successfully")
        
    except ImportError as e:
        logger.warning(f"Some scheduler jobs not available yet: {e}")
    
    return scheduler


def start_scheduler() -> None:
    """Start the background scheduler."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler is disabled, not starting")
        return
    
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Background scheduler started")


def shutdown_scheduler() -> None:
    """Shutdown the background scheduler."""
    scheduler = get_scheduler()
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler shutdown")

# Made with Bob
