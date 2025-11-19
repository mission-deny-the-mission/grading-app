# grading-app Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-17

## Active Technologies
- SQLite (replacing PostgreSQL/Redis for single-user desktop), local filesystem for uploads and backups (004-desktop-app)
- Python 3.13.7 (recommend constraint: `>=3.9,<4.0` in setup.py) (002-api-provider-security)
- Python 3.13.7 (existing project) (004-optional-auth-system)
- Python 3.13.7 (001-ocr-image-grading)
- Python 3.13.7 (per CLAUDE.md requirements) + Flask 2.3.3, Flask-SQLAlchemy 3.0.5, Celery (async document processing), existing LLM provider abstraction (from 002-api-provider-security), PyPDF2 3.0.1, python-docx 0.8.11, Pillow (image handling) (005-marking-schema-as-file)
- SQLite for desktop version, database (PostgreSQL for production) for web version, local filesystem for exported JSON files (005-marking-schema-as-file)

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
- 005-marking-schema-as-file: Added Python 3.13.7 (per CLAUDE.md requirements) + Flask 2.3.3, Flask-SQLAlchemy 3.0.5, Celery (async document processing), existing LLM provider abstraction (from 002-api-provider-security), PyPDF2 3.0.1, python-docx 0.8.11, Pillow (image handling)
- 004-desktop-app: Added SQLite (replacing PostgreSQL/Redis for single-user desktop), local filesystem for uploads and backups
- 004-optional-auth-system: Added Python 3.13.7 (existing project)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
