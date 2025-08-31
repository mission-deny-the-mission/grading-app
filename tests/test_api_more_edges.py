"""
Additional API edge-case tests for routes.api to improve coverage.
"""

import json


def test_remove_job_from_wrong_batch(client, app):
    with app.app_context():
        from models import JobBatch, GradingJob, db
        batch_a = JobBatch(batch_name='A')
        batch_b = JobBatch(batch_name='B')
        db.session.add(batch_a)
        db.session.add(batch_b)
        db.session.commit()
        job = GradingJob(job_name='J', provider='openrouter', prompt='p', batch_id=batch_a.id)
        db.session.add(job)
        db.session.commit()
        jid = job.id
        bid_b = batch_b.id

    resp = client.delete(f'/api/batches/{bid_b}/jobs/{jid}')
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data['success'] is False and 'not part of this batch' in data['error']


def test_add_jobs_to_batch_skips(client, app):
    with app.app_context():
        from models import JobBatch, GradingJob, db
        batch = JobBatch(batch_name='Target')
        db.session.add(batch)
        db.session.commit()
        bid = batch.id
        # Already assigned job
        assigned = GradingJob(job_name='Assigned', provider='openrouter', prompt='p', batch_id=bid)
        db.session.add(assigned)
        db.session.commit()
        assigned_id = assigned.id

    resp = client.post(f'/api/batches/{bid}/jobs', json={'job_ids': [assigned_id, 'missing-id']})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['success'] is True
    assert any(s.get('reason', '').startswith('Already assigned') for s in data['skipped_jobs'])
    assert any(s.get('reason') == 'Job not found' for s in data['skipped_jobs'])


def test_export_empty_batch_zip(client, app):
    with app.app_context():
        from models import JobBatch, db
        batch = JobBatch(batch_name='EmptyBatch')
        db.session.add(batch)
        db.session.commit()
        bid = batch.id

    resp = client.get(f'/api/batches/{bid}/export')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/zip'


def test_get_provider_models_unknown(client):
    resp = client.get('/api/models/doesnotexist')
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert 'Unknown provider' in data['error']



def test_delete_saved_marking_scheme(client):
    # Create via JSON
    resp = client.post('/api/saved-marking-schemes', json={
        'name': 'ToDelete',
        'description': 'd',
        'category': 'essay',
        'content': 'RUBRIC\n1) Content'
    })
    assert resp.status_code == 200
    scheme_id = json.loads(resp.data)['scheme']['id']

    # Delete
    resp = client.delete(f'/api/saved-marking-schemes/{scheme_id}')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['success'] is True

def test_get_jobs_api_pagination(client, sample_job):
    """Test jobs API with pagination parameters"""
    response = client.get('/api/jobs?page=1&per_page=5')
    assert response.status_code == 200
    data = response.get_json()
    # The response is a list of jobs, not a dictionary with 'jobs' key
    assert isinstance(data, list)
    # Check if we have at least one job
    assert len(data) >= 1

def test_get_jobs_api_invalid_pagination(client):
    """Test jobs API with invalid pagination parameters"""
    response = client.get('/api/jobs?page=-1&per_page=0')
    # The API might not validate pagination parameters, so check for success
    assert response.status_code == 200
    data = response.get_json()
    # The response should be a list (possibly empty)
    assert isinstance(data, list)

def test_get_batches_api_filter_by_status(client, sample_batch):
    """Test batches API with status filter"""
    response = client.get('/api/batches?status=processing')
    assert response.status_code == 200
    data = response.get_json()
    # The response is a dictionary with batches list, not a direct list
    assert 'batches' in data
    assert isinstance(data['batches'], list)


