"""Shared limiter module to avoid circular imports."""

# Import limiter here to avoid circular imports
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    FLASK_LIMITER_AVAILABLE = True
except ImportError:
    FLASK_LIMITER_AVAILABLE = False
    # Mock classes for when Flask-Limiter is not available
    class Limiter:
        def __init__(self, *args, **kwargs):
            pass
        
        def limit(self, *args, **kwargs):
            """Return a no-op decorator."""
            def decorator(func):
                return func
            return decorator

    def get_remote_address():
        return "127.0.0.1"

# Create a global limiter instance that can be imported
limiter = None

def init_limiter(app):
    """Initialize the limiter with the Flask app."""
    global limiter
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per day", "100 per hour"],
        storage_uri="memory://",
        strategy="fixed-window",
    )
    
    return limiter