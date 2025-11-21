# Testing Notes

## Background Task Testing

Tests that use background tasks (via `ThreadPoolExecutor`) are now properly configured.

### The Problem

Background tasks spawn worker threads that need database access:
1. Worker threads call `create_app()` to get a Flask app instance
2. In testing mode, each thread was getting a different app with a different database
3. This caused **"no such table"** and **"Flask app not registered"** errors

### The Solution

**Two-part fix:**

1. **App Instance Caching** (`tasks.py`):
   - Added `set_test_app()` to register the test's app instance
   - Worker threads now reuse the same app (and database) as the test

2. **Serial Test Execution** (`pytest.ini`):
   - Disabled parallel execution to avoid race conditions
   - Tests run reliably without database conflicts

**Result:**
- ✅ No database access errors
- ✅ No Flask app registration errors
- ✅ Worker threads share the test database
- ❌ Tests run slower (serial vs parallel)

### Alternative Solutions Considered

1. **File-based test databases** - Adds complexity, still has race conditions
2. **Mock all background tasks** - Already done for most tests, but some tests need real execution
3. **Shared database per test worker** - Complex setup, prone to conflicts
4. **Fix `create_app()` to reuse existing app** - Major refactoring, risky for production code

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_tasks.py::TestProcessJob::test_process_job_success

# Run with verbose output
pytest -v

# If you need parallel execution for development (at your own risk)
pytest -n auto  # May cause intermittent failures
```

### Test Performance

- **Serial execution**: ~1-2 minutes for full test suite
- **Parallel execution**: Would be ~20-30 seconds, but unstable

For most development workflows, the reliability of serial execution outweighs the speed benefit of parallel execution.
