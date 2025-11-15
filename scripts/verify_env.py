#!/usr/bin/env python3
"""
Environment Validation Script

Validates all required environment variables, encryption key format,
database connectivity, and Redis connectivity before application startup.
"""

import os
import sys
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.BLUE}{'=' * 50}{Colors.NC}")
    print(f"{Colors.BLUE}  {text}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.NC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.NC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")


def validate_secret_key():
    """Validate SECRET_KEY environment variable."""
    print_header("SECRET_KEY Validation")

    secret_key = os.getenv("SECRET_KEY")
    flask_env = os.getenv("FLASK_ENV", "production")

    if not secret_key:
        print_error("SECRET_KEY not set")
        return False

    if secret_key == "your-secret-key-here":
        if flask_env == "production":
            print_error("SECRET_KEY is using default value in production")
            print_error("Generate a secure key with:")
            print_error("  python -c 'import secrets; print(secrets.token_hex(32))'")
            return False
        else:
            print_warning("SECRET_KEY is using default value (development mode)")
            return True

    if len(secret_key) < 32:
        print_error(f"SECRET_KEY too short: {len(secret_key)} < 32 characters")
        if flask_env == "production":
            return False
        else:
            print_warning("Continue anyway in development mode")
            return True

    print_success(f"SECRET_KEY is set ({len(secret_key)} characters)")
    return True


def validate_encryption_key():
    """Validate DB_ENCRYPTION_KEY environment variable."""
    print_header("DB_ENCRYPTION_KEY Validation")

    encryption_key = os.getenv("DB_ENCRYPTION_KEY")
    flask_env = os.getenv("FLASK_ENV", "production")

    if not encryption_key:
        if flask_env == "production":
            print_error("DB_ENCRYPTION_KEY not set (required in production)")
            print_error("Generate with:")
            print_error("  python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
            return False
        else:
            print_warning("DB_ENCRYPTION_KEY not set (development mode)")
            return True

    # Validate Fernet key format
    try:
        from cryptography.fernet import Fernet
        Fernet(encryption_key.encode())
        print_success(f"DB_ENCRYPTION_KEY is valid ({len(encryption_key)} characters)")

        # Test encryption/decryption
        fernet = Fernet(encryption_key.encode())
        test_data = b"test message"
        encrypted = fernet.encrypt(test_data)
        decrypted = fernet.decrypt(encrypted)

        if decrypted == test_data:
            print_success("Encryption/decryption test passed")
        else:
            print_error("Encryption test failed - decryption doesn't match")
            return False

        return True

    except ImportError:
        print_error("cryptography package not installed")
        print_error("Install with: pip install cryptography")
        return False
    except Exception as e:
        print_error(f"Invalid DB_ENCRYPTION_KEY format: {e}")
        return False


def validate_database():
    """Validate database configuration and connectivity."""
    print_header("Database Validation")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        # Check for default SQLite path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_db = os.path.join(base_dir, "grading_app.db")

        if os.path.exists(default_db):
            print_success(f"Using default SQLite database: {default_db}")
        else:
            print_warning("DATABASE_URL not set, using default SQLite path")
            print_warning(f"Database will be created at: {default_db}")

        return True

    print_success(f"DATABASE_URL is set")

    # Test database connectivity
    try:
        if database_url.startswith("sqlite:///"):
            db_path = database_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                print_success(f"SQLite database exists: {db_path}")

                # Test read access
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                conn.close()

                print_success(f"Database accessible ({len(tables)} tables found)")
                return True
            else:
                print_warning(f"SQLite database does not exist yet: {db_path}")
                print_warning("Database will be created on first run")
                return True

        elif database_url.startswith("postgresql://"):
            # Test PostgreSQL connection
            try:
                import psycopg2
                from urllib.parse import urlparse

                result = urlparse(database_url)
                username = result.username
                password = result.password
                database = result.path[1:]
                hostname = result.hostname
                port = result.port or 5432

                conn = psycopg2.connect(
                    database=database,
                    user=username,
                    password=password,
                    host=hostname,
                    port=port,
                    connect_timeout=5
                )

                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                conn.close()

                print_success(f"PostgreSQL connected: {version[0][:50]}...")
                return True

            except ImportError:
                print_error("psycopg2 not installed (required for PostgreSQL)")
                print_error("Install with: pip install psycopg2-binary")
                return False
            except Exception as e:
                print_error(f"PostgreSQL connection failed: {e}")
                return False

        else:
            print_warning(f"Unknown database type: {database_url[:20]}...")
            return True

    except Exception as e:
        print_error(f"Database validation error: {e}")
        return False


def validate_redis():
    """Validate Redis configuration and connectivity."""
    print_header("Redis Validation")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    print_success(f"REDIS_URL: {redis_url}")

    try:
        import redis

        client = redis.from_url(redis_url, decode_responses=True)

        # Test connection
        client.ping()
        print_success("Redis connection successful")

        # Test read/write
        test_key = "test:verify_env"
        test_value = f"test_{datetime.now().isoformat()}"

        client.setex(test_key, 10, test_value)  # 10 second expiration
        retrieved = client.get(test_key)

        if retrieved == test_value:
            print_success("Redis read/write test passed")
            client.delete(test_key)
        else:
            print_error("Redis read/write test failed")
            return False

        # Check memory info
        info = client.info("memory")
        used_memory_mb = info.get("used_memory", 0) / (1024 * 1024)
        print_success(f"Redis memory usage: {used_memory_mb:.2f} MB")

        return True

    except ImportError:
        print_error("redis package not installed")
        print_error("Install with: pip install redis")
        return False
    except redis.ConnectionError as e:
        print_error(f"Redis connection failed: {e}")
        print_warning("Password reset tokens will not work without Redis")
        print_warning("Start Redis with: redis-server")
        return False
    except Exception as e:
        print_error(f"Redis validation error: {e}")
        return False


def validate_flask_env():
    """Validate Flask environment configuration."""
    print_header("Flask Environment Validation")

    flask_env = os.getenv("FLASK_ENV", "production")

    print_success(f"FLASK_ENV: {flask_env}")

    if flask_env == "production":
        print_success("Production mode - strict security validation")
    else:
        print_warning("Development mode - relaxed validation")

    return True


def validate_required_packages():
    """Validate required Python packages are installed."""
    print_header("Required Packages Validation")

    required_packages = [
        "flask",
        "flask_login",
        "flask_limiter",
        "flask_wtf",
        "werkzeug",
        "email_validator",
        "cryptography",
        "redis",
        "sqlalchemy",
    ]

    all_installed = True

    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} installed")
        except ImportError:
            print_error(f"{package} NOT installed")
            all_installed = False

    if not all_installed:
        print_error("\nMissing packages detected")
        print_error("Install with: pip install -r requirements.txt")
        return False

    return True


