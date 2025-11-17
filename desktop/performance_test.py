"""
Performance testing script for desktop application.

Measures:
- Flask startup time
- Database initialization time
- Window creation time
- Total startup time

Performance targets (from SC-004):
- Startup time: <10 seconds
- Idle RAM: <500MB
- Active RAM: <1GB

Usage:
    python desktop/performance_test.py
"""

import logging
import sys
import time
from pathlib import Path
import os

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def measure_time(func, description):
    """Measure execution time of a function."""
    start_time = time.time()
    try:
        result = func()
        elapsed = time.time() - start_time
        logger.info(f"✓ {description}: {elapsed:.2f}s")
        return elapsed, result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"✗ {description} failed after {elapsed:.2f}s: {e}")
        return elapsed, None


def test_flask_import():
    """Measure time to import Flask app."""
    def import_app():
        # Set database URL before import
        if sys.platform == 'win32':
            user_data_dir = Path(os.getenv('APPDATA')) / 'GradingApp'
        elif sys.platform == 'darwin':
            user_data_dir = Path.home() / 'Library' / 'Application Support' / 'GradingApp'
        else:
            user_data_dir = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'GradingApp'

        user_data_dir.mkdir(parents=True, exist_ok=True)
        db_path = user_data_dir / 'grading_test.db'
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'

        # Add parent directory to path
        parent_dir = Path(__file__).parent.parent.resolve()
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        from app import app
        return app

    return measure_time(import_app, "Flask app import")


def test_database_init(app):
    """Measure time to initialize database."""
    def init_db():
        with app.app_context():
            from models import db
            db.create_all()
        return True

    return measure_time(init_db, "Database initialization")


def test_desktop_wrapper_config(app):
    """Measure time to configure app for desktop."""
    def configure():
        from desktop.app_wrapper import configure_app_for_desktop
        configure_app_for_desktop(app)
        return True

    return measure_time(configure, "Desktop app configuration")


def test_get_free_port():
    """Measure time to get free port."""
    def get_port():
        from desktop.app_wrapper import get_free_port
        return get_free_port()

    return measure_time(get_port, "Get free port")


def get_memory_usage():
    """Get current process memory usage in MB."""
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        return mem_info.rss / (1024 * 1024)  # Convert to MB
    except ImportError:
        logger.warning("psutil not available, cannot measure memory usage")
        return None


def main():
    """Run all performance tests."""
    logger.info("=" * 60)
    logger.info("Desktop Application Performance Test")
    logger.info("=" * 60)
    logger.info("")

    # Record start time
    total_start = time.time()

    # Get initial memory
    initial_mem = get_memory_usage()
    if initial_mem:
        logger.info(f"Initial memory: {initial_mem:.1f} MB")
        logger.info("")

    # Test 1: Flask import
    flask_time, app = test_flask_import()
    if not app:
        logger.error("Flask import failed, aborting tests")
        return 1

    # Test 2: Database initialization
    db_time, _ = test_database_init(app)

    # Test 3: Desktop configuration
    config_time, _ = test_desktop_wrapper_config(app)

    # Test 4: Port allocation
    port_time, port = test_get_free_port()

    # Calculate total time
    total_time = time.time() - total_start

    # Get final memory
    final_mem = get_memory_usage()

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Performance Summary")
    logger.info("=" * 60)
    logger.info("")
    logger.info(f"Flask import:          {flask_time:6.2f}s")
    logger.info(f"Database init:         {db_time:6.2f}s")
    logger.info(f"Desktop config:        {config_time:6.2f}s")
    logger.info(f"Port allocation:       {port_time:6.2f}s")
    logger.info("-" * 60)
    logger.info(f"Total startup time:    {total_time:6.2f}s")
    logger.info("")

    if final_mem and initial_mem:
        mem_used = final_mem - initial_mem
        logger.info(f"Memory usage:          {final_mem:.1f} MB (+{mem_used:.1f} MB)")
        logger.info("")

    # Check against performance targets
    logger.info("Performance Targets (SC-004):")
    logger.info("-" * 60)

    # Startup time target: <10 seconds
    startup_target = 10.0
    if total_time < startup_target:
        logger.info(f"✓ Startup time:        {total_time:.2f}s < {startup_target}s (PASS)")
    else:
        logger.warning(f"✗ Startup time:        {total_time:.2f}s >= {startup_target}s (FAIL)")

    # Idle RAM target: <500MB
    if final_mem:
        idle_target = 500.0
        if final_mem < idle_target:
            logger.info(f"✓ Idle RAM:            {final_mem:.1f} MB < {idle_target} MB (PASS)")
        else:
            logger.warning(f"✗ Idle RAM:            {final_mem:.1f} MB >= {idle_target} MB (FAIL)")

    logger.info("")
    logger.info("=" * 60)

    # Note about window creation (not tested here as it requires GUI)
    logger.info("")
    logger.info("Note: Window creation time not measured (requires GUI environment)")
    logger.info("      Estimate window creation adds ~1-2s to total startup")
    logger.info("")

    return 0


if __name__ == '__main__':
    sys.exit(main())
