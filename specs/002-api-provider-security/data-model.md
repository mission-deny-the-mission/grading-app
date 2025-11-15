# Data Model: API Provider Security & UX Improvements

**Feature**: 002-api-provider-security
**Date**: 2025-01-15
**Phase**: Phase 1 - Data Model Design

## Overview

This document defines the database schema changes, entity relationships, and data structures for implementing secure API key storage, validation, error handling, and configuration management features.

---

## 1. Modified Entities

### 1.1 Config Model (models.py)

**Current Implementation** (Plaintext Storage):
```python
class Config(db.Model):
    """Application configuration stored in database."""
    __tablename__ = 'config'

    id = db.Column(db.Integer, primary_key=True)
    openrouter_api_key = db.Column(db.String(200))  # PLAINTEXT
    claude_api_key = db.Column(db.String(200))      # PLAINTEXT
    gemini_api_key = db.Column(db.String(200))      # PLAINTEXT
    # ... other keys (all plaintext)
```

**New Implementation** (Encrypted Storage):
```python
class Config(db.Model):
    """Application configuration with encrypted API keys."""
    __tablename__ = 'config'

    id = db.Column(db.Integer, primary_key=True)

    # Private encrypted fields (prefixed with _)
    _openrouter_api_key = db.Column('openrouter_api_key', db.String(500))
    _claude_api_key = db.Column('claude_api_key', db.String(500))
    _gemini_api_key = db.Column('gemini_api_key', db.String(500))
    _openai_api_key = db.Column('openai_api_key', db.String(500))
    _nanogpt_api_key = db.Column('nanogpt_api_key', db.String(500))
    _chutes_api_key = db.Column('chutes_api_key', db.String(500))
    _zai_api_key = db.Column('zai_api_key', db.String(500))

    # Public properties with encryption/decryption
    @property
    def openrouter_api_key(self):
        """Get decrypted OpenRouter API key."""
        return self._decrypt(self._openrouter_api_key)

    @openrouter_api_key.setter
    def openrouter_api_key(self, value):
        """Set encrypted OpenRouter API key."""
        self._openrouter_api_key = self._encrypt(value)

    # ... repeat for all other API key properties

    # Encryption utilities
    def _get_cipher(self):
        """Get Fernet cipher with encryption key."""
        from utils.encryption import get_encryption_key
        return get_encryption_key()

    def _encrypt(self, value):
        """Encrypt a string value."""
        if not value:
            return None
        from cryptography.fernet import Fernet
        cipher = Fernet(self._get_cipher())
        return cipher.encrypt(value.encode()).decode()

    def _decrypt(self, value):
        """Decrypt a string value."""
        if not value:
            return None
        from cryptography.fernet import Fernet
        cipher = Fernet(self._get_cipher())
        try:
            return cipher.decrypt(value.encode()).decode()
        except Exception as e:
            # Log error but don't expose key
            print(f"Decryption failed: {type(e).__name__}")
            raise ValueError("Failed to decrypt API key - check DB_ENCRYPTION_KEY")
```

**Schema Changes**:
| Field | Old Type | New Type | Reason |
|-------|----------|----------|--------|
| `*_api_key` | VARCHAR(200) | VARCHAR(500) | Fernet ciphertext is longer than plaintext |

**Migration Required**: YES
- Existing plaintext keys must be encrypted
- Column length must be increased to 500 characters
- Migration script: `migrations/encrypt_api_keys.py`

**Validation Rules**:
- API keys validated before encryption (see ValidationPattern below)
- Empty/null values allowed (optional configuration)
- Decryption failures raise ValueError (fail-safe)

**State Transitions**:
```
[Plaintext Key] ──(save)──> [Encrypted Key in DB]
                              ↓
                          (load/decrypt)
                              ↓
                     [Plaintext Key in Memory]
                              ↓
                        (display masked)
                              ↓
                       [****key (UI)]
```

---

## 2. New Entities

### 2.1 ValidationPattern (Constants)

