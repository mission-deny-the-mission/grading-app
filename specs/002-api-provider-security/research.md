# Technical Research: API Provider Security & UX Improvements

**Feature**: 002-api-provider-security
**Date**: 2025-01-15
**Research Phase**: Phase 0 - Technology Selection and Best Practices

## Overview

This document captures technical decisions, alternatives considered, and best practices research for implementing secure API key storage, validation, error handling, and accessibility improvements in the grading application.

---

## 1. Encryption Strategy

### Decision: Fernet Symmetric Encryption (cryptography library)

**Chosen Approach**:
```python
from cryptography.fernet import Fernet

# Key generation (one-time setup)
key = Fernet.generate_key()  # Returns base64-encoded 32-byte key

# Encryption
cipher = Fernet(key)
encrypted = cipher.encrypt(plaintext.encode())

# Decryption
decrypted = cipher.decrypt(encrypted).decode()
```

**Rationale**:
1. **Industry Standard**: Fernet is a symmetric encryption specification designed by cryptography experts
2. **Built-in Key Derivation**: Automatically handles HMAC authentication and timestamp verification
3. **Simple API**: Single key for encrypt/decrypt, no IV management needed
4. **Python Native**: Part of `cryptography` library (widely used, well-maintained)
5. **Performance**: Fast symmetric encryption (<1ms overhead per operation)
6. **Security**: AES-128-CBC with HMAC-SHA256 authentication

**Alternatives Considered**:

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| **AES-256-GCM** | Stronger encryption, authenticated | Requires IV management, more complex | Fernet provides sufficient security for API keys |
| **RSA Asymmetric** | Public/private key separation | Slower, more complex key management | Unnecessary complexity for single-user app |
| **AWS KMS / Vault** | Enterprise-grade, key rotation | External dependency, cost, complexity | Over-engineered for single-user deployment |
| **Database-level encryption** | Transparent to application | All-or-nothing, no selective encryption | Requires PostgreSQL/MySQL enterprise features |

**Key Storage Decision**: Environment variable (`DB_ENCRYPTION_KEY`)
- Base64-encoded 32-byte Fernet key
- Set once during deployment
- **Never commit to version control**
- Rotation requires migration script (manual process)

**Key Generation Script**:
```python
# utils/encryption.py
import os
from cryptography.fernet import Fernet

def generate_encryption_key():
    """Generate a new Fernet key for DB_ENCRYPTION_KEY."""
    key = Fernet.generate_key()
    print(f"Add this to your .env file:")
    print(f"DB_ENCRYPTION_KEY={key.decode()}")
    return key
```

**References**:
- [Cryptography Fernet Documentation](https://cryptography.io/en/latest/fernet/)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)

---

## 2. API Key Validation Patterns

### Decision: Provider-Specific Regex with Dual Validation (Client + Server)

**Validation Patterns**:
```python
# utils/llm_providers.py
API_KEY_PATTERNS = {
    'openrouter': r'^sk-or-v1-[A-Za-z0-9]{64}$',
    'claude': r'^sk-ant-api03-[A-Za-z0-9_-]{95}$',
    'openai': r'^sk-[A-Za-z0-9]{48}$',
    'gemini': r'^[A-Za-z0-9_-]{39}$',
    'nanogpt': r'^[A-Za-z0-9]{32,64}$',
    'chutes': r'^chutes_[A-Za-z0-9]{32}$',
    'zai': r'^[A-Za-z0-9]{32,}$',
}

def validate_api_key_format(provider, key):
    """Validate API key format for provider."""
    if not key:
        return True  # Empty is valid (optional)
    pattern = API_KEY_PATTERNS.get(provider)
    if not pattern:
        return True  # No pattern defined
    return re.match(pattern, key) is not None
```

**Rationale**:
1. **Early Feedback**: Client-side validation prevents form submission with invalid keys
2. **Security**: Server-side validation prevents bypass of client-side checks
3. **Specificity**: Provider-specific patterns catch common mistakes (wrong provider key)
4. **Maintenance**: Centralized pattern dictionary easy to update

**Client-Side Implementation** (JavaScript):
```javascript
// static/js/config.js
const API_KEY_PATTERNS = {
    openrouter: /^sk-or-v1-[A-Za-z0-9]{64}$/,
    claude: /^sk-ant-api03-[A-Za-z0-9_-]{95}$/,
    // ... other providers
};

function validateKeyFormat(provider, key) {
    if (!key) return true;
    const pattern = API_KEY_PATTERNS[provider];
    return pattern ? pattern.test(key) : true;
}
```

**Actual API Testing Decision**: Add `test_connection()` to LLMProvider base class
```python
class LLMProvider(ABC):
    def test_connection(self):
        """Test API connectivity with minimal request."""
        start = time.time()
        try:
            result = self.grade_document(
                text="Test",
                prompt="Respond with 'OK'",
                model=self.get_default_model(),
                max_tokens=10,
                temperature=0.0
            )
            latency = int((time.time() - start) * 1000)
            return {
                "success": result["success"],
                "message": "Connection successful" if result["success"] else result.get("error"),
                "latency_ms": latency
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
```

**Alternatives Considered**:
- **No Validation**: Users discover errors during grading (poor UX)
- **Server-Only Validation**: No immediate feedback on typos
- **Key Prefix Validation Only**: Too permissive, doesn't catch malformed keys
- **API Metadata Endpoints**: Not all providers have validation-only endpoints

**References**:
- Provider API documentation for key formats
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)

