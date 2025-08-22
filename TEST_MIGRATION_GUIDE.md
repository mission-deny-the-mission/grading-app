# Test Migration Guide

## Overview

The old test scripts have been replaced with a comprehensive unit test suite using pytest. This guide helps you understand the migration and how to use the new test system.

## What Changed

### Old System (Scripts)
- Individual Python scripts that could be run directly
- Manual setup and teardown
- Limited test isolation
- No standardized reporting

### New System (Pytest)
- Structured test suite with fixtures
- Automatic test discovery
- Comprehensive coverage reporting
- Better error handling and debugging

## Migration Mapping

| Old Test Script | New Test Files | Purpose |
|----------------|----------------|---------|
| `test_celery.py` | `tests/test_tasks.py` | Celery task testing |
| `test_configurable_params.py` | `tests/test_models.py` | Model parameter testing |
| `test_custom_models.py` | `tests/test_routes.py` | API endpoint testing |
| `test_error_handling.py` | `tests/test_tasks.py` | Error handling testing |
| `test_error_handling_simple.py` | `tests/test_tasks.py` | Error handling testing |
| `test_job_details.py` | `tests/test_routes.py` | Job API testing |
| `test_marking_scheme.py` | `tests/test_routes.py` | Marking scheme testing |
| `test_multi_model.py` | `tests/test_utils.py` | Multi-model comparison |
| `test_retry.py` | `tests/test_models.py` | Retry functionality |
| `test_retry_all.py` | `tests/test_models.py` | Batch retry functionality |

## How to Run Tests

### Before (Old Scripts)
```bash
python test_celery.py
python test_configurable_params.py
# etc...
```

### After (New Test Suite)
```bash
# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py --type unit
python run_tests.py --type api
python run_tests.py --type celery

# Run with coverage
python run_tests.py --coverage

# Run specific test files
pytest tests/test_models.py
```

## Key Benefits

1. **Better Organization**: Tests are organized by functionality
2. **Fixtures**: Reusable test setup and teardown
3. **Coverage**: Automatic coverage reporting
4. **Isolation**: Each test runs in isolation
5. **Debugging**: Better error messages and debugging tools
6. **CI/CD Ready**: Designed for continuous integration

## Test Categories

### Unit Tests (`tests/test_models.py`)
- Database model testing
- Business logic validation
- Model relationships

### API Tests (`tests/test_routes.py`)
- HTTP endpoint testing
- Request/response validation
- Error handling

### Task Tests (`tests/test_tasks.py`)
- Celery task testing
- Background job processing
- API integration testing

### Utility Tests (`tests/test_utils.py`)
- File processing
- Text extraction
- Configuration validation

## Writing New Tests

### Example: Testing a New Model Method

```python
# tests/test_models.py
class TestGradingJob:
    def test_new_method(self, app):
        # Test the new method functionality
        with app.app_context():
            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                prompt="Test prompt"
            )
            
            result = job.new_method()
            assert result == expected_value
```

### Example: Testing a New API Endpoint

```python
# tests/test_routes.py
class TestNewAPI:
    def test_new_endpoint(self, client):
        # Test the new API endpoint
        response = client.post('/api/new_endpoint', json={
            'data': 'test_data'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from project root
2. **Database Errors**: Check test database configuration
3. **Missing Dependencies**: Install `requirements-dev.txt`

### Getting Help

1. Check `tests/README.md` for detailed documentation
2. Review existing test examples
3. Check pytest documentation
4. Look at the application code for context

## Next Steps

1. Familiarize yourself with the new test structure
2. Run the test suite to ensure everything works
3. Update any CI/CD pipelines to use the new test commands
4. Write tests for any new features you develop

## Rollback

If you need to rollback to the old test system:
1. Check the `old_tests_backup/` directory
2. Copy the old test files back to the root directory
3. Remove the `tests/` directory and `run_tests.py`

However, we recommend using the new test suite as it provides better testing capabilities and maintainability.
