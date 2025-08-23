"""
Additional API route tests to increase coverage for routes.api and routes.upload.
"""

import io
import json
from unittest.mock import patch, MagicMock

import pytest


class TestApiModels:
    def test_get_models_unknown_provider(self, client):
        resp = client.get('/api/models/unknown')
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'Unknown provider' in data['error']


class TestApiJobsExports:
    def test_export_job_results_zip(self, client, app, sample_job, sample_submission, tmp_path):
        # mark submission as completed with a grade to include in ZIP
        with app.app_context():
            from models import db
            sample_submission.status = 'completed'
            sample_submission.grade = 'Grade: A'
            db.session.commit()

        resp = client.get(f'/api/jobs/{sample_job.id}/export')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'application/zip'


class TestApiJobActions:
    @patch('tasks.process_job.delay')
    def test_trigger_job_processing_success(self, mock_delay, client, sample_job):
        mock_delay.return_value = MagicMock(id='task123')
        resp = client.post(f'/api/jobs/{sample_job.id}/process')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True and data['task_id'] == 'task123'

    def test_retry_failed_submissions_no_failed(self, client, sample_job):
        # sample_job has no failed submissions in fixture
        resp = client.post(f'/api/jobs/{sample_job.id}/retry')
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data['success'] is False

    @patch('tasks.process_job.delay')
    def test_retry_submission_success_path(self, mock_delay, client, app, sample_job, sample_submission, tmp_path):
        mock_delay.return_value = MagicMock(id='task123')
        # create a real file so tasks code finds it
        file_path = tmp_path / 'test_document.txt'
        file_path.write_text('hello world')
        with app.app_context():
            from models import db
            # Ensure submission file points to the path we created
            sample_submission.filename = file_path.name
            db.session.commit()

        # Allow retry
        with app.app_context():
            sample_submission.status = 'failed'
            from models import db
            db.session.commit()

        resp = client.post(f'/api/submissions/{sample_submission.id}/retry')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True


class TestUploadRoutes:
    def test_upload_marking_scheme_missing_file(self, client):
        resp = client.post('/upload_marking_scheme', data={})
        assert resp.status_code == 400

    def test_upload_marking_scheme_unsupported_type(self, client):
        data = {
            'marking_scheme': (io.BytesIO(b'invalid'), 'file.png')
        }
        resp = client.post('/upload_marking_scheme', data=data)
        assert resp.status_code == 400

    def test_upload_unsupported_file_type(self, client):
        data = {
            'file': (io.BytesIO(b'data'), 'file.png'),
            'prompt': 'p',
            'provider': 'openrouter'
        }
        resp = client.post('/upload', data=data)
        assert resp.status_code == 400

    def test_upload_provider_unknown(self, client):
        data = {
            'file': (io.BytesIO(b'hello'), 'file.txt'),
            'prompt': 'p',
            'provider': 'unknown'
        }
        resp = client.post('/upload', data=data)
        assert resp.status_code == 400

    @patch.dict('os.environ', {'OPENROUTER_API_KEY': ''}, clear=False)
    def test_upload_missing_openrouter_key(self, client):
        data = {
            'file': (io.BytesIO(b'hello'), 'file.txt'),
            'prompt': 'p',
            'provider': 'openrouter'
        }
        resp = client.post('/upload', data=data)
        assert resp.status_code == 400


