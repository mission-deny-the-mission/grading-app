# Grading App - AI Agent Guide

## Project Overview

This is a Flask-based web application for AI-powered document grading. The system supports multiple AI providers (OpenRouter, Claude API, LM Studio) and provides batch processing capabilities for grading documents with configurable marking schemes.

### Core Features
- **Multi-format document processing**: DOCX, PDF, TXT support
- **Multiple AI providers**: OpenRouter, Claude API, LM Studio (local)
- **Batch processing**: Upload multiple documents for grading at once
- **Marking schemes**: Upload rubrics to guide grading consistency
- **Saved configurations**: Reuse prompts and marking schemes
- **Multi-model comparison**: Compare feedback from different AI models
- **Background processing**: Celery-based async task processing
- **Progress tracking**: Real-time status updates for grading jobs

### Architecture
- **Frontend**: Flask with Jinja2 templates
- **Backend**: Flask routes with SQLAlchemy ORM
- **Task Queue**: Celery with Redis broker
- **Database**: SQLite (default) or PostgreSQL
- **AI Integration**: Multiple provider support through modular LLM provider system

## Project Structure

```
grading-app/
├── app.py                    # Main Flask application
├── models.py                 # Database models (SQLAlchemy)
├── tasks.py                  # Celery tasks for background processing
├── routes/                   # Flask route blueprints
│   ├── main.py              # Main web interface routes
│   ├── api.py               # REST API endpoints
│   ├── upload.py            # File upload handling
│   ├── batches.py           # Batch management
│   └── templates.py         # Template/saved config management
├── utils/                    # Utility modules
│   ├── llm_providers.py     # AI provider integrations
│   ├── text_extraction.py   # Document text extraction
│   └── file_utils.py        # File handling utilities
├── templates/               # Jinja2 HTML templates
├── static/                  # CSS, JS, images
├── tests/                   # Test suite
├── uploads/                 # Uploaded document storage
└── docs/                    # Documentation
```

## Environment Setup

### Prerequisites
- Python 3.10+
- Redis server (for Celery)
- AI provider API keys or LM Studio running locally

### Quick Start
1. Copy environment variables:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your configuration:
   ```env
   OPENROUTER_API_KEY=your_openrouter_key
   CLAUDE_API_KEY=your_claude_key
   LM_STUDIO_URL=http://localhost:1234/v1
   SECRET_KEY=your_secret_key
   DATABASE_URL=sqlite:///grading_app.db
   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start Redis and run the application:
   ```bash
   ./start_services.sh
   ```

### Development with Nix
The project includes Nix support for reproducible development environments:

```bash
nix-shell  # Sets up complete dev environment
```

### Docker Development
```bash
make dev  # Start development containers
make dev-web  # Start Flask web service
make dev-worker  # Start Celery worker
```

## AI Agent Instructions

### Code Style and Conventions

1. **Python Style**: Follow PEP 8 with Black formatting
   - Use `black` and `isort` for consistent formatting
   - Maximum line length: 88 characters

2. **Database Models**:
   - All models inherit from `db.Model` in `models.py`
   - Use `to_dict()` methods for JSON serialization
   - Include descriptive docstrings and type hints

3. **Flask Routes**:
   - Use blueprint pattern (see `routes/` directory)
   - Keep routes thin - delegate business logic to utility functions
   - Use proper error handling and validation

4. **Background Tasks**:
   - All async processing goes through Celery tasks in `tasks.py`
   - Use `@celery.task` decorator for task functions
   - Implement proper error handling and status updates

### Working with the Codebase

#### Database Operations
- Always use SQLAlchemy ORM, never raw SQL
- Database sessions are managed automatically
- Use the existing models in `models.py` for consistency

#### File Uploads
- Maximum file size: 100MB (configurable in `app.py`)
- Supported formats: DOCX, PDF, TXT
- Files are stored in `uploads/` directory
- Use `utils.file_utils` for safe file operations

#### AI Provider Integration
- Implement new providers in `utils.llm_providers.py`
- Follow the existing provider interface pattern
- Use the provider semaphore for rate limiting
- Handle provider-specific errors gracefully

#### Error Handling
- Use appropriate HTTP status codes
- Return JSON error responses with clear messages
- Log errors for debugging purposes
- Handle provider-specific errors (API limits, auth failures)

### Testing Guidelines

1. **Test Structure**:
   - Unit tests for individual functions
   - Integration tests for database operations
   - End-to-end tests for API endpoints
   - Mock external API calls (AI providers)

2. **Running Tests**:
   ```bash
   pytest  # Run all tests
   pytest tests/test_models.py -v  # Specific module
   pytest -k "create and not slow"  # Filter by keyword
   ```

3. **Coverage**:
   - Maintain high test coverage
   - Coverage reports are generated automatically
   - Use `--no-cov` flag to skip coverage locally

### Common Tasks

#### Adding New Features
1. Plan the feature and identify affected components
2. Update database models if needed
3. Implement business logic in utility functions
4. Add API endpoints or web routes
5. Update frontend templates if needed
6. Add tests for new functionality

#### Debugging
1. Check application logs
2. Verify database state
3. Test with mock data
4. Use the development tools in Nix/Docker environments
5. Check Celery worker logs for background tasks

#### Performance Considerations
- Use background tasks for long-running operations
- Implement pagination for large datasets
- Cache frequently accessed data
- Optimize database queries with proper indexing

### Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **File Uploads**: Validate file types and sizes
3. **SQL Injection**: Always use parameterized queries through SQLAlchemy
4. **CSRF Protection**: Flask-WTF forms include CSRF protection
5. **Input Validation**: Validate all user inputs

### Contributing

1. Create feature branches from `main`
2. Write tests for new functionality
3. Ensure all tests pass before submitting
4. Follow the existing code style
5. Update documentation for significant changes

## Troubleshooting

### Common Issues

**Redis Connection Failed**
- Verify Redis is running on the configured host/port
- Check Redis logs for errors

**Database Connection Issues**
- Verify database URL in `.env`
- Check database service status
- Ensure proper file permissions for SQLite

**AI Provider Errors**
- Verify API keys are valid and not expired
- Check provider service status
- Verify LM Studio is running if using local provider

**File Upload Problems**
- Check file size limits
- Verify file format support
- Ensure upload directory exists and is writable

### Getting Help

- Check the `docs/` directory for detailed guides
- Review existing code patterns for similar functionality
- Check application and Celery logs for error details
- Use the provided test cases as examples of expected behavior

## Development Tools

### Available Commands
- `make dev` - Start development environment
- `make test` - Run test suite
- `make lint` - Run code linting
- `make format` - Format code with Black/isort
- `make shell` - Access development container shell

### Database Management
- `flask init-db` - Initialize database tables
- Database migrations are handled manually (current state)
- For schema changes, update models and handle migration carefully

### Monitoring
- Flower interface for Celery monitoring: `http://localhost:5555`
- Application logs available in development containers
- Database can be inspected through standard SQLite/PostgreSQL tools

This guide should help AI agents understand the project structure and contribute effectively to the codebase while maintaining consistency with existing patterns and practices.