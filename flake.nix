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

          # Desktop dependencies
          pywebview
          pystray
          apscheduler
          keyring
          pygobject3

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

            # Desktop app system dependencies
            gtk3
            gobject-introspection
            wrapGAppsHook3
            webkitgtk_4_1

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
            export LM_STUDIO_URL=''${LM_STUDIO_URL:-http://localhost:1234/v1}
            export PYTHONPATH=$(pwd)
            export PATH="$(pwd)/bin:$PATH"

            # GTK/GObject introspection for PyWebView
            export GI_TYPELIB_PATH="${pkgs.gtk3}/lib/girepository-1.0:${pkgs.webkitgtk_4_1}/lib/girepository-1.0"
            export LD_LIBRARY_PATH="${pkgs.gtk3}/lib:${pkgs.webkitgtk_4_1}/lib:''${LD_LIBRARY_PATH:-}"

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
            echo "Available commands:"
            echo "  - flask-app       Start Flask development server"
            echo "  - celery-worker   Start Celery worker"
            echo "  - celery-beat     Start Celery beat scheduler"
            echo "  - start-all       Start all three services in parallel"
            echo ""
            echo "Quick start:"
            echo "  flask-app        # in one terminal"
            echo "  celery-worker    # in another terminal"
            echo "  celery-beat      # in a third terminal"
          '';

        };

        # Package the Python environment for direct use
        packages.default = pythonEnv;
      });
}
