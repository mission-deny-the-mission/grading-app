# grading-app Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-17

## Active Technologies
- SQLite (replacing PostgreSQL/Redis for single-user desktop), local filesystem for uploads and backups (004-desktop-app)
- Python 3.13.7 (recommend constraint: `>=3.9,<4.0` in setup.py) (002-api-provider-security)
- Python 3.13.7 (existing project) (004-optional-auth-system)
- Python 3.13.7 (001-ocr-image-grading)

## Project Structure

```text
src/
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.13.7 (recommend constraint: `>=3.9,<4.0` in setup.py): Follow standard conventions

## Recent Changes
- 004-desktop-app: Added SQLite (replacing PostgreSQL/Redis for single-user desktop), local filesystem for uploads and backups
- 004-optional-auth-system: Added Python 3.13.7 (existing project)
- 003-structured-grading-scheme: Added Python 3.13.7 + Flask 2.3.3, Flask-SQLAlchemy 3.0.5, Celery 5.3.4, Redis 5.0.1
- 002-api-provider-security: Added Python 3.13.7 (recommend constraint: `>=3.9,<4.0` in setup.py)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
