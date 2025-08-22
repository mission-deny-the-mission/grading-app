# Grading App Test Suite

This directory contains comprehensive unit tests for the grading application. The test suite is designed to ensure the reliability and correctness of all application components.

## Test Structure

```
tests/
├── __init__.py              # Makes tests a Python package
├── conftest.py              # Pytest configuration and fixtures
├── test_models.py           # Database model tests
├── test_routes.py           # Flask route and API endpoint tests
├── test_tasks.py            # Celery task and grading function tests
├── test_utils.py            # Utility function and file processing tests
└── README.md               # This file
```

## Test Categories

### 1. Unit Tests (`test_models.py`)
- **Purpose**: Test individual database models and their methods
- **Coverage**: Model creation, validation, relationships, and business logic
- **Examples**: 
  - Creating grading jobs and submissions
  - Testing model relationships
  - Validating model constraints
  - Testing retry functionality

### 2. API Tests (`test_routes.py`)
- **Purpose**: Test Flask routes and API endpoints
- **Coverage**: HTTP endpoints, request/response handling, error cases
- **Examples**:
  - File upload endpoints
  - Job management APIs
  - Batch processing endpoints
  - Error handling for invalid requests

### 3. Task Tests (`test_tasks.py`)
- **Purpose**: Test Celery tasks and grading functions
- **Coverage**: Background job processing, API integrations, error handling
- **Examples**:
  - Grading with different AI providers
  - Task execution and error recovery
  - Batch processing workflows
  - API timeout and failure scenarios

### 4. Utility Tests (`test_utils.py`)
- **Purpose**: Test utility functions and file processing
- **Coverage**: File handling, text extraction, validation
- **Examples**:
  - PDF, DOCX, and TXT file processing
  - Multi-model comparison
  - Configuration validation
  - Data export functionality

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Ensure the application is properly configured (database, environment variables)

### Basic Test Commands

#### Run All Tests
```bash
python run_tests.py
# or
pytest tests/
```

#### Run Specific Test Categories
```bash
# Unit tests only
python run_tests.py --type unit

# API tests only
python run_tests.py --type api

# Database tests only
python run_tests.py --type database

# Celery task tests only
python run_tests.py --type celery
```

#### Run Tests with Coverage
```bash
python run_tests.py --coverage
# or
pytest tests/ --cov=app --cov=models --cov=tasks --cov-report=html
```

#### Run Specific Test Files
```bash
python run_tests.py --file tests/test_models.py
# or
pytest tests/test_models.py
```

#### Run Specific Test Classes
```bash
python run_tests.py --class models
# or
pytest tests/test_models.py::TestGradingJob
```

#### Run Fast Tests (Exclude Slow Tests)
```bash
python run_tests.py --type fast
# or
pytest tests/ -m "not slow"
```

### Advanced Test Commands

#### Run All Checks (Tests + Linting + Type Checking)
```bash
python run_tests.py --all-checks
```

#### Run Only Linting
```bash
python run_tests.py --lint
```

#### Run Only Type Checking
```bash
python run_tests.py --type-check
```

### Direct Pytest Commands

```bash
# Run with verbose output
pytest tests/ -v

# Run with coverage and generate HTML report
pytest tests/ --cov=app --cov=models --cov=tasks --cov-report=html

# Run specific test function
pytest tests/test_models.py::TestGradingJob::test_create_job

# Run tests matching a pattern
pytest tests/ -k "test_create"

# Run tests with specific markers
pytest tests/ -m "unit"
pytest tests/ -m "integration"
pytest tests/ -m "not slow"
```

## Test Fixtures

The test suite uses pytest fixtures defined in `conftest.py`:

### Database Fixtures
- `app`: Flask application with test configuration
- `client`: Test client for making HTTP requests
- `sample_job`: Pre-created grading job for testing
- `sample_submission`: Pre-created submission for testing
- `sample_batch`: Pre-created batch for testing
- `sample_marking_scheme`: Pre-created marking scheme for testing

### File Fixtures
- `sample_text_file`: Temporary text file for testing
- `sample_docx_file`: Temporary DOCX file for testing
- `sample_pdf_file`: Temporary PDF file for testing

### Mock Fixtures
- `mock_api_keys`: Mocked API keys for testing
- `mock_celery`: Mocked Celery for testing

## Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.api`: API tests
- `@pytest.mark.database`: Database tests
- `@pytest.mark.celery`: Celery task tests
- `@pytest.mark.slow`: Slow-running tests

## Coverage Reports

After running tests with coverage, you can find reports in:

- **Terminal**: Coverage summary in the test output
- **HTML**: `htmlcov/index.html` - Detailed coverage report
- **XML**: `coverage.xml` - Coverage data for CI/CD tools

## Writing New Tests

### Test File Structure
```python
"""
Unit tests for [component name].
"""

import pytest
from unittest.mock import patch, MagicMock

class TestComponentName:
    """Test cases for [component name]."""
    
    def test_specific_functionality(self, app):
        """Test description."""
        # Arrange
        # Act
        # Assert
        pass
    
    @patch('module.function')
    def test_with_mocking(self, mock_function, app):
        """Test with mocked dependencies."""
        # Arrange
        mock_function.return_value = "expected_result"
        
        # Act
        result = function_under_test()
        
        # Assert
        assert result == "expected_result"
```

### Test Naming Conventions
- Test files: `test_<module_name>.py`
- Test classes: `Test<ComponentName>`
- Test methods: `test_<description>`

### Best Practices
1. **Arrange-Act-Assert**: Structure tests clearly
2. **Descriptive names**: Use clear, descriptive test names
3. **One assertion per test**: Focus on testing one thing
4. **Use fixtures**: Leverage pytest fixtures for common setup
5. **Mock external dependencies**: Mock APIs, databases, and external services
6. **Test edge cases**: Include error conditions and boundary cases

## Continuous Integration

The test suite is designed to work with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pip install -r requirements-dev.txt
    python run_tests.py --coverage
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running tests from the project root
2. **Database Errors**: Check that test database is properly configured
3. **Missing Dependencies**: Install all requirements from `requirements-dev.txt`
4. **Permission Errors**: Ensure test files have proper permissions

### Debugging Tests

```bash
# Run tests with debug output
pytest tests/ -v -s

# Run specific test with debugger
pytest tests/test_models.py::TestGradingJob::test_create_job -s

# Run tests with maximum verbosity
pytest tests/ -vvv
```

## Test Data

Test data is created dynamically and cleaned up automatically. No persistent test data is stored in the main database.

## Performance

- **Unit tests**: < 1 second each
- **Integration tests**: 1-5 seconds each
- **API tests**: 1-3 seconds each
- **Full test suite**: 30-60 seconds

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve coverage
4. Update this README if adding new test categories

## Support

For questions about the test suite:
1. Check this README
2. Review existing test examples
3. Check pytest documentation
4. Review the application code for context