**Purpose**: Centralized API key format validation patterns

**Implementation** (utils/llm_providers.py):
```python
# Constants - not stored in database
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
    """Validate API key format for a provider."""
    if not key:
        return True, None  # Empty is valid
    pattern = API_KEY_PATTERNS.get(provider)
    if not pattern:
        return True, None  # No pattern defined
    if not re.match(pattern, key):
        return False, f"Invalid {provider} API key format"
    return True, None
```

**Attributes**:
- `provider` (string): Provider identifier (lowercase)
- `pattern` (regex string): Validation regex pattern
- `version` (implicit): Pattern version for tracking changes

**Relationships**: None (constants)

**Validation**: N/A (these are the validators)

---

### 2.2 LLMProviderError (Exception Class)

**Purpose**: Standardized error handling across all LLM providers

**Implementation** (utils/llm_providers.py):
```python
class LLMProviderError(Exception):
    """Standardized exception for LLM provider errors."""

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
        """Get user-friendly remediation suggestion."""
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

**Attributes**:
- `error_type` (string): Error category from ERROR_TYPES enum
- `message` (string): Human-readable error description
- `provider` (string): Provider name (e.g., "OpenRouter")
- `http_status` (int, optional): HTTP status code if applicable

**Relationships**: None (exception class)

**Usage**:
```python
# In provider implementation
try:
    response = requests.post(url, headers=headers, timeout=60)
    response.raise_for_status()
except requests.exceptions.Timeout:
    raise LLMProviderError('TIMEOUT', "Request timed out", "OpenRouter")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        raise LLMProviderError('AUTH', "Authentication failed", "OpenRouter", 401)
```

---

### 2.3 ConfigurationExport (Data Transfer Object)

**Purpose**: Structure for configuration import/export operations

**Implementation** (routes/main.py):
```python
class ConfigurationExport:
    """DTO for configuration import/export."""

    def __init__(self, config):
        """Initialize from Config model."""
        self.version = "1.0"
        self.exported_at = datetime.utcnow().isoformat()
        self.openrouter_api_key = config.openrouter_api_key or ""
        self.claude_api_key = config.claude_api_key or ""
        # ... all other configuration fields

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return {
            "version": self.version,
            "exported_at": self.exported_at,
            "warning": "This file contains sensitive API keys. Protect accordingly.",
            # All configuration fields
            "openrouter_api_key": self.openrouter_api_key,
            "claude_api_key": self.claude_api_key,
            # ...
        }

    @classmethod
    def from_dict(cls, data):
        """Create from imported JSON dict."""
        if data.get("version") != "1.0":
            raise ValueError(f"Unsupported version: {data.get('version')}")
        # Validation and mapping logic
        return data  # Returns dict for Config model update
```

**Attributes**:
- `version` (string): Export format version ("1.0")
- `exported_at` (ISO timestamp): Export creation time
- `warning` (string): Security warning message
- All Config model fields (API keys, URLs, default models, etc.)

**Relationships**:
- Maps to/from `Config` model
- Used by export/import endpoints

**Validation**:
- Version must be "1.0"
- Required fields: version, exported_at
- API keys validated before import (via ValidationPattern)

---

## 3. Data Flow Diagrams

### 3.1 API Key Save Flow
```
User Input (form)
    ↓
Client-side Validation (JavaScript)
    ↓ (if valid)
POST /save_config
    ↓
Server-side Validation (Python)
    ↓ (if valid)
Encryption (Fernet)
    ↓
Database Write (SQLAlchemy)
    ↓
Success Response
```

### 3.2 API Key Load Flow
```
GET /load_config OR Page Load
    ↓
Database Read (SQLAlchemy)
    ↓
Decryption (Fernet)
    ↓ (if DB_ENCRYPTION_KEY valid)
Environment Variable Fallback (if DB empty)
    ↓
Masking for UI Display
    ↓
JSON Response OR Template Render
```

### 3.3 API Key Test Flow
```
User Clicks "Test Key"
    ↓
