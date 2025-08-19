# Docker & Dev Container Setup for Grading App

This document provides instructions for setting up and running the Grading App using Docker and Dev Containers.

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- VS Code with Dev Containers extension (for development)
- Git

## Quick Start

### Production Environment

1. **Clone and setup:**
   ```bash
   git clone <your-repo>
   cd grading-app
   cp env.example .env
   # Edit .env with your API keys
   ```

2. **Build and run:**
   ```bash
   make build
   make up
   ```

3. **Access the application:**
   - Flask App: http://localhost:5000
   - Flower (Celery Monitor): http://localhost:5555



#### Option 1: Using Dev Containers (Recommended)

1. **Open in VS Code:**
   ```bash
   code .
   ```

2. **Open in Dev Container:**
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Select "Dev Containers: Reopen in Container"
   - Wait for the container to build and start

3. **Start services:**
   ```bash
   # In the dev container terminal
   flask init-db
   python app.py
   ```

4. **Start background services (in separate terminals):**
   ```bash
   # Terminal 1: Celery Worker
   celery -A tasks worker --loglevel=info --concurrency=2 --queues=grading,maintenance
   
   # Terminal 2: Celery Beat (optional)
   celery -A tasks beat --loglevel=info
   ```

#### Option 2: Using Docker Compose

1. **Build and start development environment:**
   ```bash
   make dev
   ```

2. **Start additional services:**
   ```bash
   make dev-worker  # Start Celery worker
   make dev-beat    # Start Celery beat
   ```

## Available Commands

### Production Commands
```bash
make build    # Build production images
make up       # Start production services
make down     # Stop production services
make logs     # View logs
make clean    # Clean up containers and volumes
```

### Development Commands
```bash
make dev-build    # Build development images
make dev-up       # Start development services
make dev-down     # Stop development services
make dev-logs     # View development logs
make dev-worker   # Start Celery worker
make dev-beat     # Start Celery beat
make shell        # Access container shell
```

### Code Quality Commands
```bash
make test     # Run tests
make lint     # Run linting
make format   # Format code
```

## Environment Configuration

Create a `.env` file based on `env.example`:

```bash
# API Keys for LLM Providers
OPENROUTER_API_KEY=sk-or-your-key-here
CLAUDE_API_KEY=sk-ant-your-key-here
LM_STUDIO_URL=http://localhost:1234/v1

# Flask secret key
SECRET_KEY=your-secret-key-here-change-this-in-production
```

## Service Architecture

The application consists of several services:

- **Web (Flask)**: Main web application (port 5000 for production, 5001 for development)
- **Worker (Celery)**: Background task processing
- **Beat (Celery)**: Scheduled task execution
- **Redis**: Message broker and result backend (port 6379)
- **Flower**: Celery monitoring interface (port 5555)

## Development Workflow

### Using Dev Containers

1. **Code Changes**: All changes are automatically reflected due to volume mounting
2. **Dependencies**: Install new packages in the container, then update `requirements.txt`
3. **Database**: Use `flask init-db` to initialize/reset the database
4. **Testing**: Run `pytest` in the container
5. **Debugging**: Use VS Code's debugging features with the dev container

### Using Docker Compose

1. **Code Changes**: Restart the web service to see changes
2. **Dependencies**: Rebuild the image after updating requirements
3. **Logs**: Use `make dev-logs` to monitor all services

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 5000, 5555, and 6379 are available
2. **Permission issues**: The containers run as non-root users
3. **Database issues**: Use `make init-db` to reset the database
4. **Redis connection**: Ensure Redis is running and accessible

### Debugging

1. **Container logs**: `make dev-logs` or `docker-compose logs -f`
2. **Container shell**: `make shell` or `docker-compose exec app bash`
3. **Service status**: `docker-compose ps`

### Performance

- **Development**: Use volume mounts for fast code changes
- **Production**: Use multi-stage builds for smaller images
- **Caching**: Docker layer caching is optimized in the Dockerfiles

## Production Deployment

For production deployment:

1. **Environment**: Set `FLASK_ENV=production`
2. **Secrets**: Use proper secret management (not .env files)
3. **Database**: Consider using PostgreSQL instead of SQLite
4. **Monitoring**: Enable proper logging and monitoring
5. **Security**: Review and update security settings

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Dev Containers Documentation](https://containers.dev/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)
