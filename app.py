import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

try:
    from flask_login import LoginManager
    FLASK_LOGIN_AVAILABLE = True
except ImportError:
    FLASK_LOGIN_AVAILABLE = False
    # Create a no-op LoginManager for testing
    class LoginManager:
        def __init__(self):
            self.login_view = None
            self.session_protection = None
        def init_app(self, app):
            pass
        def user_loader(self, func):
            return func

# Optional imports for rate limiting and CSRF protection
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    FLASK_LIMITER_AVAILABLE = True
except ImportError:
    FLASK_LIMITER_AVAILABLE = False

try:
    from flask_wtf.csrf import CSRFProtect
    CSRF_PROTECT_AVAILABLE = True
except ImportError:
    CSRF_PROTECT_AVAILABLE = False

try:
    from flask_migrate import Migrate
    FLASK_MIGRATE_AVAILABLE = True
except ImportError:
    FLASK_MIGRATE_AVAILABLE = False

from models import db
# Import blueprints that don't depend on limiter - these go after limiter initialization
from routes.api import api_bp
from routes.batches import batches_bp
from routes.config_routes import config_bp
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
# Import desktop settings blueprint
from routes.desktop_settings import desktop_settings_bp
from routes.desktop_data import desktop_data_bp
# admin_routes, auth_routes, sharing_routes, usage_routes are imported after limiter is initialized

load_dotenv()

app = Flask(__name__, template_folder="templates")

# SECRET_KEY validation - CRITICAL SECURITY
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
FLASK_ENV = os.getenv("FLASK_ENV", "production")

# In production, SECRET_KEY must be properly set
if FLASK_ENV == "production":
    if SECRET_KEY == "your-secret-key-here" or not SECRET_KEY or len(SECRET_KEY) < 32:
        raise ValueError(
            "CRITICAL SECURITY ERROR: SECRET_KEY must be set to a secure random value in production. "
            "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )

# In development, warn if using default key
if FLASK_ENV != "production" and SECRET_KEY == "your-secret-key-here":
    print("WARNING: Using default SECRET_KEY. Generate a secure key for production.")

app.secret_key = SECRET_KEY

# DB_ENCRYPTION_KEY validation - CRITICAL SECURITY
# Validate encryption key at startup to fail fast if misconfigured
if FLASK_ENV == "production":
    DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")
    if not DB_ENCRYPTION_KEY:
        raise ValueError(
            "CRITICAL SECURITY ERROR: DB_ENCRYPTION_KEY must be set in production. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    # Validate key format
    try:
        from cryptography.fernet import Fernet
        Fernet(DB_ENCRYPTION_KEY.encode())
    except Exception as e:
        raise ValueError(
            f"CRITICAL SECURITY ERROR: DB_ENCRYPTION_KEY is invalid: {e}. "
            "Generate a new one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

# In development, warn if encryption key is missing
if FLASK_ENV != "production" and not os.getenv("DB_ENCRYPTION_KEY"):
    print("WARNING: DB_ENCRYPTION_KEY not set. Encryption features will fail. Generate one for development.")

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max file size

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.session_protection = 'strong'

# Session configuration (security & timeouts)
# Cookie security flags based on environment (HTTPS required in production, optional in dev)
IS_PRODUCTION = FLASK_ENV == "production"
app.config['REMEMBER_COOKIE_SECURE'] = IS_PRODUCTION  # HTTPS only in production
app.config['REMEMBER_COOKIE_HTTPONLY'] = True  # No JS access to cookie (always enforced)
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JS access to cookie (always enforced)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection (always enforced)
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

# Initialize Flask-Migrate for database migrations (optional)
if FLASK_MIGRATE_AVAILABLE:
    migrate = Migrate(app, db)

# Initialize CSRF protection (optional)
csrf = None
if CSRF_PROTECT_AVAILABLE:
    csrf = CSRFProtect(app)

# Initialize rate limiter BEFORE importing blueprints to avoid circular imports (optional)
class NoOpLimiter:
    """No-op limiter for when Flask-Limiter is not available."""
    def limit(self, *args, **kwargs):
        """Return a no-op decorator."""
        def decorator(func):
            return func
        return decorator

if FLASK_LIMITER_AVAILABLE:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per day", "100 per hour"],
        storage_uri="memory://",
        strategy="fixed-window"
    )
else:
    limiter = NoOpLimiter()

# Flask-Login user_loader callback (will be properly configured after User model is available)
@login_manager.user_loader
def load_user(user_id):
    """Load user from database for Flask-Login session management."""
    from models import User
    return User.query.get(user_id)

# NOW import blueprints that depend on limiter (after limiter is initialized)
from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.sharing_routes import sharing_bp
from routes.usage_routes import usage_bp

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

# Register desktop settings blueprint
app.register_blueprint(desktop_settings_bp)
app.register_blueprint(desktop_data_bp)

# Register authentication and configuration blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
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
