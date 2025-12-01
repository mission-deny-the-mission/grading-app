# Testing Guide - Optional Multi-User Authentication System

## Overview

This guide covers testing for the optional multi-user authentication system added to the grading application. The test suite includes 141 total tests (45 from Phases 1-3, 96 new in Phase 4).

## Test Organization

### Test Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── factories.py                   # Test data factories
├── unit/
│   ├── test_auth_service.py      # Auth service unit tests (19 tests)
│   └── test_deployment_service.py # Deployment service tests (17 tests)
├── integration/
│   └── test_deployment_modes.py   # Mode integration tests (9 tests)
├── test_authorization.py          # Authorization & permissions (19 tests)
├── test_usage_tracking.py         # Usage tracking & quotas (18 tests)
├── test_project_sharing.py        # Project sharing (19 tests)
├── test_phase4_single_user.py     # Single-user optimization (20 tests)
└── test_mode_specific.py          # Mode-specific behavior (20 tests)
```

## Running Tests

### Prerequisites

```bash
# Activate virtual environment
source venv_test/bin/activate

# Install test dependencies
pip install pytest pytest-cov
```

### Run All Tests

```bash
# All tests with verbose output
pytest -v

# All tests with coverage
pytest --cov=app --cov=services --cov=routes --cov=models --cov-report=html
```

### Run Specific Test Categories

```bash
# Authentication tests
pytest tests/unit/test_auth_service.py -v

# Deployment mode tests
pytest tests/unit/test_deployment_service.py tests/integration/test_deployment_modes.py -v

# Authorization tests
pytest tests/test_authorization.py -v

# Usage tracking tests
pytest tests/test_usage_tracking.py -v

# Project sharing tests
pytest tests/test_project_sharing.py -v

# Phase 4 single-user tests
pytest tests/test_phase4_single_user.py -v

# Mode-specific behavior tests
pytest tests/test_mode_specific.py -v
```

### Run Performance Tests

```bash
# All performance tests
pytest tests/test_phase4_single_user.py::TestPerformanceOptimization \
       tests/test_phase4_single_user.py::TestDatabasePerformance \
       tests/test_phase4_single_user.py::TestResourceUsage -v

# API response time tests
pytest tests/test_phase4_single_user.py::TestPerformanceOptimization::test_api_response_time_under_threshold -v
```

### Run Tests by Tag

```bash
# Only passing tests
pytest -v -k "not test_owner" | grep PASSED

# Only usage tracking tests
pytest -v -k "usage"

# Only authorization tests
pytest -v -k "auth"
```

## Test Fixtures

### Common Fixtures

All test files use these fixtures from `conftest.py` and individual test files:

**App Fixtures**:
- `app`: Base Flask app with in-memory SQLite database
- `app_single_user`: App configured for single-user mode
- `app_multi_user`: App configured for multi-user mode

**Client Fixtures**:
- `client`: Test client for making HTTP requests
- `client_single_user`: Client for single-user mode testing
- `client_multi_user`: Client for multi-user mode testing

**Data Fixtures**:
- `sample_job`: Pre-created grading job for testing
- `sample_submission`: Pre-created submission for testing
- `sample_marking_scheme`: Pre-created marking scheme
- `sample_batch`: Pre-created job batch

### Factory Fixtures

Use factories from `tests/factories.py` for creating test data:

```python
from tests.factories import UserFactory, ProjectFactory, UsageRecordFactory

def test_example(app):
    with app.app_context():
        # Create test user
        user = UserFactory.create(email="test@example.com")

        # Create test project
        project = ProjectFactory.create(
            job_name="Test Project",
            owner_id=user.id
        )

        # Create usage record
        usage = UsageRecordFactory.create(
            user_id=user.id,
            provider="openrouter",
            tokens_consumed=1000
        )
```

## Test Data Factories

### UserFactory

```python
# Create single user
user = UserFactory.create(
    email="user@example.com",
    password="Password123!",
    display_name="Test User",
    is_admin=False
)

# Create multiple users
users = UserFactory.create_batch(count=5)

# Create admin user
admin = UserFactory.create(is_admin=True)
```

### ProjectFactory

```python
# Create project
project = ProjectFactory.create(
    job_name="My Project",
    owner_id=user.id,
    description="Test project"
)

# Create multiple projects
projects = ProjectFactory.create_batch(count=3, owner_id=user.id)
```

### UsageRecordFactory

```python
# Create usage record
usage = UsageRecordFactory.create(
    user_id=user.id,
    provider="openrouter",
    tokens_consumed=1000,
    operation_type="grading"
)