---

## 3. Error Handling Standardization

### Decision: Custom Exception Class with Error Type Enum

**Implementation**:
```python
# utils/llm_providers.py

class LLMProviderError(Exception):
    """Standardized exception for all LLM provider errors."""

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
        return {
            "success": False,
            "error": self.message,
            "error_type": self.error_type,
            "provider": self.provider,
            "http_status": self.http_status,
            "remediation": self._get_remediation()
        }

    def _get_remediation(self):
        """Provide actionable remediation steps."""
        remediation_map = {
            'authentication': "Verify your API key is correct and not expired",
            'rate_limit': "Wait a few minutes or check your account limits",
            'timeout': "Check network connectivity or try again later",
            'not_found': "Verify the model name is correct",
            'server_error': "Provider may be experiencing issues, try again later",
            'unknown': "Contact support if the issue persists"
        }
        return remediation_map.get(self.error_type, "Try again or contact support")
```

**Usage in Providers**:
```python
class OpenRouterLLMProvider(LLMProvider):
    def grade_document(self, ...):
        try:
            response = requests.post(...)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise LLMProviderError(
                'TIMEOUT',
                "OpenRouter request timed out after 60 seconds",
                "OpenRouter"
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise LLMProviderError(
                    'AUTH',
                    "OpenRouter authentication failed",
                    "OpenRouter",
                    http_status=401
                )
            elif e.response.status_code == 429:
                raise LLMProviderError(
                    'RATE_LIMIT',
                    "OpenRouter rate limit exceeded",
                    "OpenRouter",
                    http_status=429
                )
            # ... other error types
```

**Rationale**:
1. **Consistency**: All providers return identical error structure
2. **Actionability**: Users get specific remediation steps
3. **Debuggability**: Error type categorization aids troubleshooting
4. **User Experience**: Clear, non-technical error messages

**Alternatives Considered**:
- **Generic Exceptions**: No structure, inconsistent messages
- **HTTP Status Codes Only**: Not all errors have HTTP context
- **Provider-Specific Errors**: Inconsistent handling across providers
- **Logging Only**: Users get no feedback on failures

---

## 4. Database Migration Strategy

### Decision: Flask-Migrate (Alembic) + One-Time Migration Script

**Why Flask-Migrate**:
1. **Reversibility**: Alembic provides up/down migrations (constitution requirement)
2. **Version Control**: Migration history tracked in git
3. **Safety**: Dry-run capability before production execution
4. **Industry Standard**: Used by most Flask applications
5. **Future-Proof**: Handles future schema changes beyond encryption

**Installation**:
```bash
pip install Flask-Migrate>=4.0.0
```

**Initialization** (one-time setup):
```python
# app.py
from flask_migrate import Migrate

migrate = Migrate(app, db)
```

**Migration Script for Encryption**:
```python
# migrations/encrypt_api_keys.py
"""
One-time migration to encrypt existing plaintext API keys.
Run with: python migrations/encrypt_api_keys.py
"""
import os
import sys
from cryptography.fernet import Fernet
from app import app, db
from models import Config

def encrypt_existing_keys():
    """Encrypt all plaintext API keys in the database."""
    encryption_key = os.getenv('DB_ENCRYPTION_KEY')
    if not encryption_key:
        print("ERROR: DB_ENCRYPTION_KEY not set in environment")
        sys.exit(1)

    cipher = Fernet(encryption_key.encode())

    with app.app_context():
        config = Config.query.first()
        if not config:
            print("No configuration found in database")
            return

        # Migrate each key field
        fields = [
            'openrouter_api_key', 'claude_api_key', 'gemini_api_key',
            'openai_api_key', 'nanogpt_api_key', 'chutes_api_key', 'zai_api_key'
        ]

        for field in fields:
            value = getattr(config, field)
            if value and not value.startswith('gAAAAA'):  # Not already encrypted
                encrypted = cipher.encrypt(value.encode()).decode()
                setattr(config, field, encrypted)
                print(f"Encrypted {field}")

        db.session.commit()
        print("Migration complete!")

if __name__ == '__main__':
    encrypt_existing_keys()
```

**Alternatives Considered**:
- **Manual SQL**: Error-prone, no rollback capability
- **In-App Migration**: Risky to run on app startup
- **Database-Level Triggers**: PostgreSQL-specific, not portable

---

## 5. Frontend Import/Export Strategy

### Decision: Client-Side JSON Generation with Security Warnings