def validate_file_permissions():
    """Validate critical file permissions."""
    print_header("File Permissions Validation")

    # Check .env file permissions if it exists
    if os.path.exists(".env"):
        stat_info = os.stat(".env")
        mode = oct(stat_info.st_mode)[-3:]

        if mode == "600" or mode == "400":
            print_success(f".env file permissions: {mode} (secure)")
        else:
            print_warning(f".env file permissions: {mode} (should be 600 or 400)")
            print_warning("Fix with: chmod 600 .env")

    # Check database file permissions if SQLite
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        if os.path.exists(db_path):
            stat_info = os.stat(db_path)
            mode = oct(stat_info.st_mode)[-3:]
            print_success(f"Database file permissions: {mode}")

    return True


def main():
    """Main validation function."""
    print_header("Grading App - Environment Validation")

    results = []

    # Run all validations
    results.append(("Flask Environment", validate_flask_env()))
    results.append(("Required Packages", validate_required_packages()))
    results.append(("SECRET_KEY", validate_secret_key()))
    results.append(("DB_ENCRYPTION_KEY", validate_encryption_key()))
    results.append(("Database", validate_database()))
    results.append(("Redis", validate_redis()))
    results.append(("File Permissions", validate_file_permissions()))

    # Summary
    print_header("Validation Summary")

    total = len(results)
    passed = sum(1 for _, result in results if result)
    failed = total - passed

    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.NC}" if result else f"{Colors.RED}FAIL{Colors.NC}"
        print(f"{name:.<40} {status}")

    print()

    if failed == 0:
        print_success(f"All validations passed ({passed}/{total})")
        print_success("Environment is ready for production")
        return 0
    else:
        print_error(f"{failed} validation(s) failed ({passed}/{total} passed)")

        flask_env = os.getenv("FLASK_ENV", "production")
        if flask_env == "production":
            print_error("Production environment - must fix all errors")
            return 1
        else:
            print_warning("Development environment - some errors may be acceptable")
            return 0


if __name__ == "__main__":
    sys.exit(main())
