# Desktop Application Integration Tests

This directory contains integration tests for the desktop application (Phase 3 of User Story 1).

## Overview

Integration tests verify that multiple components work together correctly in realistic scenarios. These tests cover:

### test_startup.py
Tests for application startup sequence:
- Flask server startup in desktop window
- Database initialization on first run
- User data directory creation
- Settings file creation
- Full application startup sequence
- Port allocation and Flask server binding
- Error handling during startup

### test_offline.py
Tests for offline functionality:
- Application starts without internet connection
- Existing grading features work offline
- Database operations work offline (CRUD operations)
- AI API calls fail gracefully when offline
- Settings persistence works offline
- File operations work offline
- Complete offline session scenarios

## Running the Tests

### Run all integration tests:
```bash
python -m pytest tests/desktop/integration/ -v
```

### Run specific test file:
```bash
python -m pytest tests/desktop/integration/test_startup.py -v
python -m pytest tests/desktop/integration/test_offline.py -v
```

### Run specific test class:
```bash
python -m pytest tests/desktop/integration/test_startup.py::TestFullStartupSequence -v
python -m pytest tests/desktop/integration/test_offline.py::TestOfflineStartup -v
```

### Run specific test:
```bash
python -m pytest tests/desktop/integration/test_startup.py::TestFullStartupSequence::test_full_startup_creates_all_components -v
```

### Run with coverage:
```bash
python -m pytest tests/desktop/integration/ --cov=desktop --cov-report=html
```

## Test Structure

Integration tests use proper mocking for:
- PyWebView (desktop window management)
- Keyring (credential storage)
- APScheduler (background task scheduling)
- Network operations (to simulate offline mode)
- Flask app and database operations

## Dependencies

The integration tests mock external dependencies but test real interactions between:
- Flask application
- Database (SQLite)
- Desktop configuration
- Settings management
- File system operations

## Notes

- Tests use temporary directories for file operations
- Database operations use in-memory SQLite for speed
- All tests are isolated and can run in parallel
- Mocks are set up in `conftest.py` before module imports