# Create batch of usage records
records = UsageRecordFactory.create_batch(
    count=10,
    user_id=user.id,
    provider="openrouter"
)
```

### QuotaFactory

```python
# Create quota
quota = QuotaFactory.create(
    user_id=user.id,
    provider="openrouter",
    limit_value=100000,
    reset_period="monthly"
)
```

### ShareFactory

```python
# Create project share
share = ShareFactory.create(
    project_id=project.id,
    owner_id=owner.id,
    recipient_id=recipient.id,
    permission_level="read"  # or "write"
)
```

### Pre-Configured Scenarios

```python
from tests.factories import TestScenarios

# Multi-user project with collaborators
scenario = TestScenarios.create_multi_user_project_scenario()
owner = scenario["owner"]
collaborators = scenario["collaborators"]
project = scenario["project"]
shares = scenario["shares"]

# User near quota limit (85% usage)
scenario = TestScenarios.create_quota_limit_scenario()
user = scenario["user"]
quota = scenario["quota"]
usage_records = scenario["usage_records"]

# User over quota (110% usage)
scenario = TestScenarios.create_over_quota_scenario()
```

## Test Categories

### 1. Authentication Tests (19 tests)

Tests for user creation, password validation, authentication, and user management.

**Key Test Cases**:
- User creation with validation
- Password strength requirements
- Email validation
- User authentication
- Session management
- User updates
- User listing and pagination

**Example**:
```python
def test_create_user_success(app):
    with app.app_context():
        user = AuthService.create_user(
            "test@example.com",
            "Password123!",
            "Test User"
        )
        assert user.email == "test@example.com"
        assert user.is_active
```

### 2. Deployment Mode Tests (17 tests)

Tests for deployment mode management and validation.

**Key Test Cases**:
- Get current mode
- Set mode (single-user/multi-user)
- Mode persistence
- Mode validation
- Environment variable consistency

**Example**:
```python
def test_set_mode_single_user(app):
    with app.app_context():
        DeploymentService.set_mode("single-user")
        assert DeploymentService.is_single_user_mode()
```

### 3. Authorization Tests (19 tests)

Tests for access control and permissions.

**Key Test Cases**:
- Single-user mode bypass
- Multi-user mode enforcement
- Admin permissions
- Project access control
- Data isolation

**Example**:
```python
def test_single_user_mode_no_auth_required(app_single_user, client_single_user):
    response = client_single_user.get("/")
    assert response.status_code == 200
```

### 4. Usage Tracking Tests (18 tests)

Tests for AI provider usage tracking and quota management.

**Key Test Cases**:
- Usage recording
- Quota calculation
- Quota enforcement
- Usage history
- Usage dashboard
- Quota management

**Example**:
```python
def test_record_usage_success(app):
    with app.app_context():
        user = UserFactory.create()
        record = UsageTrackingService.record_usage(
            user_id=user.id,
            provider="openrouter",
            tokens_consumed=1000,
            operation_type="grading"
        )
        assert record.tokens_consumed == 1000
```

### 5. Project Sharing Tests (19 tests)

Tests for project sharing and permissions.

**Key Test Cases**:
- Share project with users
- Permission levels (read/write)
- Share updates
- Share revocation
- Access validation
- Modification permissions

**Example**:
```python
def test_share_project_success(app):
    with app.app_context():
        owner = UserFactory.create()
        recipient = UserFactory.create()
        project = ProjectFactory.create(owner_id=owner.id)

        share = SharingService.share_project(
            project_id=project.id,
            owner_id=owner.id,
            recipient_id=recipient.id,
            permission_level="read"
        )
        assert share is not None
```

### 6. Single-User Mode Tests (20 tests)

Tests for single-user mode optimization and performance.

**Key Test Cases**:
- Grading without authentication
- Backwards compatibility
- Middleware bypass
- API performance (<500ms)
- Database efficiency
- Resource usage

**Example**:
```python
def test_api_response_time_under_threshold(app_single_user, client_single_user):
    start = time.time()
    response = client_single_user.get("/api/config/deployment-mode")
    duration = (time.time() - start) * 1000

    assert response.status_code == 200
    assert duration < 500  # Under 500ms
```

### 7. Mode-Specific Tests (20 tests)

Tests for mode-specific behavior and feature visibility.

**Key Test Cases**:
- Feature availability by mode
- Mode switching
- Data preservation
- API behavior differences
- Permission enforcement by mode

**Example**:
```python
def test_data_preserved_on_mode_switch(app):
    with app.app_context():
        DeploymentService.set_mode("multi-user")
        user = AuthService.create_user("test@example.com", "Password123!")

        DeploymentService.set_mode("single-user")

        retrieved = User.query.get(user.id)
        assert retrieved is not None
