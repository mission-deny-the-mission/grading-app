# Codebase Structure

## Root Directory Layout
```
grading-app/
├── app.py              # Flask application entry point, configuration
├── models.py           # SQLAlchemy database models
├── tasks.py            # Celery background tasks
├── conftest.py         # Root pytest configuration
├── routes/             # Flask route blueprints
├── services/           # Business logic services
├── utils/              # Utility functions
├── templates/          # Jinja2 HTML templates
├── static/             # CSS, JS, images
├── tests/              # Test suite
├── desktop/            # Desktop application code
├── migrations/         # Database migrations
├── docs/               # Documentation
├── specs/              # Feature specifications
├── uploads/            # File upload storage
└── exports/            # Export output directory
```

## Key Files

### Entry Points
- `app.py` - Flask app factory and configuration
- `run_desktop_dev.py` - Desktop application entry
- `tasks.py` - Celery task definitions

### Models (`models.py`)
Key database models:
- `GradingJob` - Individual grading task
- `JobBatch` - Batch of grading jobs
- `Submission` - Student submission
- `GradingScheme` - Grading rubric
- `SchemeQuestion` - Question in a scheme
- `SchemeCriterion` - Criterion for evaluation
- `GradeResult` - Grading results
- `Config` - Application configuration
- `User` - User accounts (multi-user mode)

### Routes Directory
- `main.py` - Main page routes
- `grading.py` - Grading API endpoints
- `schemes.py` - Grading scheme API
- `batches.py` - Batch processing routes
- `export.py` - Export functionality
- `config_routes.py` - Configuration endpoints
- `auth_routes.py` - Authentication API
- `admin_routes.py` - Admin panel routes
- `sharing_routes.py` - Collaboration features

### Services Directory
- `auth_service.py` - Authentication logic
- `deployment_service.py` - Single/multi-user mode
- `document_parser.py` - Document text extraction
- `scheme_serializer.py` - Scheme JSON serialization
- `scheme_deserializer.py` - Scheme import
- `sharing_service.py` - Project sharing logic

### Utils Directory
- `llm_providers.py` - AI provider abstraction
- `encryption.py` - API key encryption
- `text_extraction.py` - Document text extraction
- `scheme_calculator.py` - Grade calculations
- `scheme_validator.py` - Scheme validation
- `export_formatters.py` - Export formatting

### Tests Directory
- `tests/test_models.py` - Model unit tests
- `tests/test_tasks.py` - Celery task tests
- `tests/integration/` - Integration tests
- `tests/desktop/` - Desktop app tests
- `tests/unit/` - Unit tests
- `tests/conftest.py` - Test fixtures
