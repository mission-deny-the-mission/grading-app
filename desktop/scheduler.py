"""
Periodic task scheduler for desktop application.

Replaces Celery Beat with APScheduler for single-user desktop deployments.
Manages periodic cleanup tasks and automatic backups without requiring Redis infrastructure.
"""

import logging
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from tasks import cleanup_old_files, cleanup_completed_batches
from desktop.data_export import export_data
from desktop.settings import Settings

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


def create_automatic_backup():
    """
    Create an automatic backup of the application data.

    Reads database and uploads paths from settings, creates a backup
    in the user_data_dir/backups/ directory with timestamp naming.
    """
    try:
        import sys
        import os

        # Get user data directory
        user_data_dir = Settings._get_user_data_dir()

        # Load settings to get paths
        settings_path = user_data_dir / 'settings.json'
        settings = Settings(settings_path)
        settings.load()

        # Get database and uploads paths
        database_path = settings.get('data.database_path')
        uploads_path = settings.get('data.uploads_path')
        app_version = settings.get('app_version', '0.1.0')

        # Set defaults if not configured
        if not database_path:
            database_path = str(user_data_dir / 'grading.db')

        if not uploads_path:
            uploads_path = str(user_data_dir / 'uploads')

        # Create backups directory
        backups_dir = user_data_dir / 'backups'
        backups_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_filename = f'auto-backup-{timestamp}.zip'
        backup_path = backups_dir / backup_filename

        # Create backup
        logger.info(f"Creating automatic backup: {backup_filename}")
        export_data(
            database_path=database_path,
            uploads_path=uploads_path,
            output_path=str(backup_path),
            app_version=app_version
        )

        logger.info(f"Automatic backup created successfully: {backup_path}")

        # Run cleanup of old backups
        cleanup_old_backups()

    except Exception as e:
        logger.error(f"Failed to create automatic backup: {e}", exc_info=True)


def cleanup_old_backups():
    """
    Delete backups older than the retention period specified in settings.

    Reads retention_days from settings (default 30) and removes backup files
    from user_data_dir/backups/ that are older than this period.
    """
    try:
        # Get user data directory
        user_data_dir = Settings._get_user_data_dir()

        # Load settings to get retention days
        settings_path = user_data_dir / 'settings.json'
        settings = Settings(settings_path)
        settings.load()

        retention_days = settings.get('data.backup_retention_days', 30)

        # Get backups directory
        backups_dir = user_data_dir / 'backups'
        if not backups_dir.exists():
            logger.debug("Backups directory does not exist, skipping cleanup")
            return

        # Calculate cutoff time
        from datetime import timedelta
        cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)

        # Find and delete old backups
        deleted_count = 0
        for backup_file in backups_dir.glob('*.zip'):
            if backup_file.stat().st_mtime < cutoff_time:
                logger.info(f"Deleting old backup: {backup_file.name}")
                backup_file.unlink()
                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old backup(s) older than {retention_days} days")
        else:
            logger.debug(f"No backups older than {retention_days} days found")

    except Exception as e:
        logger.error(f"Failed to cleanup old backups: {e}", exc_info=True)


def schedule_automatic_backup():
    """
    Schedule automatic backup job based on settings.

    Reads backup settings (backups_enabled, backup_frequency) and schedules
    the appropriate APScheduler job. Can be called to update schedule when
    settings change.
    """
    try:
        # Get user data directory
        user_data_dir = Settings._get_user_data_dir()

        # Load settings
        settings_path = user_data_dir / 'settings.json'
        settings = Settings(settings_path)
        settings.load()

        # Check if backups are enabled
        backups_enabled = settings.get('data.backups_enabled', True)
        backup_frequency = settings.get('data.backup_frequency', 'daily')

        # Remove existing backup job if present
        try:
            scheduler.remove_job('automatic_backup')
            logger.debug("Removed existing automatic backup job")
        except:
            pass  # Job doesn't exist yet

        # Schedule new job if enabled and frequency is not 'never'
        if backups_enabled and backup_frequency != 'never':
            if backup_frequency == 'daily':
                # Run daily at 2 AM
                scheduler.add_job(
                    create_automatic_backup,
                    'cron',
                    hour=2,
                    minute=0,
                    id='automatic_backup',
                    name='Create automatic backup',
                    replace_existing=True
                )
                logger.info("Scheduled automatic backups: daily at 2:00 AM")

            elif backup_frequency == 'weekly':
                # Run weekly on Sunday at 2 AM
                scheduler.add_job(
                    create_automatic_backup,
                    'cron',
                    day_of_week='sun',
                    hour=2,
                    minute=0,
                    id='automatic_backup',
                    name='Create automatic backup',
                    replace_existing=True
                )
                logger.info("Scheduled automatic backups: weekly on Sunday at 2:00 AM")

        else:
            logger.info("Automatic backups disabled or set to 'never'")

    except Exception as e:
        logger.error(f"Failed to schedule automatic backup: {e}", exc_info=True)


# Initialize scheduler on module import
initialize_scheduler()
