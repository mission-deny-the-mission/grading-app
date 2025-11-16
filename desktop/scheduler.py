"""
Periodic task scheduler for desktop application.

Replaces Celery Beat with APScheduler for single-user desktop deployments.
Manages periodic cleanup tasks without requiring Redis infrastructure.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from tasks import cleanup_old_files, cleanup_completed_batches

# Configure logging
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def initialize_scheduler():
    """
    Initialize and configure the periodic task scheduler.

    Adds periodic jobs for maintenance tasks:
    - cleanup_old_files: Removes old uploaded files (24-hour interval)
    - cleanup_completed_batches: Archives old completed batches (6-hour interval)
    """
    try:
        # Add periodic cleanup jobs
        scheduler.add_job(
            cleanup_old_files,
            'interval',
            hours=24,
            id='cleanup_old_files',
            name='Clean up old uploaded files',
            replace_existing=True
        )

        scheduler.add_job(
            cleanup_completed_batches,
            'interval',
            hours=6,
            id='cleanup_completed_batches',
            name='Archive old completed batches',
            replace_existing=True
        )

        logger.info("Scheduler initialized with 2 periodic jobs")

    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")
        raise


def start():
    """
    Start the background scheduler.

    Should be called during application startup after scheduler initialization.
    """
    try:
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started successfully")
        else:
            logger.warning("Scheduler is already running")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise


def stop():
    """
    Stop the background scheduler gracefully.

    Should be called during application shutdown to ensure clean exit.
    Waits for currently executing jobs to complete.
    """
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped successfully")
        else:
            logger.warning("Scheduler is not running")
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")
        raise


# Initialize scheduler on module import
initialize_scheduler()