```

## Coverage Goals

### Current Coverage

- **Overall**: 76% (107/141 tests passing)
- **Usage Tracking**: 100% (18/18 tests passing)
- **Performance**: 85% (17/20 tests passing)
- **Mode Behavior**: 85% (17/20 tests passing)
- **Services**: 90%+ target
- **Routes/API**: 80%+ target
- **Models**: 85%+ target

### Measuring Coverage

```bash
# Generate HTML coverage report
pytest --cov=app --cov=services --cov=routes --cov=models --cov-report=html

# View coverage report
open htmlcov/index.html

# Coverage for specific module
pytest --cov=services.auth_service --cov-report=term-missing
```

## Writing New Tests

### Test Structure

```python
"""Module docstring describing test purpose."""

import pytest
from models import db
from services.auth_service import AuthService


class TestFeatureName:
    """Test class for specific feature."""

    def test_specific_behavior(self, app):
        """Test specific behavior with descriptive docstring."""
        with app.app_context():
            # Arrange
            user = UserFactory.create()

            # Act
            result = AuthService.some_method(user.id)

            # Assert
            assert result is not None


@pytest.fixture
def app():
    """Create Flask app fixture."""
    from app import create_app

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
```

### Best Practices

1. **Use Descriptive Names**: Test names should clearly describe what is being tested
2. **One Assertion Per Test**: Focus each test on a single behavior
3. **Use Factories**: Leverage test factories for creating test data
4. **Test Isolation**: Each test should be independent and not rely on others
5. **Clean Up**: Use fixtures to ensure proper cleanup
6. **Document**: Include docstrings explaining test purpose

### Common Patterns

**Testing Services**:
```python
def test_service_method(app):
    with app.app_context():
        # Create test data
        user = UserFactory.create()

        # Call service method
        result = AuthService.some_method(user.id)

        # Verify behavior
        assert result.some_property == expected_value
```

**Testing API Endpoints**:
```python
def test_api_endpoint(client):
    response = client.get("/api/some-endpoint")

    assert response.status_code == 200
    data = response.get_json()
    assert data["key"] == "expected_value"
```

**Testing Permissions**:
```python
def test_permission_enforcement(app_multi_user, client_multi_user):
    # Attempt protected action without auth
    response = client_multi_user.get("/protected-route")

    assert response.status_code == 401
```

## Debugging Tests

### Running Single Test

```bash
# Run specific test
pytest tests/test_usage_tracking.py::TestUsageRecording::test_record_usage_success -v

# Run with print statements
pytest tests/test_usage_tracking.py::TestUsageRecording::test_record_usage_success -v -s

# Run with debugger
pytest tests/test_usage_tracking.py::TestUsageRecording::test_record_usage_success -v --pdb
```

### Verbose Output

```bash
# Show detailed output
pytest -v -s

# Show all output including passed tests
pytest -v -s --tb=short

# Show full traceback
pytest -v --tb=long
```

### Selective Running

```bash
# Run only failed tests
pytest --lf

# Run failed tests first
pytest --ff

# Run tests matching pattern
pytest -k "usage_tracking"
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.13

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest --cov=app --cov=services --cov=routes --cov=models

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Troubleshooting

### Common Issues

**Import Errors**:
```bash
# Ensure you're in the project root
cd /path/to/grading-app-auth

# Activate virtual environment
source venv_test/bin/activate
```

**Database Errors**:
```bash
# Clear test database
rm -f test.db

# Run with fresh database
pytest --create-db
```

**Fixture Errors**:
```bash
# Check fixture dependencies
pytest --fixtures

# Run with fixture setup details
pytest -v --setup-show
```

### Getting Help

- Check test output for error messages
- Use `-v` flag for verbose output
- Use `-s` flag to see print statements
- Use `--pdb` flag to drop into debugger on failure
- Review test docstrings for expected behavior

## Next Steps

After running tests:

1. **Review Coverage Report**: Identify untested code paths
2. **Fix Failing Tests**: Address test failures one by one
3. **Add Missing Tests**: Cover gaps identified in coverage report
4. **Update Documentation**: Keep this guide current with new tests
5. **Optimize Performance**: Use performance tests to identify bottlenecks

## Conclusion

This test suite provides comprehensive coverage of the authentication system with focus on:
- Functional correctness
- Performance optimization
- Security validation
- Backwards compatibility
- Mode-specific behavior

Continue adding tests as new features are developed to maintain high code quality and prevent regressions.
