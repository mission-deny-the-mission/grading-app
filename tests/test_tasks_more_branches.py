"""
Deeper tasks.py grading loop branches: provider mapping errors and model failures.
"""

from unittest.mock import patch, MagicMock


def test_process_submission_sync_provider_not_found(app, tmp_path):
    from models import db, GradingJob, Submission
    from tasks import process_submission_sync

    with app.app_context():
        job = GradingJob(job_name='Bad Provider', provider='unknown', prompt='p')
        db.session.add(job)
        db.session.commit()

        # Create file in uploads
        upload_folder = app.config['UPLOAD_FOLDER']
        file_name = 'x.txt'
        with open(f"{upload_folder}/{file_name}", 'w') as f:
            f.write('content')

        sub = Submission(job_id=job.id, filename=file_name, original_filename=file_name, file_type='txt', status='pending')
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

    # Should fail early due to unsupported provider mapping
    assert process_submission_sync(sid) is False


def test_process_submission_sync_all_models_fail(app, tmp_path):
    from models import db, GradingJob, Submission
    from tasks import process_submission_sync

    with app.app_context():
        job = GradingJob(job_name='All Fail', provider='lm_studio', prompt='p')
        db.session.add(job)
        db.session.commit()

        # Create file
        upload_folder = app.config['UPLOAD_FOLDER']
        file_name = 'y.txt'
        with open(f"{upload_folder}/{file_name}", 'w') as f:
            f.write('content')

        sub = Submission(job_id=job.id, filename=file_name, original_filename=file_name, file_type='txt', status='pending')
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

    # Make LM Studio return non-200 so result['success'] is False
    fake_resp = MagicMock(status_code=500, text='err')
    with patch('utils.llm_providers.requests.post', return_value=fake_resp):
        assert process_submission_sync(sid) is False