POST /test_api_key {type, key}
    ↓
Format Validation (regex)
    ↓ (if valid)
Get LLMProvider instance
    ↓
test_connection() → Actual API Call
    ↓
Success: {success: true, latency_ms}
Failure: {success: false, error, error_type, remediation}
```

### 3.4 Configuration Export/Import Flow
```
EXPORT:
User clicks "Export"
    ↓
JavaScript: Gather form values
    ↓
Create JSON with metadata
    ↓
Download as file
    ↓
Show security warning

IMPORT:
User uploads JSON file
    ↓
JavaScript: Read file
    ↓
Validate JSON structure & version
    ↓
Populate form fields
    ↓
Success message
```

---

## 4. Database Schema

### 4.1 Config Table (Modified)

**Table**: `config`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Singleton record ID (always 1) |
| `openrouter_api_key` | VARCHAR(500) | NULL | Encrypted OpenRouter API key |
| `claude_api_key` | VARCHAR(500) | NULL | Encrypted Claude API key |
| `gemini_api_key` | VARCHAR(500) | NULL | Encrypted Gemini API key |
| `openai_api_key` | VARCHAR(500) | NULL | Encrypted OpenAI API key |
| `nanogpt_api_key` | VARCHAR(500) | NULL | Encrypted NanoGPT API key |
| `chutes_api_key` | VARCHAR(500) | NULL | Encrypted Chutes API key |
| `zai_api_key` | VARCHAR(500) | NULL | Encrypted Z.AI API key |
| `lm_studio_url` | VARCHAR(200) | DEFAULT 'http://localhost:1234/v1' | LM Studio endpoint URL |
| `ollama_url` | VARCHAR(200) | DEFAULT 'http://localhost:11434' | Ollama endpoint URL |
| `default_prompt` | TEXT | NULL | Default grading prompt |
| `zai_pricing_plan` | VARCHAR(20) | DEFAULT 'normal' | Z.AI plan ('normal' or 'coding') |
| `openrouter_default_model` | VARCHAR(100) | NULL | Default model for OpenRouter |
| `claude_default_model` | VARCHAR(100) | NULL | Default model for Claude |
| `gemini_default_model` | VARCHAR(100) | NULL | Default model for Gemini |
| `openai_default_model` | VARCHAR(100) | NULL | Default model for OpenAI |
| `nanogpt_default_model` | VARCHAR(100) | NULL | Default model for NanoGPT |
| `chutes_default_model` | VARCHAR(100) | NULL | Default model for Chutes |
| `zai_default_model` | VARCHAR(100) | NULL | Default model for Z.AI |
| `lm_studio_default_model` | VARCHAR(100) | NULL | Default model for LM Studio |
| `ollama_default_model` | VARCHAR(100) | NULL | Default model for Ollama |

**Indexes**: None (singleton table)

**Constraints**:
- Exactly one row (enforced by application logic)
- API key fields can be NULL (optional configuration)

**Migration SQL** (generated by Flask-Migrate):
```sql
-- Increase column length for encrypted keys
ALTER TABLE config ALTER COLUMN openrouter_api_key TYPE VARCHAR(500);
ALTER TABLE config ALTER COLUMN claude_api_key TYPE VARCHAR(500);
ALTER TABLE config ALTER COLUMN gemini_api_key TYPE VARCHAR(500);
ALTER TABLE config ALTER COLUMN openai_api_key TYPE VARCHAR(500);
ALTER TABLE config ALTER COLUMN nanogpt_api_key TYPE VARCHAR(500);
ALTER TABLE config ALTER COLUMN chutes_api_key TYPE VARCHAR(500);
ALTER TABLE config ALTER COLUMN zai_api_key TYPE VARCHAR(500);

