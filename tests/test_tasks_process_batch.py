"""
Process batch task branch coverage: cannot start, no pending jobs, and queuing jobs.
"""

from unittest.mock import patch, ANY


def test_process_batch_cannot_start(app):
    from models import db, JobBatch
    from tasks import process_batch

    with app.app_context():
        # No jobs, status draft -> can_start requires jobs > 0, so False
        batch = JobBatch(batch_name='Empty', status='draft')
        db.session.add(batch)
        db.session.commit()
        assert process_batch.run(batch.id) is False


def test_process_batch_no_pending_jobs(app):
    from models import db, JobBatch, GradingJob
    from tasks import process_batch

    with app.app_context():
        batch = JobBatch(batch_name='NoPending', status='draft')
        db.session.add(batch)
        db.session.commit()
        # Add a completed job so pending list is empty
        job = GradingJob(job_name='Done', provider='openrouter', prompt='p', status='completed', batch_id=batch.id)
        db.session.add(job)
        db.session.commit()

        assert process_batch.run(batch.id) is True


@patch('tasks.process_job.apply_async')
def test_process_batch_queues_jobs(mock_apply_async, app):
    from models import db, JobBatch, GradingJob
    from tasks import process_batch

    with app.app_context():
        batch = JobBatch(batch_name='Queue', status='draft')
        db.session.add(batch)
        db.session.commit()
        # Two pending jobs with different priorities
        j1 = GradingJob(job_name='Low', provider='openrouter', prompt='p', status='pending', batch_id=batch.id, priority=1)
        j2 = GradingJob(job_name='High', provider='openrouter', prompt='p', status='pending', batch_id=batch.id, priority=9)
        db.session.add_all([j1, j2])
        db.session.commit()

        assert process_batch.run(batch.id) is True

    # Expect two calls, with countdown 0 and 5 in priority order
    # Verify at least two enqueues, and that 0 and 5 countdowns were used
    assert mock_apply_async.call_count >= 2
    mock_apply_async.assert_any_call(args=[ANY], countdown=0)
    mock_apply_async.assert_any_call(args=[ANY], countdown=5)

