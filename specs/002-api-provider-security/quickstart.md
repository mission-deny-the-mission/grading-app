# Quick Start: API Provider Security Implementation

**Feature**: 002-api-provider-security
**Date**: 2025-01-15
**Target Audience**: Developers implementing the security enhancements

## Overview

This guide walks you through implementing API key encryption, validation, error handling, and UI improvements for the grading application. Follow steps in order for successful implementation.

---

## Prerequisites

- Python ≥3.9 installed
- Existing grading-app-main repository cloned
- Virtual environment activated
- PostgreSQL (optional, for production testing)

---

## Step 1: Install Dependencies

### 1.1 Add to requirements.txt
```bash
# Add these lines to requirements.txt
cryptography>=41.0.0
Flask-Migrate>=4.0.0
```

### 1.2 Install packages
```bash
pip install -r requirements.txt
```

### 1.3 Verify installation
```bash
python -c "from cryptography.fernet import Fernet; print('cryptography OK')"
python -c "from flask_migrate import Migrate; print('Flask-Migrate OK')"
```

---

## Step 2: Generate Encryption Key

### 2.1 Run key generator
```bash
python -c "from cryptography.fernet import Fernet; print(f'DB_ENCRYPTION_KEY={Fernet.generate_key().decode()}')"
```

### 2.2 Add to environment
```bash
# .env file
DB_ENCRYPTION_KEY=your_generated_key_here

# IMPORTANT: Never commit this key to version control!
# Add .env to .gitignore if not already present
```

### 2.3 Test key loading
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Key loaded' if os.getenv('DB_ENCRYPTION_KEY') else 'Key missing')"
```

---

## Step 3: Create Encryption Utilities

### 3.1 Create utils/encryption.py
```python
"""
Encryption utilities for API key storage.
"""
import os
from cryptography.fernet import Fernet