**Export Implementation**:
```javascript
function exportConfig() {
    const config = {
        // Gather all form values
        openrouter_api_key: $('#openrouter_api_key').val(),
        claude_api_key: $('#claude_api_key').val(),
        // ... all other fields

        // Metadata
        exported_at: new Date().toISOString(),
        version: '1.0',
        warning: 'This file contains sensitive API keys. Protect it accordingly.'
    };

    const blob = new Blob(
        [JSON.stringify(config, null, 2)],
        {type: 'application/json'}
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `grading-config-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);

    // Show warning
    alert('⚠️ Configuration exported! This file contains sensitive API keys. Store it securely.');
}
```

**Import Implementation**:
```javascript
function importConfig(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const config = JSON.parse(e.target.result);

            // Validate version
            if (config.version !== '1.0') {
                showError('Incompatible configuration version');
                return;
            }

            // Populate form fields
            Object.keys(config).forEach(key => {
                if (key !== 'exported_at' && key !== 'version' && key !== 'warning') {
                    $(`#${key}`).val(config[key] || '');
                }
            });

            showSuccess('Configuration imported successfully!');
        } catch (error) {
            showError(`Import failed: ${error.message}`);
        }
    };
    reader.readAsText(file);
}
```

**Rationale**:
- **Client-Side**: No sensitive data transmitted to server during export
- **JSON Format**: Human-readable, version-controllable (with care)
- **Metadata**: Timestamp and version for tracking
- **Warning**: Explicit reminder about sensitive content

---

## 6. Accessibility Implementation

### Decision: WCAG 2.1 Level AA Compliance with Manual + Automated Testing

**Key Accessibility Features**:

1. **ARIA Labels** for all interactive elements:
```html
<button
    type="button"
    class="btn btn-outline-primary"
    onclick="togglePassword('openrouter_api_key')"
    aria-label="Toggle OpenRouter API key visibility"
    aria-pressed="false">
    <i class="fas fa-eye" aria-hidden="true"></i>
</button>
```

2. **Screen Reader Text** for status indicators:
```html
<div class="d-flex align-items-center">
    <div id="openrouter-status" class="status-indicator"
         role="status" aria-label="OpenRouter API status"></div>
    <span>OpenRouter</span>
    <span id="openrouter-status-text" class="visually-hidden">
        Status unknown
    </span>
</div>
```

3. **Keyboard Navigation**:
- All interactive elements reachable via Tab
- Logical tab order (top to bottom, left to right)
- Focus indicators visible
- Enter/Space activate buttons

4. **Form Validation** announced to screen readers:
```javascript
function showValidationError(fieldId, message) {
    const field = $(`#${fieldId}`);
    field.attr('aria-invalid', 'true');
    field.attr('aria-describedby', `${fieldId}-error`);

    $(`#${fieldId}-error`).text(message).attr('role', 'alert');
}
```

**Testing Strategy**:
- **Automated**: axe-core accessibility testing in pytest
- **Manual**: Screen reader testing (NVDA on Windows, VoiceOver on Mac)
- **Keyboard-Only**: Navigate entire config page without mouse

**Tools**:
```bash
pip install pytest-axe  # Automated WCAG testing
```

```python
# tests/test_accessibility.py
def test_config_page_accessibility(client):
    """Test config page meets WCAG 2.1 Level AA."""
    response = client.get('/config')
    assert response.status_code == 200

    # Run axe-core accessibility checks
    violations = axe.run(response.data)
    assert len(violations) == 0, f"Accessibility violations: {violations}"
```

---

## 7. Best Practices Summary

### Security
- ✅ Encryption at rest (Fernet)
- ✅ Separation of encryption key from database
- ✅ No API keys in logs or error messages
- ✅ Client + server validation
- ✅ Export warning about sensitive data

### Performance
- ✅ <1ms encryption overhead
- ✅ Client-side export (no server round-trip)
- ✅ Minimal API test requests (single prompt)

### Maintainability
- ✅ Centralized validation patterns
- ✅ Standardized error handling
- ✅ Migration scripts for schema changes
- ✅ Version-controlled configuration exports

### User Experience
- ✅ Immediate validation feedback
- ✅ Clear error messages with remediation
- ✅ Visual provider type distinction
- ✅ Bulk import/export for efficiency
- ✅ WCAG 2.1 Level AA accessibility

### Testing
- ✅ Unit tests for encryption
- ✅ Integration tests for endpoints
- ✅ Accessibility automated + manual testing
- ✅ Migration script dry-run capability

---

## References

### Official Documentation
- [Cryptography Library Fernet](https://cryptography.io/en/latest/fernet/)
- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)

### Security Standards
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [NIST Cryptographic Standards](https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines)

### Provider API Documentation
- [OpenRouter API Documentation](https://openrouter.ai/docs)
- [Anthropic Claude API Reference](https://docs.anthropic.com/claude/reference)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Google Gemini API Docs](https://ai.google.dev/docs)

---

**Document Status**: ✅ **Complete** - All technical decisions documented with rationale
**Next Phase**: data-model.md (database schema design)
