"""
Unit tests for Flask routes and API endpoints.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestMainRoutes:
    """Test cases for main application routes."""
    
    def test_index_route(self, client):
        """Test the index route."""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_jobs_route(self, client):
        """Test the jobs listing route."""
        response = client.get('/jobs')
        assert response.status_code == 200
    
    def test_batches_route(self, client):
        """Test the batches listing route."""
        response = client.get('/batches')
        assert response.status_code == 200
    
    def test_config_route(self, client):
        """Test the configuration route."""
        response = client.get('/config')
        assert response.status_code == 200
    
    def test_saved_configurations_route(self, client):
        """Test the saved configurations route."""
        response = client.get('/saved-configurations')
        assert response.status_code == 200


class TestAPIEndpoints:
    """Test cases for API endpoints."""
    
    @pytest.mark.api
    
    def test_get_jobs_api(self, client, sample_job):
        """Test getting jobs via API."""
        response = client.get('/api/jobs')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 1
        
        job_data = data[0]
        assert 'id' in job_data
        assert 'job_name' in job_data
        assert 'status' in job_data
        assert 'progress' in job_data
    
    def test_get_job_details_api(self, client, sample_job):
        """Test getting job details via API."""
        response = client.get(f'/api/jobs/{sample_job.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == sample_job.id
        assert data['job_name'] == sample_job.job_name
        assert data['status'] == sample_job.status
    
    def test_get_nonexistent_job_api(self, client):
        """Test getting a job that doesn't exist."""
        response = client.get('/api/jobs/nonexistent-id')
        assert response.status_code == 404
    
    def test_get_job_submissions_api(self, client, sample_job, sample_submission):
        """Test getting job submissions via API."""
        response = client.get(f'/api/jobs/{sample_job.id}/submissions')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 1
        
        submission_data = data[0]
        assert 'id' in submission_data
        assert 'original_filename' in submission_data
        assert 'status' in submission_data
    
    def test_get_submission_details_api(self, client, sample_submission):
        """Test getting submission details via API."""
        response = client.get(f'/api/submissions/{sample_submission.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == sample_submission.id
        assert data['original_filename'] == sample_submission.original_filename
        assert data['status'] == sample_submission.status
    
    def test_get_batches_api(self, client, sample_batch):
        """Test getting batches via API."""
        response = client.get('/api/batches')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'batches' in data
        assert isinstance(data['batches'], list)
        assert len(data['batches']) >= 1
        
        batch_data = data['batches'][0]
        assert 'id' in batch_data
        assert 'batch_name' in batch_data
        assert 'status' in batch_data
    
    def test_get_batch_details_api(self, client, sample_batch):
        """Test getting batch details via API."""
        response = client.get(f'/api/batches/{sample_batch.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'batch' in data
        assert data['batch']['id'] == sample_batch.id
        assert data['batch']['batch_name'] == sample_batch.batch_name
        assert data['batch']['status'] == sample_batch.status
    
    def test_get_models_api(self, client):
        """Test getting available models via API."""
        response = client.get('/api/models')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'openrouter' in data
        assert 'claude' in data
        assert 'lm_studio' in data
    
    def test_get_models_by_provider_api(self, client):
        """Test getting models for a specific provider."""
        response = client.get('/api/models/openrouter')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'popular' in data
        assert 'default' in data
    
    def test_get_saved_prompts_api(self, client):
        """Test getting saved prompts via API."""
        response = client.get('/api/saved-prompts')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'prompts' in data
        assert isinstance(data['prompts'], list)
    
    def test_get_saved_marking_schemes_api(self, client):
        """Test getting saved marking schemes via API."""
        response = client.get('/api/saved-marking-schemes')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'schemes' in data
        assert isinstance(data['schemes'], list)


class TestFileUpload:
    """Test cases for file upload functionality."""
    
    @pytest.mark.api
    
    @patch('app.process_job.delay')
    def test_single_file_upload(self, mock_process_job, client, sample_text_file):
        """Test uploading a single file."""
        mock_process_job.return_value = MagicMock(id='test-task-id')
        
        with open(sample_text_file, 'rb') as f:
            response = client.post('/upload', data={
                'file': (f, 'test_document.txt'),
                'prompt': 'Please grade this document.',
                'provider': 'openrouter',
                'customModel': 'anthropic/claude-3-5-sonnet-20241022'
            })
        
        # The upload will fail because API keys are not configured in test environment
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'API key' in data['error']
    
    @patch('app.process_job.delay')
    def test_file_upload_with_marking_scheme(self, mock_process_job, client, sample_text_file):
        """Test uploading a file with a marking scheme."""
        mock_process_job.return_value = MagicMock(id='test-task-id')
        
        # Create marking scheme content
        marking_scheme_content = "Test marking scheme content"
        
        with open(sample_text_file, 'rb') as f:
            response = client.post('/upload', data={
                'file': (f, 'test_document.txt'),
                'prompt': 'Please grade this document.',
                'provider': 'openrouter',
                'customModel': 'anthropic/claude-3-5-sonnet-20241022',
                'marking_scheme': (BytesIO(marking_scheme_content.encode()), 'rubric.txt')
            })
        
        # The upload will fail because API keys are not configured in test environment
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'API key' in data['error']
    
    def test_file_upload_invalid_file(self, client):
        """Test uploading an invalid file."""
        response = client.post('/upload', data={
            'file': (BytesIO(b'invalid content'), ''),
            'prompt': 'Please grade this document.',
            'provider': 'openrouter'
        })
        
        assert response.status_code == 400
    
    def test_file_upload_missing_required_fields(self, client, sample_text_file):
        """Test uploading a file with missing required fields."""
        with open(sample_text_file, 'rb') as f:
            response = client.post('/upload', data={
                'file': (f, 'test_document.txt')
                # Missing prompt and provider
            })
        
        assert response.status_code == 400
    
    @patch('app.process_batch.delay')
    def test_bulk_upload(self, mock_process_batch, client, sample_text_file):
        """Test bulk file upload."""
        mock_process_batch.return_value = MagicMock(id='test-task-id')
        
        with open(sample_text_file, 'rb') as f:
            response = client.post('/upload_bulk', data={
                'files[]': (f, 'test_document.txt'),
                'job_name': 'Test Bulk Job',
                'description': 'A test bulk job',
                'provider': 'openrouter',
                'customModel': 'anthropic/claude-3-5-sonnet-20241022',
                'prompt': 'Please grade these documents.'
            })
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'job_id' in data


class TestJobManagement:
    """Test cases for job management functionality."""
    
    @pytest.mark.api
    
    @patch('app.process_job.delay')
    def test_create_job(self, mock_process_job, client):
        """Test creating a new job."""
        mock_process_job.return_value = MagicMock(id='test-task-id')
        
        response = client.post('/create_job', json={
            'job_name': 'Test Job',
            'description': 'A test job',
            'provider': 'openrouter',
            'customModel': 'anthropic/claude-3-5-sonnet-20241022',
            'prompt': 'Please grade this document.',
            'priority': 5,
            'temperature': 0.7,
            'max_tokens': 2000
        })
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'job_id' in data
    
    def test_create_job_missing_fields(self, client):
        """Test creating a job with missing required fields."""
        response = client.post('/create_job', json={
            'job_name': 'Test Job'
            # Missing required fields
        })
        
        assert response.status_code == 400
    
    @patch('app.process_job.delay')
    def test_retry_job(self, mock_process_job, client, sample_job):
        """Test retrying a job."""
        mock_process_job.return_value = MagicMock(id='test-task-id')
        
        # Create a failed submission
        from models import db, Submission
        with client.application.app_context():
            submission = Submission(
                job_id=sample_job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                status="failed",
                error_message="Test error"
            )
            db.session.add(submission)
            db.session.commit()
        
        response = client.post(f'/api/jobs/{sample_job.id}/retry')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
    
    def test_retry_nonexistent_job(self, client):
        """Test retrying a job that doesn't exist."""
        response = client.post('/api/jobs/nonexistent-id/retry')
        assert response.status_code == 404


class TestBatchManagement:
    """Test cases for batch management functionality."""
    
    @pytest.mark.api
    
    @patch('app.process_batch.delay')
    def test_create_batch(self, mock_process_batch, client):
        """Test creating a new batch."""
        mock_process_batch.return_value = MagicMock(id='test-task-id')
        
        response = client.post('/create_batch', json={
            'batch_name': 'Test Batch',
            'description': 'A test batch',
            'priority': 5
        })
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'batch_id' in data
    
    @patch('app.pause_batch_processing.delay')
    def test_pause_batch(self, mock_pause_batch, client, sample_batch):
        """Test pausing a batch."""
        mock_pause_batch.return_value = MagicMock(id='test-task-id')
        
        response = client.post(f'/api/batches/{sample_batch.id}/pause')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
    
    @patch('app.resume_batch_processing.delay')
    def test_resume_batch(self, mock_resume_batch, client, sample_batch):
        """Test resuming a batch."""
        mock_resume_batch.return_value = MagicMock(id='test-task-id')
        
        response = client.post(f'/api/batches/{sample_batch.id}/resume')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
    
    @patch('app.cancel_batch_processing.delay')
    def test_cancel_batch(self, mock_cancel_batch, client, sample_batch):
        """Test canceling a batch."""
        mock_cancel_batch.return_value = MagicMock(id='test-task-id')
        
        response = client.post(f'/api/batches/{sample_batch.id}/cancel')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
    
    def test_add_jobs_to_batch(self, client, sample_batch, sample_job):
        """Test adding existing jobs to a batch."""
        response = client.post(f'/api/batches/{sample_batch.id}/jobs', json={
            'job_ids': [sample_job.id]
        })
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'added_jobs' in data
        assert len(data['added_jobs']) == 1
        assert data['added_jobs'][0]['id'] == sample_job.id
    
    def test_add_jobs_to_batch_no_job_ids(self, client, sample_batch):
        """Test adding jobs to batch with no job IDs provided."""
        response = client.post(f'/api/batches/{sample_batch.id}/jobs', json={})
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'No job IDs provided' in data['error']
    
    def test_create_job_in_batch(self, client, sample_batch):
        """Test creating a new job within a batch."""
        response = client.post(f'/api/batches/{sample_batch.id}/jobs/create', json={
            'job_name': 'New Batch Job',
            'description': 'A job created in the batch',
            'provider': 'openrouter',
            'prompt': 'Custom prompt'
        })
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'job' in data
        assert data['job']['job_name'] == 'New Batch Job'
        assert data['job']['description'] == 'A job created in the batch'
        assert data['job']['provider'] == 'openrouter'
        assert data['job']['prompt'] == 'Custom prompt'
    
    def test_create_job_in_batch_no_name(self, client, sample_batch):
        """Test creating a job in batch without job name."""
        response = client.post(f'/api/batches/{sample_batch.id}/jobs/create', json={
            'description': 'A job without name'
        })
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Job name is required' in data['error']
    
    def test_get_available_jobs_for_batch(self, client, sample_batch):
        """Test getting available jobs that can be added to a batch."""
        # Create a standalone job (not in any batch)
        from models import GradingJob, db
        with client.application.app_context():
            standalone_job = GradingJob(
                job_name="Standalone Job",
                provider="openrouter",
                prompt="Test prompt"
            )
            db.session.add(standalone_job)
            db.session.commit()
            standalone_job_id = standalone_job.id
        
        response = client.get(f'/api/batches/{sample_batch.id}/available-jobs')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'available_jobs' in data
        assert 'pagination' in data
        
        # Check that the standalone job is in the available jobs
        job_ids = [job['id'] for job in data['available_jobs']]
        assert standalone_job_id in job_ids
    
    def test_get_batch_settings(self, client, sample_batch):
        """Test getting batch settings summary."""
        response = client.get(f'/api/batches/{sample_batch.id}/settings')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'settings' in data
        settings = data['settings']
        assert 'can_add_jobs' in settings
        assert 'batch_name' in settings
        assert 'batch_status' in settings
    
    def test_remove_job_from_batch(self, client, sample_batch):
        """Test removing a job from a batch."""
        # First create and add a job to the batch
        from models import GradingJob, db
        with client.application.app_context():
            job = GradingJob(
                job_name="Job to Remove",
                provider="openrouter",
                prompt="Test prompt"
            )
            db.session.add(job)
            db.session.commit()
            
            # Add job to batch
            sample_batch = db.session.merge(sample_batch)
            sample_batch.add_job(job)
            job_id = job.id
        
        # Remove job from batch
        response = client.delete(f'/api/batches/{sample_batch.id}/jobs/{job_id}')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'message' in data
    
    def test_batch_analytics(self, client, sample_batch):
        """Test getting batch analytics."""
        response = client.get(f'/api/batches/{sample_batch.id}/analytics')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'analytics' in data
        analytics = data['analytics']
        assert 'overview' in analytics
        assert 'job_status_breakdown' in analytics
        assert 'provider_breakdown' in analytics
        assert 'timeline' in analytics


class TestSavedConfigurations:
    """Test cases for saved configurations functionality."""
    
    @pytest.mark.api
    
    def test_save_prompt(self, client):
        """Test saving a prompt."""
        response = client.post('/api/saved-prompts', json={
            'name': 'Test Prompt',
            'description': 'A test prompt',
            'category': 'essay',
            'prompt_text': 'Please grade this essay.'
        })
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'prompt' in data
        assert 'id' in data['prompt']
    
    def test_save_marking_scheme(self, client):
        """Test saving a marking scheme."""
        response = client.post('/api/saved-marking-schemes', json={
            'name': 'Test Scheme',
            'description': 'A test marking scheme',
            'category': 'essay',
            'content': 'Test marking scheme content'
        })
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'scheme' in data
        assert 'id' in data['scheme']
    
    def test_delete_saved_prompt(self, client):
        """Test deleting a saved prompt."""
        # First create a prompt
        create_response = client.post('/api/saved-prompts', json={
            'name': 'Test Prompt',
            'description': 'A test prompt',
            'category': 'essay',
            'prompt_text': 'Please grade this essay.'
        })
        
        prompt_data = json.loads(create_response.data)
        prompt_id = prompt_data['prompt']['id']
        
        # Then delete it
        response = client.delete(f'/api/saved-prompts/{prompt_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
    
    def test_delete_saved_marking_scheme(self, client):
        """Test deleting a saved marking scheme."""
        # First create a marking scheme
        create_response = client.post('/api/saved-marking-schemes', json={
            'name': 'Test Scheme',
            'description': 'A test marking scheme',
            'category': 'essay',
            'content': 'Test marking scheme content'
        })
        
        scheme_data = json.loads(create_response.data)
        scheme_id = scheme_data['scheme']['id']
        
        # Then delete it
        response = client.delete(f'/api/saved-marking-schemes/{scheme_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True


class TestErrorHandling:
    """Test cases for error handling."""
    
    @pytest.mark.api
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent-route')
        assert response.status_code == 404
    
    def test_413_error(self, client):
        """Test 413 error handling for large files."""
        # Create a large file content
        large_content = b'x' * (17 * 1024 * 1024)  # 17MB
        
        response = client.post('/upload', data={
            'file': (BytesIO(large_content), 'large_file.txt'),
            'prompt': 'Please grade this document.',
            'provider': 'openrouter'
        })
        
        assert response.status_code == 413
    
    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post('/create_job', 
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
