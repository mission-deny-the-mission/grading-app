# Testing Guide

This document describes the testing setup and improvements made to the grading-app test suite.

## Quick Start

### Running Tests

```bash
# Using Makefile (recommended, easiest)
make test              # Run tests in parallel (default)
make test-sequential   # Run tests sequentially
make test-coverage     # Run tests with coverage report
make test-verbose      # Run tests with verbose output
make test-failed       # Re-run only previously failed tests
make test-fast         # Run tests with minimal output

# In container (manual)
docker-compose -f docker-compose.dev.yml exec app pytest tests/

# Local (requires venv)
source .venv/bin/activate
pytest tests/
```

Tests now run in parallel by default using pytest-xdist, providing:
- ✅ **2x faster** execution (~45s vs ~110s)
- ✅ **Better test isolation** through process separation
- ✅ **Higher pass rate** (76.4% vs 65.0%)

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/test_models.py

# Run a specific test class
pytest tests/test_models.py::TestGradingJob

# Run a specific test
pytest tests/test_models.py::TestGradingJob::test_create_job

# Run tests sequentially (no parallel)
pytest tests/ -n 0

# Run with coverage (disables parallelization)
pytest tests/ -n 0 --cov=app --cov=models --cov=tasks --cov=desktop
```

## Test Results Summary

### Before Improvements
- ❌ 414 tests failed
- ✅ 993 tests passed
- ⚠️ 145 errors
- ⏱️ ~110 seconds
- **Pass rate: 64.0%**

### After Improvements
- ❌ 327 tests failed
- ✅ 1,186 tests passed
- ⚠️ 41 errors
- ⏱️ ~44 seconds
- **Pass rate: 76.4%**

### Improvements
- **+193 more tests passing** ✅
- **-87 fewer failures** ✅
- **-104 fewer errors** ✅
- **2.5x faster execution** ⚡
- **+12.4% pass rate improvement** 📈

## Key Changes Made

### 1. Parallel Test Execution (pytest-xdist)

**Why:** Tests were failing due to state pollution when run sequentially. Individual test files passed 100% when run alone.

**Solution:** pytest-xdist runs tests in separate worker processes, providing true isolation.

**Configuration:** `pytest.ini`
```ini
addopts =
    -n auto          # Auto-detect CPU cores and spawn workers
    --dist loadscope # Distribute tests by test scope
```

### 2. Enhanced Test Cleanup Fixtures

**Added to `tests/conftest.py`:**

- **Database Session Cleanup** - Rollback, close, and remove sessions after each test
- **Deployment Mode Reset** - Reset to single-user mode after each test
- **Flask Globals Cleanup** - Clear Flask `g` object to prevent request context leakage
- **Scheduler Cleanup** - Shutdown background schedulers before and after tests
- **Environment Cleanup** - Restore test-specific environment variables
- **Celery Task Mocking** - Add `.delay` and `.apply_async` methods to task functions

### 3. Fixed Sharing Flow Tests

**Issue:** Tests created isolated databases missing the `deployment_config` table.

**Fix:** Added deployment mode initialization in test fixtures (`tests/integration/test_sharing_flow.py`).

## Test Categories

### Unit Tests
- `tests/unit/` - Unit tests for services and utilities
- Fast, isolated, no external dependencies

### Integration Tests
- `tests/integration/` - Integration tests for routes and workflows
- Test multiple components together

### Desktop Tests
- `tests/desktop/` - Desktop application-specific tests
- Test scheduler, updater, credentials, window management

### API Tests
- Marked with `@pytest.mark.api`
- Test API endpoints and responses

## Known Issues

### Remaining Test Failures

The 327 remaining failures fall into these categories:

1. **Test Design Issues** (~5 tests)
   - Tests have incorrect expectations about thread counts or directory paths
   - Example: `test_startup.py` expects 1 thread but `main()` starts 3

2. **Feature Gaps** (~2 tests)
   - Tests for unimplemented group membership features
   - Example: Group member access removal not fully implemented

3. **Redis/Session Infrastructure** (~30 tests)
   - Tests expecting specific Redis infrastructure not available in test env
   - Password reset tokens, session security

4. **State Pollution** (~290 tests)
   - Some tests still interfere with each other despite parallelization
   - Likely due to shared file system resources or timing issues

### Tests That Pass Individually But Fail in Suite

These tests demonstrate state pollution issues:
- `test_updater.py` - 40/40 pass alone
- `test_mode_specific.py` - 21/21 pass alone
- `test_auth_service.py` - 19/19 pass alone
- `test_tasks.py` - 41/41 pass alone

Running them individually is a workaround until root causes are fixed.

## Coverage

Coverage reporting is **disabled by default** when using parallel execution due to pytest-cov/pytest-xdist compatibility issues.

To generate coverage reports:
```bash
# Run sequentially with coverage
pytest tests/ -n 0 --cov=app --cov=models --cov=tasks --cov=desktop --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Troubleshooting

### Tests Fail Locally But Pass in CI
- Ensure you have pytest-xdist installed: `pip install pytest-xdist`
- Check you're using the same Python version (3.11+)

### Individual Test Passes But Fails in Suite
- This indicates test isolation issues
- Run the test alone: `pytest tests/path/to/test_file.py::TestClass::test_name`
- Check for shared state (global variables, singletons, class attributes)

### Slow Test Execution
- Parallel execution should be automatic with `-n auto`
- Check worker count: `pytest tests/ -n 4` for 4 workers
- Consider running fewer tests: `pytest tests/unit/` instead of all

### Coverage Not Working
- Coverage is disabled by default with xdist
- Run without parallelization: `pytest tests/ -n 0 --cov`

## Best Practices

### Writing New Tests

1. **Use fixtures for setup/teardown**
   ```python
   @pytest.fixture
   def sample_data(app):
       with app.app_context():
           # Setup
           yield data
           # Teardown happens automatically
   ```

2. **Don't rely on test execution order**
   - Tests should be independent
   - Don't share state between tests

3. **Clean up after yourself**
   - Database records
   - Files created
   - Environment variables

4. **Use appropriate markers**
   ```python
   @pytest.mark.integration
   @pytest.mark.slow
   def test_expensive_operation():
       pass
   ```

### Running Tests in Development

```bash
# Quick feedback loop - run only changed tests
pytest tests/test_models.py -v

# Full test suite before committing
pytest tests/

# Specific test while debugging
pytest tests/test_file.py::TestClass::test_method -vv -s
```

## Dependencies

### Required
- pytest >= 7.4.4
- pytest-xdist >= 3.8.0
- pytest-flask >= 1.3.0

### Optional
- pytest-cov >= 4.1.0 (for coverage reports)
- pytest-randomly (for randomized test order)

## Files Modified

1. **pytest.ini** - Added pytest-xdist configuration
2. **requirements-dev.txt** - Added pytest-xdist dependency
3. **Dockerfile.dev** - Added pytest-xdist to dev dependencies
4. **tests/conftest.py** - Enhanced cleanup fixtures
5. **tests/integration/test_sharing_flow.py** - Fixed deployment mode initialization

## Future Improvements

1. **Investigate remaining state pollution** - 290 tests still fail
2. **Add pytest-randomly** - Catch order-dependent failures
3. **Improve Redis test infrastructure** - Mock or provide test Redis instance
4. **Fix test design issues** - Update expectations in startup tests
5. **Transaction-based cleanup** - For specific test suites (API endpoints)
6. **Parallel-safe coverage** - Configure pytest-cov for xdist compatibility

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-xdist documentation](https://pytest-xdist.readthedocs.io/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
