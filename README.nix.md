# Nix Development Environment

This project includes a Nix development environment that sets up all required services and dependencies.

## Prerequisites

- [Nix package manager](https://nixos.org/download.html) installed on your system

## Quick Start

### Using `nix-shell`

```bash
# Enter the development environment
nix-shell

# Or if you have flakes enabled:
nix develop
```

### Using `direnv` (recommended)

1. Install direnv:
   ```bash
   # On NixOS: nix-shell -p direnv
   # On other systems: follow https://direnv.net/docs/installation.html
   ```

2. Add to your shell config (e.g., `~/.bashrc` or `~/.zshrc`):
   ```bash
   eval "$(direnv hook bash)"  # or zsh/fish
   ```

3. Create `.envrc` file:
   ```bash
   echo "use nix" > .envrc
   direnv allow
   ```

Now when you `cd` into the project directory, the environment will be automatically loaded.

## Services

The Nix environment automatically starts these services:

- **PostgreSQL**: localhost:5432 (database: `grading_app`, user: `postgres`)
- **Redis**: localhost:6379

## Environment Variables

The environment sets up these default variables:

```bash
FLASK_ENV=development
FLASK_DEBUG=1
DATABASE_URL=sqlite:///grading_app.db
SECRET_KEY=dev-secret-key-change-in-production
REDIS_HOST=localhost
REDIS_PORT=6379
LM_STUDIO_URL=http://localhost:1234/v1
PYTHONPATH=$(pwd)
```

## Usage

Once in the development environment:

### Start the Flask application
```bash
python app.py
```

### Start Celery worker
```bash
celery -A tasks worker --loglevel=info --concurrency=1 --queues=grading,maintenance
```

### Start Celery beat scheduler
```bash
celery -A tasks beat --loglevel=info
```

### Stop services manually
```bash
./stop-services.sh
```

### Run tests
```bash
pytest
```

### Run linting
```bash
black .
flake8 .
isort .
```

## Database Options

The environment supports both SQLite and PostgreSQL:

- **SQLite** (default): `DATABASE_URL=sqlite:///grading_app.db`
- **PostgreSQL**: `DATABASE_URL=postgresql://postgres@localhost:5432/grading_app`

To use PostgreSQL, set the environment variable:
```bash
export DATABASE_URL=postgresql://postgres@localhost:5432/grading_app
```

## Service Management

Services are automatically:
- Started when entering the shell
- Stopped when exiting the shell
- Managed with data persistence in `.postgres_data/`

## Troubleshooting

### Port conflicts
If ports are already in use, the environment will show warnings. You can:
1. Stop existing services using those ports
2. Modify the port numbers in the shell configuration

### Database issues
If PostgreSQL fails to start:
```bash
# Remove corrupted data and restart
rm -rf .postgres_data
exit  # Then re-enter nix-shell
```

### Redis issues
If Redis fails to start:
```bash
# Kill any existing Redis processes
pkill redis-server
# Then restart the shell
```

## Development Tools

The environment includes:
- **Python** with all project dependencies
- **PostgreSQL** database server
- **Redis** for Celery
- **Development tools**: black, flake8, isort, pylint, pytest
- **Debugging tools**: ipdb, debugpy
- **Monitoring**: flower for Celery

## Production Deployment

For production, consider using:
- NixOS modules for service management
- Systemd services for PostgreSQL and Redis
- Environment-specific configuration files
- Proper secret management

See the main README.md for production deployment instructions.