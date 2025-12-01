# Suggested Commands

## Running the Application

### Local Development (without Docker)
```bash
# Activate virtual environment
source .venv/bin/activate

# Run Flask app
python app.py

# Run with production server
gunicorn --config gunicorn.conf.py app:app
```

### Docker Development
```bash
# Build and start all services
make dev-build && make dev-up

# Start Flask web service
make dev-web

# Start Celery worker
make dev-worker

# Start Celery beat scheduler
make dev-beat

# View logs
make dev-logs

# Stop services
make dev-down
```

## Testing

### Running Tests
```bash
# Recommended: Run all tests (uses pytest-xdist for parallelization)
pytest tests/

# Run tests sequentially (slower but more reliable)
pytest tests/ -n 0

# Run specific test file
pytest tests/test_models.py

# Run specific test class
pytest tests/test_models.py::TestGradingJob

# Run specific test method
pytest tests/test_models.py::TestGradingJob::test_create_job -v

# Run with verbose output
pytest tests/ -vv

# Re-run only failed tests
pytest tests/ --lf

# Run with coverage (sequential mode required)
pytest tests/ -n 0 --cov=app --cov=models --cov=tasks --cov=desktop --cov-report=html
```

### Test Markers
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Code Quality

### Linting
```bash
# Run ruff linter (recommended)
ruff check .

# In Docker
make lint
```

### Formatting
```bash
# Format with black
black .

# Sort imports with isort
isort .

# In Docker
make format
```

## Database

### Migrations
```bash
# Create a new migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

### Initialize Database
```bash
flask init-db
```

## System Utilities
- `git` - Version control
- `ls` - List directory contents
- `cd` - Change directory
- `grep` - Search text patterns
- `find` - Find files
- `cat` - Display file contents
