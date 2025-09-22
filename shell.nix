{ pkgs ? import <nixpkgs> {} }:

let
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    flask
    python-docx
    pypdf2
    requests
    python-dotenv
    werkzeug
    openai
    anthropic
    google-generativeai
    flask-sqlalchemy
    celery
    redis
    psycopg2-binary
    
    # Development dependencies
    black
    flake8
    isort
    pylint
    pytest
    pytest-cov
    pytest-flask
    ipython
    ipdb
    debugpy
    flower
  ]);
in
pkgs.mkShell {
  name = "grading-app-dev";

  buildInputs = with pkgs; [
    pythonEnv
    redis
    postgresql
    
    # Additional useful tools
    git
    gnumake
    which
  ];

  shellHook = ''
    # Set up environment variables
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    export DATABASE_URL=postgresql://$USER@localhost:5433/grading_app
    export SECRET_KEY=dev-secret-key-change-in-production
    export REDIS_HOST=localhost
    export REDIS_PORT=6379
    export LM_STUDIO_URL="$\{LM_STUDIO_URL:-http://localhost:1234/v1}"
    export PYTHONPATH=$(pwd)
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
      echo "Creating .env file with defaults..."
      cat > .env << EOF
FLASK_ENV=development
FLASK_DEBUG=1
DATABASE_URL=postgresql://$USER@localhost:5433/grading_app
SECRET_KEY=dev-secret-key-change-in-production
REDIS_HOST=localhost
REDIS_PORT=6379
LM_STUDIO_URL=http://localhost:1234/v1
PYTHONPATH=$(pwd)
EOF
    fi

    # Initialize PostgreSQL if not already done
    if [ ! -d "$PWD/.postgres_data" ]; then
      echo "Initializing PostgreSQL data directory..."
      mkdir -p .postgres_data
      initdb -D .postgres_data --auth=trust
      echo "host all all all trust" >> .postgres_data/pg_hba.conf
      echo "listen_addresses = 'localhost'" >> .postgres_data/postgresql.conf
      echo "port = 5433" >> .postgres_data/postgresql.conf
      echo "unix_socket_directories = '$PWD/.postgres_data'" >> .postgres_data/postgresql.conf
    fi

    # Start PostgreSQL in background
    if ! pg_ctl status -D .postgres_data > /dev/null 2>&1; then
      echo "Starting PostgreSQL..."
      pg_ctl -D .postgres_data -l .postgres_log start
      sleep 2
      
      # Create database if it doesn't exist
      if ! psql -h localhost -p 5433 -U $USER -lqt | cut -d \| -f 1 | grep -qw grading_app; then
        echo "Creating grading_app database..."
        createdb -h localhost -p 5433 -U $USER grading_app
      fi
    fi

    # Start Redis in background
    if ! pgrep redis-server > /dev/null; then
      echo "Starting Redis..."
      redis-server --daemonize yes --port 6379
    fi

    # Create a script to stop services
    cat > stop-services.sh << 'EOF'
#!/bin/bash
echo "Stopping PostgreSQL..."
pg_ctl -D .postgres_data stop
echo "Stopping Redis..."
pkill redis-server
echo "Services stopped."
EOF
    chmod +x stop-services.sh

    echo "Development environment ready!"
    echo ""
    echo "Services running:"
    echo "  - PostgreSQL: localhost:5433"
    echo "  - Redis: localhost:6379"
    echo ""
    echo "To start the Flask app: python app.py"
    echo "To start Celery worker: celery -A tasks worker --loglevel=info --concurrency=1 --queues=grading,maintenance"
    echo "To start Celery beat: celery -A tasks beat --loglevel=info"
    echo "To stop services: ./stop-services.sh"
    echo ""
    echo "Note: Services will be stopped when you exit the shell"
  '';

  # Cleanup services when shell exits
  exitHook = ''
    echo "Stopping services..."
    if [ -d .postgres_data ]; then
      pg_ctl -D .postgres_data stop 2>/dev/null || true
    fi
    pkill redis-server 2>/dev/null || true
    echo "Services stopped."
  '';
}