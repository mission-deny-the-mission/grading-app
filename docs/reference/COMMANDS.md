# Grading App Commands Guide

Fixed and improved command execution for testing and development.

## Quick Start

### Option 1: Using Wrapper Scripts (Recommended)

Works anywhere in the project, automatically handles nix-shell:

```bash
# Run tests
./bin/run-tests

# Start Flask development server
./bin/flask-app

# Start Celery worker (in another terminal)
./bin/celery-worker

# Start Celery beat scheduler (in another terminal)
./bin/celery-beat

# Start all three services at once
./bin/start-all
```

### Option 2: Inside nix-shell (With Functions)

Enter the development shell and use functions directly:

```bash
# Enter the development environment
nix-shell

# Now you can use these commands directly:
flask-app       # Start Flask development server
celery-worker   # Start Celery worker
celery-beat     # Start Celery beat scheduler
start-all       # Start all services
```

### Option 3: Using nix-shell with --run

Run commands directly without entering shell:

```bash
# Run tests
nix-shell --run "python3 -m pytest tests/ -v"

# Start Flask
nix-shell --run "python app.py"

# Run with coverage
nix-shell --run "python3 -m pytest --cov=. tests/"
```

## Available Commands

### Testing

```bash
# Run all tests
./bin/run-tests

# Run specific test file
./bin/run-tests tests/test_models.py -v

# Run with coverage
./bin/run-tests --cov=. tests/

# Run specific test class
./bin/run-tests tests/test_tasks.py::TestProcessJob -v
```

### Development Services

```bash
# Flask development server (http://localhost:5000)
./bin/flask-app

# Celery worker (processes background jobs)
./bin/celery-worker

# Celery beat (scheduler for periodic tasks)
./bin/celery-beat

# All three services at once
./bin/start-all
```

### Manual Service Control

```bash
# Stop all services
./stop-services.sh

# Or manually kill processes
pkill -f "python app.py"
pkill -f "celery worker"
pkill -f "celery beat"
```

## Running Services in Parallel

For development, you typically want to run these in separate terminal windows:

**Terminal 1 - Flask:**
```bash
./bin/flask-app
```

**Terminal 2 - Celery Worker:**
```bash
./bin/celery-worker
```

**Terminal 3 - Celery Beat:**
```bash
./bin/celery-beat
```

Or all at once:
```bash
./bin/start-all
```

## Environment Setup

When you enter `nix-shell`, these services are automatically started:
- PostgreSQL on `localhost:5433`
- Redis on `localhost:6379`

Environment variables are automatically set:
- `FLASK_ENV=development`
- `FLASK_DEBUG=1`
- `DATABASE_URL=postgresql://$USER@localhost:5433/grading_app`
- `REDIS_HOST=localhost`
- `REDIS_PORT=6379`

## How It Works

### Wrapper Scripts (`./bin/*`)

These scripts intelligently:
1. Check if you're already in a nix-shell environment
2. If YES: Run the command directly using the current environment's Python/dependencies
3. If NO: Automatically wrap the command with `nix-shell --run` to provide the proper environment

This means you can use them from anywhere and they'll always work.

### Shell Functions (inside nix-shell)

When you enter `nix-shell`, shell functions are defined for convenience:
- `flask-app`
- `celery-worker`
- `celery-beat`
- `start-all`

These functions are only available in interactive shell sessions.

## Troubleshooting

### Commands not found outside nix-shell

Use the `./bin/` wrapper scripts instead. They automatically handle the nix-shell environment.

### Services not starting

1. Make sure you're in a nix-shell or using the `./bin/` scripts
2. Check that PostgreSQL and Redis started: `ps aux | grep -E "postgres|redis"`
3. Verify environment variables: `nix-shell --run "env | grep FLASK"`

### Tests hanging

1. Stop any running services: `./stop-services.sh`
2. Clear Redis: `redis-cli flushall`
3. Check for stuck jobs: `redis-cli llen celery`

### Port already in use

If you get "Address already in use" errors:

```bash
# Kill existing Flask processes
pkill -f "python app.py"

# Kill existing Celery processes
pkill -f celery

# Restart Redis
pkill redis-server
redis-server --daemonize yes --port 6379
```

## Development Workflow

```bash
# 1. Enter development environment (or just use ./bin scripts)
nix-shell

# 2. Run tests before making changes
./bin/run-tests

# 3. Start services for development
./bin/flask-app &
./bin/celery-worker &
./bin/celery-beat &

# 4. Make your changes

# 5. Test your changes
./bin/run-tests

# 6. Stop services when done
./stop-services.sh
```

## Notes

- All scripts are in `./bin/` for easy access
- Scripts automatically handle the nix-shell environment
- Services are cleaned up when you exit nix-shell
- Database and Redis data persist across sessions
- Use `Ctrl+C` to stop individual services