-- Data migration handled by Python script (encrypt_api_keys.py)
```

---

## 5. Validation Rules

### 5.1 Config Model Validation

**On Save** (routes/main.py):
```python
def validate_config_before_save(form_data):
    """Validate configuration before saving."""
    errors = []

    # Validate API key formats
    for provider in ['openrouter', 'claude', 'gemini', 'openai', 'nanogpt', 'chutes', 'zai']:
        key = form_data.get(f'{provider}_api_key')
        if key:
            valid, error = validate_api_key_format(provider, key)
            if not valid:
                errors.append(error)

    # Validate URLs
    for url_field in ['lm_studio_url', 'ollama_url']:
        url = form_data.get(url_field)
        if url and not url.startswith(('http://', 'https://')):
            errors.append(f"{url_field} must start with http:// or https://")

    # Validate Z.AI pricing plan
    zai_plan = form_data.get('zai_pricing_plan')
    if zai_plan and zai_plan not in ['normal', 'coding']:
        errors.append("zai_pricing_plan must be 'normal' or 'coding'")

    return errors
```

### 5.2 Import Validation

**On Import** (JavaScript + Python):
```javascript
function validateImportedConfig(config) {
    const errors = [];

    // Version check
    if (config.version !== '1.0') {
        errors.push(`Unsupported version: ${config.version}`);
    }

    // Required metadata
    if (!config.exported_at) {
        errors.push('Missing export timestamp');
    }

    // API key format validation
    Object.keys(API_KEY_PATTERNS).forEach(provider => {
        const key = config[`${provider}_api_key`];
        if (key && !validateKeyFormat(provider, key)) {
            errors.push(`Invalid ${provider} API key format`);
        }
    });

    return errors;
}
```

---

## 6. Error Handling

### 6.1 Encryption Errors

| Error Condition | Exception | User Message | Remediation |
|-----------------|-----------|--------------|-------------|
| Missing DB_ENCRYPTION_KEY | ValueError | "Encryption key not configured" | Set DB_ENCRYPTION_KEY environment variable |
| Invalid encryption key | ValueError | "Invalid encryption key format" | Generate new key with utils/encryption.py |
| Decryption failure | ValueError | "Failed to decrypt configuration" | Check DB_ENCRYPTION_KEY matches encrypted data |

### 6.2 Validation Errors

| Error Condition | HTTP Status | Response | Remediation |
|-----------------|-------------|----------|-------------|
| Invalid key format | 400 | `{success: false, error: "Invalid [provider] API key format"}` | Check provider documentation for key format |
| Invalid URL format | 400 | `{success: false, error: "URL must start with http:// or https://"}` | Correct URL format |
| Import version mismatch | 400 | `{success: false, error: "Unsupported version: [X]"}` | Use compatible export file |

---

## 7. Performance Considerations

### 7.1 Encryption Overhead

**Measurement**:
- Fernet encryption: ~0.1-0.5ms per key
- Total for 7 keys: <3.5ms
- Database write: ~10-50ms (SQLite local)
- **Total overhead**: <5% of request time

**Optimization**: None needed (overhead negligible)

### 7.2 Decryption Caching

**Not implemented** (security over performance):
- Decrypted keys kept in memory only during request
- No caching to prevent memory exposure
- Config loaded infrequently (admin operations only)

---

## 8. Security Considerations

### 8.1 Encryption Key Management

**Storage**: Environment variable only
**Access**: Read-only, never logged
**Rotation**: Manual process (requires migration)
**Backup**: Store in secure password manager

### 8.2 API Key Exposure Prevention

**Log Sanitization**:
```python
def sanitize_for_logging(data):
    """Remove API keys from logged data."""
    sensitive_fields = [f'{p}_api_key' for p in PROVIDERS]
    return {k: '***' if k in sensitive_fields else v for k, v in data.items()}
```

**Error Messages**: Never include key fragments
**Export Files**: Explicit warning about sensitivity

---

## Summary

**Schema Changes**: 1 table modified (config)
**New Entities**: 3 (LLMProviderError, ValidationPattern constants, ConfigurationExport DTO)
**Migration Required**: Yes (one-time encryption + column length increase)
**Breaking Changes**: None (backward compatible with environment variables)

**Next Phase**: contracts/ (API contract specifications)
