# Document Grading Web App

[![CI](https://gitea.harryslab.xyz/mission-deny-the-mission/grading-app/actions/workflows/ci.yml/badge.svg?branch=main)](https://gitea.harryslab.xyz/mission-deny-the-mission/grading-app/actions)

AI-powered document grading with support for OpenRouter, Claude API, and LM Studio.

**Security Update**: API keys are now encrypted at rest in the database using Fernet encryption.

## 🔧 Setup & Configuration

### Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate encryption key (REQUIRED for security)
python -c "from cryptography.fernet import Fernet; print(f'DB_ENCRYPTION_KEY={Fernet.generate_key().decode()}')"

# 3. Add key to .env file
# Copy the generated key above and add to .env:
# DB_ENCRYPTION_KEY=your_generated_key_here
# ⚠️ NEVER commit .env to version control

# 4. Start the application
python app.py
```

### Encryption Key Setup (Critical for Production)

The application uses Fernet encryption for all stored API keys. A unique encryption key **MUST** be generated for each deployment:

```bash
# Generate a new encryption key
python -c "from cryptography.fernet import Fernet; key = Fernet.generate_key().decode(); print(f'DB_ENCRYPTION_KEY={key}')"

# Add to your .env file (do NOT commit to git):
echo "DB_ENCRYPTION_KEY=your_generated_key_here" >> .env

# Verify the key is loaded:
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ Key loaded' if os.getenv('DB_ENCRYPTION_KEY') else '❌ Key missing')"
```

**⚠️ Important Security Notes**:
- Store the `DB_ENCRYPTION_KEY` securely (environment variables, secrets manager, etc.)
- **Never commit** the key or `.env` file to version control
- Use the same key across application restarts to decrypt stored keys
- Losing the key makes encrypted keys unrecoverable

### Production Migration (Existing Installations)

If upgrading an existing installation with plaintext API keys:

```bash
# 1. Backup your database before proceeding
# Example with SQLite:
cp grading_app.db grading_app.db.backup

# 2. Set DB_ENCRYPTION_KEY environment variable
export DB_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 3. Run the migration script to encrypt existing keys
python migrations/encrypt_api_keys.py

# 4. Verify keys are encrypted
# Check logs for "✅ Migration complete!"

# 5. Start the application
python app.py

# 6. Test API key functionality on the configuration page
```

## Quick Links

- Getting started: `docs/Getting-Started.md`
- Features overview: `docs/Features.md`
- Testing: `docs/Testing.md`
- Docker: `docs/Docker.md`
- Bulk upload tests: `tests/README_bulk_upload_tests.md`
- Security implementation: `specs/002-api-provider-security/quickstart.md`

## File structure

```
grading-app/
├── app.py
├── routes/
├── utils/
├── models.py
├── tasks.py
├── templates/
├── docs/
├── tests/
├── validate_bulk_upload_fix.py  # Quick validation script
└── uploads/
```

## License

MIT
