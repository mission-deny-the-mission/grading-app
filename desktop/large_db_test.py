"""
Large database performance test.

Creates a test database with 10,000+ submissions and measures:
- Database startup time
- Query performance
- Export/import performance

Usage:
    python desktop/large_db_test.py
"""

import logging
import sys
import time
from pathlib import Path
import os
from datetime import datetime, timedelta
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_test_database():
    """Setup test database with large dataset."""
    # Set database URL
    if sys.platform == 'win32':
        user_data_dir = Path(os.getenv('APPDATA')) / 'GradingApp'
    elif sys.platform == 'darwin':
        user_data_dir = Path.home() / 'Library' / 'Application Support' / 'GradingApp'
    else:
        user_data_dir = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'GradingApp'

    user_data_dir.mkdir(parents=True, exist_ok=True)
    db_path = user_data_dir / 'grading_large_test.db'

    # Remove existing test database
    if db_path.exists():
        logger.info(f"Removing existing test database: {db_path}")
        db_path.unlink()

    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'

    # Add parent directory to path
    parent_dir = Path(__file__).parent.parent.resolve()
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    from app import app
    from models import db, Batch, Job

    with app.app_context():
        db.create_all()

    return app, db_path


def create_test_data(app, num_submissions=10000):
    """Create test data with specified number of submissions."""
    from models import db, Batch, Job

    logger.info(f"Creating test data with {num_submissions} submissions...")

    with app.app_context():
        # Create batches (100 batches with ~100 submissions each)
        num_batches = 100
        submissions_per_batch = num_submissions // num_batches

        start_time = time.time()

        for batch_num in range(num_batches):
            # Create batch
            batch = Batch(
                name=f"Test Batch {batch_num + 1}",
                provider="openrouter",
                model="test-model",
                created_at=datetime.now() - timedelta(days=random.randint(0, 365))
            )
            db.session.add(batch)
            db.session.flush()  # Get batch ID

            # Create submissions for this batch
            for job_num in range(submissions_per_batch):
                job = Job(
                    batch_id=batch.id,
                    filename=f"submission_{batch_num}_{job_num}.pdf",
                    status=random.choice(['pending', 'processing', 'completed', 'failed']),
                    created_at=datetime.now() - timedelta(days=random.randint(0, 365)),
                    result=f"Test result for submission {job_num}" if random.random() > 0.3 else None
                )
                db.session.add(job)

            # Commit every batch to avoid memory issues
            db.session.commit()

            if (batch_num + 1) % 10 == 0:
                elapsed = time.time() - start_time
                logger.info(f"  Created {(batch_num + 1) * submissions_per_batch} submissions ({elapsed:.1f}s)")

        elapsed = time.time() - start_time
        logger.info(f"✓ Created {num_submissions} submissions in {elapsed:.2f}s")

        # Verify count
        total_count = db.session.query(Job).count()
        logger.info(f"✓ Verified database contains {total_count} submissions")

    return elapsed


def test_database_startup(app):
    """Test database startup time with large dataset."""
    logger.info("Testing database startup time...")

    start_time = time.time()

    with app.app_context():
        from models import db, Job
        # Query count to force connection
        count = db.session.query(Job).count()

    elapsed = time.time() - start_time
    logger.info(f"✓ Database startup with {count} submissions: {elapsed:.2f}s")

    return elapsed


def test_query_performance(app):
    """Test query performance on large database."""
    from models import db, Job, Batch

    logger.info("Testing query performance...")

    with app.app_context():
        # Test 1: Count all jobs
        start_time = time.time()
        count = db.session.query(Job).count()
        elapsed = time.time() - start_time
        logger.info(f"  Count query:          {elapsed:.3f}s ({count} rows)")

        # Test 2: Get recent jobs (limit 100)
        start_time = time.time()
        recent_jobs = db.session.query(Job).order_by(Job.created_at.desc()).limit(100).all()
        elapsed = time.time() - start_time
        logger.info(f"  Recent jobs (100):    {elapsed:.3f}s")

        # Test 3: Filter by status
        start_time = time.time()
        completed = db.session.query(Job).filter_by(status='completed').count()
        elapsed = time.time() - start_time
        logger.info(f"  Status filter:        {elapsed:.3f}s ({completed} completed)")

        # Test 4: Join with batches
        start_time = time.time()
        results = db.session.query(Job, Batch).join(Batch).limit(100).all()
        elapsed = time.time() - start_time
        logger.info(f"  Join query (100):     {elapsed:.3f}s")

    logger.info("✓ Query performance tests complete")


def test_export_import(app, db_path):
    """Test export/import with large database."""
    from desktop.data_export import DataExporter
    from desktop.app_wrapper import get_user_data_dir

    logger.info("Testing export/import performance...")

    # Create exporter
    exporter = DataExporter(app, get_user_data_dir())

    # Test export
    logger.info("  Exporting database...")
    start_time = time.time()
    export_path = exporter.export_all_data()
    export_time = time.time() - start_time
    logger.info(f"✓ Export completed in {export_time:.2f}s")
    logger.info(f"  Export file: {export_path}")

    # Check export size
    export_size_mb = export_path.stat().st_size / (1024 * 1024)
    logger.info(f"  Export size: {export_size_mb:.1f} MB")

    # Note: Import test would require creating a new database
    # Skipping for now to keep test simple
    logger.info("  (Import test skipped - would require fresh database)")


def main():
    """Run large database performance tests."""
    logger.info("=" * 60)
    logger.info("Large Database Performance Test")
    logger.info("=" * 60)
    logger.info("")

    # Setup test database
    logger.info("Setting up test database...")
    app, db_path = setup_test_database()
    logger.info(f"✓ Test database: {db_path}")
    logger.info("")

    # Create test data
    create_time = create_test_data(app, num_submissions=10000)
    logger.info("")

    # Test database startup
    startup_time = test_database_startup(app)
    logger.info("")

    # Test query performance
    test_query_performance(app)
    logger.info("")

    # Test export
    test_export_import(app, db_path)
    logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("Performance Summary")
    logger.info("=" * 60)
    logger.info("")
    logger.info(f"Data creation:         {create_time:.2f}s (10,000 submissions)")
    logger.info(f"Database startup:      {startup_time:.2f}s")
    logger.info("")

    # Check against targets
    startup_target = 10.0
    if startup_time < startup_target:
        logger.info(f"✓ Startup time:        {startup_time:.2f}s < {startup_target}s (PASS)")
    else:
        logger.warning(f"✗ Startup time:        {startup_time:.2f}s >= {startup_target}s (FAIL)")

    logger.info("")
    logger.info(f"Test database location: {db_path}")
    logger.info("(You can delete this file when done testing)")
    logger.info("")

    return 0


if __name__ == '__main__':
    sys.exit(main())
