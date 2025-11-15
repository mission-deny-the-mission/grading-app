import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_login import LoginManager
from werkzeug.exceptions import RequestEntityTooLarge

from models import db
from routes.api import api_bp
from routes.auth_routes import auth_bp
from routes.batches import batches_bp
from routes.config_routes import config_bp
from routes.sharing_routes import sharing_bp
from routes.usage_routes import usage_bp
# Import route blueprints
from routes.main import main_bp
from routes.templates import templates_bp
from routes.upload import upload_bp

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max file size

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.session_protection = 'strong'

# Session configuration (security & timeouts)
app.config['REMEMBER_COOKIE_SECURE'] = True  # HTTPS only in production
app.config['REMEMBER_COOKIE_HTTPONLY'] = True  # No JS access to cookie
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JS access to cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes idle timeout

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

# Flask-Login user_loader callback (will be properly configured after User model is available)
@login_manager.user_loader
def load_user(user_id):
    """Load user from database for Flask-Login session management."""
    from models import User
    return User.query.get(user_id)

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(api_bp)
app.register_blueprint(batches_bp)
app.register_blueprint(templates_bp)

# Register authentication and configuration blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(config_bp)
app.register_blueprint(usage_bp)
app.register_blueprint(sharing_bp)

# Initialize authentication middleware
from middleware.auth_middleware import init_auth_middleware
init_auth_middleware(app)

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
