import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

try:
    from flask_migrate import Migrate
    FLASK_MIGRATE_AVAILABLE = True
except ImportError:
    FLASK_MIGRATE_AVAILABLE = False

from models import db
from routes.api import api_bp
from routes.batches import batches_bp
# Import route blueprints
from routes.main import main_bp
from routes.templates import templates_bp
from routes.upload import upload_bp
# Import grading scheme blueprints
from routes.schemes import schemes_bp
from routes.grading import grading_bp
from routes.export import export_bp
from routes.schemes_ui import schemes_ui_bp
from routes.grading_ui import grading_ui_bp

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max file size

# Database configuration (use absolute path for SQLite to avoid CWD-related resets)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "grading_app.db")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}"
)

# Ensure we use the main database file, not the instance folder
app.instance_path = BASE_DIR
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Initialize Flask-Migrate for database migrations (optional)
if FLASK_MIGRATE_AVAILABLE:
    migrate = Migrate(app, db)

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(api_bp)
app.register_blueprint(batches_bp)
app.register_blueprint(templates_bp)
# Register grading scheme blueprints
app.register_blueprint(schemes_bp)
app.register_blueprint(grading_bp)
app.register_blueprint(export_bp)
app.register_blueprint(schemes_ui_bp)
app.register_blueprint(grading_ui_bp)

# Configure upload folder
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Expose configuration values for tests that patch module-level variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

# Backward-compatible endpoint aliases for templates/tests expecting app-level endpoints
try:
    app.add_url_rule(
        "/create_batch",
        endpoint="create_batch",
        view_func=app.view_functions["batches.create_batch"],
        methods=["POST"],
    )
    app.add_url_rule(
        "/batches",
        endpoint="batches",
        view_func=app.view_functions["batches.batches"],
        methods=["GET"],
    )
except Exception:
    # If blueprints not registered or endpoints missing, ignore in non-server contexts
    pass


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({"error": "File too large. Maximum size is 100MB."}), 413


@app.cli.command("init-db")
def init_db():
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        print("Database initialized!")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)


# Optional app factory for external consumers (keeps compatibility with tests importing app)


def create_app():
    return app
