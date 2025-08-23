"""
More API route tests to push overall coverage beyond 80%.
"""

import io
import json
from unittest.mock import patch, MagicMock

import pytest


class TestBatchTemplates:
    def test_batch_templates_crud(self, client):
        # Create
        resp = client.post('/api/batch-templates', json={
            'name': 'Essay Template',
            'description': 'Default essay grading',
            'category': 'essay',
            'default_settings': {'provider': 'openrouter'},
            'job_structure': {},
            'processing_rules': {},
            'is_public': True,
            'created_by': 'tester'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        template_id = data['template']['id']

        # List
        resp = client.get('/api/batch-templates')
        assert resp.status_code == 200
        lst = json.loads(resp.data)
        assert lst['success'] is True and isinstance(lst['templates'], list)

        # Get
        resp = client.get(f'/api/batch-templates/{template_id}')
        assert resp.status_code == 200
        got = json.loads(resp.data)
        assert got['success'] is True and got['template']['name'] == 'Essay Template'


class TestSavedConfigsDetailUpdate:
    def test_saved_prompt_get_and_update(self, client):
        # Create prompt first
        resp = client.post('/api/saved-prompts', json={
            'name': 'P1',
            'description': 'd',
            'category': 'c',
            'prompt_text': 'Please grade.'
        })
        assert resp.status_code == 200
        pid = json.loads(resp.data)['prompt']['id']

        # Get
        resp = client.get(f'/api/saved-prompts/{pid}')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True and data['prompt']['id'] == pid

        # Update
        resp = client.put(f'/api/saved-prompts/{pid}', json={'name': 'P1-updated'})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True and data['prompt']['name'] == 'P1-updated'

    def test_saved_marking_scheme_get_and_update(self, client):
        # Create via JSON path
        resp = client.post('/api/saved-marking-schemes', json={
            'name': 'Scheme A',
            'description': 'desc',
            'category': 'essay',
            'content': 'GRADING RUBRIC\n1. Content\n2. Structure'
        })
        assert resp.status_code == 200
        sid = json.loads(resp.data)['scheme']['id']

        # Get
        resp = client.get(f'/api/saved-marking-schemes/{sid}')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True and data['scheme']['id'] == sid

        # Update
        resp = client.put(f'/api/saved-marking-schemes/{sid}', json={'name': 'Scheme B'})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True and data['scheme']['name'] == 'Scheme B'


class TestBatchOps:
    def test_duplicate_and_archive_batch(self, client, app):
        # Create a batch via model to get id
        with app.app_context():
            from models import JobBatch, db
            batch = JobBatch(batch_name='Original Batch')
            db.session.add(batch)
            db.session.commit()
            bid = batch.id

        # Duplicate
        resp = client.post(f'/api/batches/{bid}/duplicate', json={'new_name': 'Original Batch (Copy)'})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True and data['new_batch']['batch_name'].endswith('(Copy)')

        # Archive
        resp = client.post(f'/api/batches/{bid}/archive')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_batch_jobs_and_export(self, client, app, tmp_path):
        with app.app_context():
            from models import JobBatch, GradingJob, Submission, db
            batch = JobBatch(batch_name='Batch X')
            db.session.add(batch)
            db.session.commit()
            # Add one job
            job = GradingJob(job_name='Job X', provider='openrouter', prompt='p', batch_id=batch.id)
            db.session.add(job)
            db.session.commit()
            # Add a completed submission with grade so export has content
            # Create a dummy file in uploads if needed is not required for export
            sub = Submission(
                job_id=job.id,
                original_filename='doc.txt',
                filename='doc.txt',
                file_type='txt',
                status='completed',
                grade='Great job!'
            )
            db.session.add(sub)
            db.session.commit()
            bid = batch.id

        # Jobs list
        resp = client.get(f'/api/batches/{bid}/jobs')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True and data['total_jobs'] >= 1

        # Export
        resp = client.get(f'/api/batches/{bid}/export')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'application/zip'

    def test_available_jobs_endpoint(self, client, app):
        with app.app_context():
            from models import GradingJob, db
            job = GradingJob(job_name='Standalone', provider='openrouter', prompt='p')
            db.session.add(job)
            db.session.commit()
            jid = job.id

        # Create a batch
        from models import JobBatch, db as _db
        with app.app_context():
            batch = JobBatch(batch_name='AvailBatch')
            _db.session.add(batch)
            _db.session.commit()
            bid = batch.id

        resp = client.get(f'/api/batches/{bid}/available-jobs?page=1&per_page=5&search=Stand')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True and any(j['id'] == jid for j in data['available_jobs'])


class TestUploadSuccessPaths:
    def test_upload_lm_studio_success_with_marking_scheme_and_models(self, client, tmp_path):
        # Prepare files
        file_content = b'Hello text contents.'
        scheme_content = b'RUBRIC: 1) Content 2) Structure'

        def fake_post(url, json=None, headers=None, timeout=None):
            fake = MagicMock()
            fake.status_code = 200
            fake.json.return_value = {
                'choices': [{'message': {'content': 'Grade: B+'}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 20}
            }
            return fake

        with patch('utils.llm_providers.requests.post', side_effect=fake_post):
            data = {
                'file': (io.BytesIO(file_content), 'essay.txt'),
                'marking_scheme': (io.BytesIO(scheme_content), 'rubric.txt'),
                'prompt': 'Please grade.',
                'provider': 'lm_studio',
                'customModels[]': ['local-model-A', 'local-model-B']
            }
            resp = client.post('/upload', data=data)
        assert resp.status_code == 200
        payload = json.loads(resp.data)
        # Comparison path because multiple models provided
        assert payload.get('comparison') is True
        assert 'results' in payload and len(payload['results']) >= 1


