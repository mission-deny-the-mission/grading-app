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
    beautifulsoup4

    # Desktop dependencies
    pywebview
    pystray
    apscheduler
    keyring
    pillow

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

    # Desktop app dependencies
    gtk3
    gobject-introspection
    wrapGAppsHook3

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

    # Set up shell aliases
    alias celery-worker="celery -A tasks worker --loglevel=info --concurrency=1 --queues=grading,maintenance"
    alias celery-beat="celery -A tasks beat --loglevel=info"
    alias flask-app="python app.py"
    alias start-all="python app.py & celery -A tasks worker --loglevel=info --concurrency=1 --queues=grading,maintenance & celery -A tasks beat --loglevel=info"

    echo "Development environment ready!"
    echo ""
    echo "Available aliases:"
    echo "  - flask-app: Start the Flask application"
    echo "  - celery-worker: Start Celery worker"
    echo "  - celery-beat: Start Celery beat scheduler"
    echo "  - start-all: Start all three services (Flask, Celery worker, Celery beat)"
  '';

}
