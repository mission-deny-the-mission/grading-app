# Testing Guide for Document Grading App

This document provides guidelines for properly running tests and avoiding common issues with the grading application.

## Environment Setup

### Prerequisites
- Nix package manager installed
- PostgreSQL and Redis available (handled by Nix shell)

### Proper Development Environment

The grading app uses Nix for reproducible development environments. **Always run tests inside the Nix shell**:

```bash
# Enter the development environment
nix-shell

# Once inside the shell, you can run tests
python3 -m pytest tests/
```

### Avoid These Common Mistakes

❌ **Don't run tests outside Nix shell**:
```bash
# This will fail or cause hanging
python3 -m pytest tests/  # Wrong - missing dependencies
```

❌ **Don't mix Celery workers from different environments**:
```bash
# Don't run Celery workers outside Nix shell
celery -A tasks worker  # Wrong - different Python environment
```

❌ **Don't run trigger scripts during testing**:
```bash
# Don't run this during test sessions
python3 trigger_job.py  # This creates real tasks that can hang
```

## Running Tests

### Single Test Execution
```bash
nix-shell --run "python3 -m pytest tests/test_models.py -v"
```

### Test Coverage
```bash
nix-shell --run "python3 -m pytest --cov=. tests/"
```

### Specific Test Classes
```bash
nix-shell --run "python3 -m pytest tests/test_tasks.py::TestProcessJob -v"
```

## Services Management

### Starting Services for Development
Inside the Nix shell, use the provided aliases:

```bash
nix-shell
# Then inside the shell:
flask-app           # Start Flask application
celery-worker       # Start Celery worker
celery-beat         # Start Celery beat scheduler
start-all           # Start all services at once
```

### Manual Service Control
If you prefer manual control:

```bash
# Start workers with proper configuration
nix-shell --run "celery -A tasks worker --loglevel=info --concurrency=1 --queues=grading,maintenance"
```

### Stopping Services
```bash
# Use the provided script
./stop-services.sh

# Or manually kill processes
pkill -f celery
```

## Debugging Common Issues

### Tests Hanging or Getting Stuck

**Symptoms**:
- Tests run indefinitely without completing
- Celery workers show "Starting to process job" but never finish
- Multiple contradictory Celery processes running

**Solutions**:

1. **Enter proper environment**:
   ```bash
   nix-shell --run "cleanup_stuck_jobs.py"
   ```

2. **Check for stuck jobs**:
   ```bash
   nix-shell --run "python3 -c \"import os; from flask import Flask; from models import GradingJob, db; app = Flask(__name__); app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grading_app.db'; app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False; db.init_app(app); app.app_context().push(); jobs = GradingJob.query.all(); print(f'Jobs: {len(jobs)}')\""
   ```

3. **Clear Redis queues**:
   ```bash
   redis-cli flushall
   ```

### Import Errors

**Symptoms**:
- `ModuleNotFoundError: No module named 'celery'`
- `ModuleNotFoundError: No module named 'flask_sqlalchemy'`

**Solution**: Always run inside `nix-shell`

### Database Connection Issues

**Symptoms**:
- Database connection errors
- Tests failing to create tables

**Solution**: Ensure PostgreSQL is running in the Nix shell environment

## Test Development Guidelines

### Writing New Tests

1. **Always mock external API calls**:
   ```python
   from unittest.mock import patch
   
   @patch("utils.llm_providers.requests.post")
   def test_provider_success(self, mock_post):
       mock_post.return_value.status_code = 200
       # test implementation
   ```

2. **Use test fixtures**:
   ```python
   @pytest.fixture
   def sample_job(app):
       with app.app_context():
           job = GradingJob(job_name="Test", provider="openrouter", prompt="Test")
           db.session.add(job)
           db.session.commit()
           return job
   ```

3. **Avoid real Celery task execution in tests**:
   ```python
   @patch("tasks.process_job.delay")
   def test_upload_success(self, mock_delay):
       mock_delay.return_value = MagicMock(id="test-id")
       # test implementation
   ```

### Test Categories

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test component interactions with real database (in Nix shell)
- **API Tests**: Test Flask routes and endpoints with mocked external services

## Continuous Integration

The CI environment automatically uses Nix, so tests will run properly in CI as long as they work locally in the Nix shell.

## Performance Considerations

- Keep test data small and focused
- Use transactions and rollback for database tests
- Mock expensive operations (file I/O, network calls)
- Run tests with appropriate concurrency settings

## Troubleshooting Checklist

Before asking for help, check:

1. [ ] Running tests inside `nix-shell`
2. [ ] All external API calls are mocked
3. [ ] Only one set of Celery workers running
4. [ ] Database is properly initialized
5. [ ] Redis is accessible
6. [ ] No real tasks queued (check `redis-cli llen celery`)

## Getting Help

If you encounter issues:

1. Check this guide first
2. Look at existing test files for proper patterns
3. Ensure you're in the Nix shell environment
4. Check the `.pytest_cache` for recent test failures