def get_encryption_key():
    """Get encryption key from environment."""
    key = os.getenv('DB_ENCRYPTION_KEY')
    if not key:
        raise ValueError(
            "DB_ENCRYPTION_KEY not set in environment. "
            "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return key.encode()

def encrypt_value(value):
    """Encrypt a string value."""
    if not value:
        return None
    cipher = Fernet(get_encryption_key())
    return cipher.encrypt(value.encode()).decode()

def decrypt_value(encrypted):
    """Decrypt an encrypted string."""
    if not encrypted:
        return None
    cipher = Fernet(get_encryption_key())
    try:
        return cipher.decrypt(encrypted.encode()).decode()
    except Exception as e:
        raise ValueError(f"Decryption failed: {type(e).__name__}")
```

### 3.2 Test encryption
```python
# test_encryption.py
from utils.encryption import encrypt_value, decrypt_value

# Test round-trip
original = "sk-test-key-12345"
encrypted = encrypt_value(original)
decrypted = decrypt_value(encrypted)

assert decrypted == original, "Encryption test failed!"
print("✅ Encryption test passed")
```

---

## Step 4: Update Config Model

### 4.1 Modify models.py
Add property-based encryption to Config model:

```python
class Config(db.Model):
    # ... existing code ...

    # Change field names to private (prefix with _)
    _openrouter_api_key = db.Column('openrouter_api_key', db.String(500))
    _claude_api_key = db.Column('claude_api_key', db.String(500))
    # ... repeat for all API key fields

    # Add properties
    @property
    def openrouter_api_key(self):
        """Get decrypted OpenRouter API key."""
        from utils.encryption import decrypt_value
        return decrypt_value(self._openrouter_api_key)

    @openrouter_api_key.setter
    def openrouter_api_key(self, value):
        """Set encrypted OpenRouter API key."""
        from utils.encryption import encrypt_value
        self._openrouter_api_key = encrypt_value(value)

    # ... repeat for all API key properties
```

### 4.2 Test model changes
```python
# Test in Python shell
from app import app, db
from models import Config

with app.app_context():
    config = Config.query.first()

    # Test encryption
    config.openrouter_api_key = "sk-test-key"
    db.session.commit()

    # Reload and verify
    config = Config.query.first()
    print(f"Decrypted: {config.openrouter_api_key}")
    print(f"Encrypted (DB): {config._openrouter_api_key}")
```

---

## Step 5: Add API Key Validation

### 5.1 Add to utils/llm_providers.py
```python
import re

# API key validation patterns
API_KEY_PATTERNS = {
    'openrouter': r'^sk-or-v1-[A-Za-z0-9]{64}$',
    'claude': r'^sk-ant-api03-[A-Za-z0-9_-]{95}$',
    'openai': r'^sk-[A-Za-z0-9]{48}$',
    'gemini': r'^[A-Za-z0-9_-]{39}$',
    # ... add all providers
}

def validate_api_key_format(provider, key):
    """Validate API key format for provider."""
    if not key:
        return True, None  # Empty is valid
    pattern = API_KEY_PATTERNS.get(provider)
    if not pattern:
        return True, None  # No pattern defined
    if not re.match(pattern, key):
        return False, f"Invalid {provider} API key format"
    return True, None
```

### 5.2 Update routes/main.py save_config
```python
@main_bp.route("/save_config", methods=["POST"])
def save_config():
    # ... existing code ...

    # Add validation before saving
    errors = []
    for provider in ['openrouter', 'claude', 'gemini', ...]:
        key = request.form.get(f"{provider}_api_key", "").strip()
        if key:
            valid, error = validate_api_key_format(provider, key)
            if not valid:
                errors.append(error)

    if errors:
        return jsonify({"success": False, "message": ", ".join(errors)})

    # ... rest of save logic ...
```

---

## Step 6: Standardize Error Handling

### 6.1 Add LLMProviderError class
```python
# In utils/llm_providers.py

class LLMProviderError(Exception):
    """Standardized LLM provider error."""

    ERROR_TYPES = {
        'AUTH': 'authentication',
        'RATE_LIMIT': 'rate_limit',
        'TIMEOUT': 'timeout',
        'NOT_FOUND': 'not_found',
        'SERVER_ERROR': 'server_error',
        'UNKNOWN': 'unknown'
    }

    def __init__(self, error_type, message, provider, http_status=None):
        self.error_type = error_type
        self.message = message
        self.provider = provider
        self.http_status = http_status
        super().__init__(self.message)

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return {
            "success": False,
            "error": self.message,
            "error_type": self.error_type,
            "provider": self.provider,
            "http_status": self.http_status,
            "remediation": self._get_remediation()
        }

    def _get_remediation(self):
        """Get remediation suggestion."""
        remediation_map = {
            'authentication': "Verify your API key is correct and not expired",
            'rate_limit': "Wait a few minutes or check your account limits",
            'timeout': "Check network connectivity or try again later",
            # ... add all error types
        }
        return remediation_map.get(self.error_type, "Contact support")
```

### 6.2 Update provider implementations
```python
# In each provider's grade_document method
try:
    response = requests.post(...)
    response.raise_for_status()
except requests.exceptions.Timeout:
    raise LLMProviderError('TIMEOUT', "Request timed out", "ProviderName")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        raise LLMProviderError('AUTH', "Authentication failed", "ProviderName", 401)
    # ... handle other status codes
```

---

## Step 7: Run Migration

### 7.1 Create migration script
```python
# migrations/encrypt_api_keys.py
"""One-time migration to encrypt existing API keys."""

import os
import sys
from app import app, db
from models import Config
from utils.encryption import encrypt_value

def migrate():
    """Encrypt all plaintext API keys."""
    if not os.getenv('DB_ENCRYPTION_KEY'):
        print("ERROR: DB_ENCRYPTION_KEY not set")
        sys.exit(1)

    with app.app_context():
        config = Config.query.first()
        if not config:
            print("No configuration to migrate")
            return

        # Check if already encrypted
        if config._openrouter_api_key and config._openrouter_api_key.startswith('gAAAAA'):
            print("Keys already encrypted")
            return

        # Encrypt each key
        for field in ['openrouter', 'claude', 'gemini', 'openai', ...]:
            attr = f'_{field}_api_key'
            value = getattr(config, attr, None)
            if value and not value.startswith('gAAAAA'):
                encrypted = encrypt_value(value)
                setattr(config, attr, encrypted)
                print(f"Encrypted {field}_api_key")

        db.session.commit()
        print("✅ Migration complete!")

if __name__ == '__main__':
    migrate()
```

### 7.2 Run migration
```bash
python migrations/encrypt_api_keys.py
```

---

## Step 8: Add UI Improvements

### 8.1 Add provider badges to config.html
```html
<!-- For each cloud provider -->
<div class="mb-4 provider-section cloud">
    <h6 class="fw-bold text-primary">
        <i class="fas fa-cloud me-2"></i>OpenRouter API
        <span class="badge bg-primary ms-2">Cloud API</span>
        <span class="badge bg-success ms-1">Pay-per-use</span>
    </h6>
    <!-- ... rest of config section -->
</div>

<!-- For local providers -->
<div class="mb-4 provider-section local">
    <h6 class="fw-bold text-primary">
        <i class="fas fa-server me-2"></i>LM Studio
        <span class="badge bg-secondary ms-2">Local Only</span>
        <span class="badge bg-info ms-1">Self-hosted</span>
    </h6>
    <!-- ... rest of config section -->
</div>
```

### 8.2 Add import/export buttons
```html
<!-- Add after existing config buttons -->
<div class="btn-group w-100 mt-2">
    <button type="button" class="btn btn-outline-info" onclick="exportConfig()">
        <i class="fas fa-file-export me-2"></i>Export Configuration
    </button>
    <label class="btn btn-outline-info" for="import-config-file">
        <i class="fas fa-file-import me-2"></i>Import Configuration
        <input type="file" id="import-config-file" accept=".json"
               style="display:none" onchange="importConfig(this.files[0])">
    </label>
</div>
```

### 8.3 Add ARIA labels
```html
<button
    type="button"
    onclick="togglePassword('openrouter_api_key')"
    aria-label="Toggle OpenRouter API key visibility"
    aria-pressed="false">
    <i class="fas fa-eye" aria-hidden="true"></i>
</button>
```

---

## Step 9: Testing

### 9.1 Run unit tests
```bash
pytest tests/test_encryption.py -v
pytest tests/test_validation.py -v
pytest tests/test_models.py -k Config -v
```

### 9.2 Run integration tests
```bash
pytest tests/test_config_routes.py -v
```

### 9.3 Manual testing checklist
- [ ] Save API key → verify encrypted in DB
- [ ] Load config page → verify keys decrypted and masked
- [ ] Test invalid key format → verify validation error shown
- [ ] Test "Test Key" button → verify actual API call
- [ ] Export configuration → verify JSON downloaded
- [ ] Import configuration → verify form populated
- [ ] Keyboard-only navigation → verify all fields accessible
- [ ] Screen reader → verify ARIA labels announced

---

## Step 10: Deployment

### 10.1 Production checklist
- [ ] `DB_ENCRYPTION_KEY` set in production environment
- [ ] Backup database before migration
- [ ] Run migration on copy of production DB (dry run)
- [ ] Verify migration succeeded (test config load)
- [ ] Run migration on production DB
- [ ] Verify application starts successfully
- [ ] Test API key functionality
- [ ] Monitor logs for decryption errors

### 10.2 Rollback plan
```bash
# If migration fails, restore from backup
psql grading_app < backup_before_migration.sql

# Remove DB_ENCRYPTION_KEY to prevent startup errors
unset DB_ENCRYPTION_KEY

# Revert code changes
git revert [commit-hash]
```

---

## Troubleshooting

### Issue: "DB_ENCRYPTION_KEY not set"
**Solution**: Add key to `.env` file or environment variables

### Issue: "Decryption failed"
**Solution**: Verify `DB_ENCRYPTION_KEY` matches key used for encryption

### Issue: "Invalid API key format"
**Solution**: Check API_KEY_PATTERNS regex matches provider's actual format

### Issue: Migration script fails
**Solution**:
1. Check DB connection
2. Verify `DB_ENCRYPTION_KEY` is set
3. Check database logs for errors
4. Restore from backup and retry

---

## Development Workflow

### TDD Cycle
1. **Write test** for new functionality (red)
2. **Implement** minimal code to pass test (green)
3. **Refactor** while keeping tests passing
4. **Repeat** for each feature

### Example: Adding new provider
```python
# 1. Add test
def test_newprovider_key_validation():
    valid, error = validate_api_key_format('newprovider', 'np-valid-key')
    assert valid

# 2. Implement
API_KEY_PATTERNS['newprovider'] = r'^np-[A-Za-z0-9]{32}$'

# 3. Verify test passes
pytest tests/test_validation.py::test_newprovider_key_validation -v
```

---

## Next Steps

After completing quickstart:
1. Review `plan.md` for detailed implementation plan
2. Run `/speckit.tasks` to generate task breakdown
3. Follow task order for systematic implementation
4. Submit PR when tests pass and coverage ≥80%

---

## Resources

- [Feature Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/)
- [Cryptography Docs](https://cryptography.io/en/latest/fernet/)
- [Flask-Migrate Docs](https://flask-migrate.readthedocs.io/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

**Document Status**: ✅ **Complete** - Ready for implementation
**Estimated Time**: 8-12 hours for full implementation
**Complexity**: Medium (encryption + migration + UI)
