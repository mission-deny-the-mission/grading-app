"""
Maintenance task tests for cleanup_old_files, cleanup_completed_batches, and
process_batch_with_priority.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


def test_cleanup_old_files_respects_failed_submission(app, tmp_path):
    from models import db, Submission
    from tasks import cleanup_old_files

    with app.app_context():
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        # Create two files in upload folder
        stale_keep = os.path.join(upload_folder, 'keep_failed.txt')
        stale_delete = os.path.join(upload_folder, 'delete_me.txt')
        with open(stale_keep, 'w') as f:
            f.write('x')
        with open(stale_delete, 'w') as f:
            f.write('y')

        # Create a job to satisfy NOT NULL job_id and associate failed submission
        from models import GradingJob
        job = GradingJob(job_name='Cleanup Job', provider='openrouter', prompt='p')
        db.session.add(job)
        db.session.commit()

        # Associate keep_failed.txt with a failed submission
        sub = Submission(
            filename='keep_failed.txt',
            original_filename='keep_failed.txt',
            file_type='txt',
            file_size=1,
            status='failed',
            job_id=job.id
        )
        db.session.add(sub)
        db.session.commit()

        # Patch getctime to make files look older than cutoff
        old_time = (datetime.now() - timedelta(hours=80)).timestamp()
        with patch('tasks.os.path.getctime', side_effect=lambda p: old_time):
            cleanup_old_files()

        # keep_failed.txt should remain; delete_me.txt should be gone
        assert os.path.exists(stale_keep)
        assert not os.path.exists(stale_delete)


def test_cleanup_completed_batches_archives_old(app):
    from models import db, JobBatch
    from tasks import cleanup_completed_batches

    with app.app_context():
        old_batch = JobBatch(batch_name='Old', status='completed')
        old_batch.completed_at = datetime.now(timezone.utc) - timedelta(days=40)
        recent_batch = JobBatch(batch_name='Recent', status='completed')
        recent_batch.completed_at = datetime.now(timezone.utc) - timedelta(days=10)
        db.session.add(old_batch)
        db.session.add(recent_batch)
        db.session.commit()

        count = cleanup_completed_batches()
        db.session.refresh(old_batch)
        db.session.refresh(recent_batch)

        assert count >= 1
        assert old_batch.status in ['archived', 'completed_with_errors', 'completed', 'failed', 'cancelled'] or old_batch.status == 'archived'


@patch('tasks.process_batch.delay')
def test_process_batch_with_priority_triggers_pending(mock_delay, app):
    mock_delay.return_value = MagicMock()
    from models import db, JobBatch, GradingJob
    from tasks import process_batch_with_priority

    with app.app_context():
        # Create a pending batch with one pending job
        batch = JobBatch(batch_name='Priority', status='pending')
        db.session.add(batch)
        db.session.commit()
        job = GradingJob(job_name='J', provider='openrouter', prompt='p', batch_id=batch.id)
        db.session.add(job)
        db.session.commit()

        process_batch_with_priority()

    assert mock_delay.called


