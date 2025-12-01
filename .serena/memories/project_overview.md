# Grading App - Project Overview

## Purpose
AI-powered document grading web application with desktop support. The app enables educators to:
- Grade documents using multiple AI providers (OpenRouter, Claude API, LM Studio, Ollama)
- Create structured grading schemes with hierarchical questions and criteria
- Process submissions in batches
- Export results in CSV/JSON formats with statistical analysis

## Tech Stack

### Backend
- **Python 3.13.7** (constraint: `>=3.9,<4.0`)
- **Flask 2.3.3** - Web framework
- **Flask-SQLAlchemy 3.0.5** - ORM
- **Flask-Migrate** - Database migrations
- **Celery** - Async task processing (background grading jobs)
- **SQLite** - Desktop/development database
- **PostgreSQL** - Production database (optional)

### Security
- **cryptography >=41.0.0** - Fernet encryption for API keys at rest
- **Flask-Login** - User authentication
- **Flask-Limiter** - Rate limiting
- **Flask-WTF** - CSRF protection

### Document Processing
- **PyPDF2 3.0.1** - PDF parsing
- **python-docx 0.8.11** - Word document parsing
- **Pillow** - Image handling
- **opencv-python-headless** - Image processing
- **beautifulsoup4** - HTML parsing

### AI Provider SDKs
- **openai** - OpenAI/OpenRouter API
- **anthropic** - Claude API
- **google-generativeai** - Gemini API

### Desktop Application
- **PyInstaller** - Executable packaging
- **pywebview** - Desktop webview
- **pystray** - System tray
- **keyring** - Secure credential storage
- **tufup** - Auto-updates

## Key Features
1. Multi-provider AI grading (OpenRouter, Claude, LM Studio, Ollama, Gemini)
2. Structured grading schemes with rubrics
3. Batch processing for multiple submissions
4. Export to CSV/JSON with analytics
5. Desktop application with offline capability
6. API key encryption at rest
7. Optional multi-user authentication mode
