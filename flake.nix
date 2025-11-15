{
  description = "Grading App Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          flask
          flask-migrate
          python-docx
          pypdf2
          requests
          python-dotenv
          werkzeug
          openai
          anthropic
          google-generativeai
          flask-sqlalchemy
          flask-migrate
          celery
          redis
          psycopg2-binary
          beautifulsoup4
          cryptography

          # Image processing dependencies
          pillow
          opencv4
          python-magic
          # Note: azure-cognitiveservices-vision-computervision and msrest
          # may need to be installed via pip in the shell

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
      {
        # Development shell
        devShells.default = pkgs.mkShell {
          name = "grading-app-dev";

          buildInputs = with pkgs; [
            pythonEnv
            redis
            postgresql
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
            export LM_STUDIO_URL=''${LM_STUDIO_URL:-http://localhost:1234/v1}
            export PYTHONPATH=$(pwd)
            export PATH="$(pwd)/bin:$PATH"

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

            # Set up shell functions (more reliable than aliases in Nix)
            flask-app() {
              python app.py "$@"
            }

            celery-worker() {
              celery -A tasks worker --loglevel=info --concurrency=1 --queues=grading,maintenance "$@"
            }

            celery-beat() {
              celery -A tasks beat --loglevel=info "$@"
            }

            start-all() {
              echo "Starting all services..."
              python app.py &
              celery -A tasks worker --loglevel=info --concurrency=1 --queues=grading,maintenance &
              celery -A tasks beat --loglevel=info
              wait
            }

            # Export functions for use in subshells
            export -f flask-app celery-worker celery-beat start-all

            echo "✓ Development environment ready!"
            echo ""
            echo "Services running:"
            echo "  - PostgreSQL: localhost:5433"
            echo "  - Redis: localhost:6379"
            echo ""
            echo "Available commands:"
            echo "  - flask-app       Start Flask development server"
            echo "  - celery-worker   Start Celery worker"
            echo "  - celery-beat     Start Celery beat scheduler"
            echo "  - start-all       Start all three services in parallel"
            echo "  - stop-services.sh Stop PostgreSQL and Redis"
            echo ""
            echo "Quick start:"
            echo "  flask-app        # in one terminal"
            echo "  celery-worker    # in another terminal"
            echo "  celery-beat      # in a third terminal"
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
        };

        # Package the Python environment for direct use
        packages.default = pythonEnv;
      });
}
