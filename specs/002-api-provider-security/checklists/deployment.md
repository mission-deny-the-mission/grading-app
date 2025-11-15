# Production Deployment Checklist: API Provider Configuration Security

**Feature**: API Provider Configuration Security & UX Improvements (US1-6)
**Date**: 2025-11-15
**Target**: Production deployment of encrypted API key storage

---

## Pre-Deployment Preparation

### Security Verification
- [ ] DB_ENCRYPTION_KEY generated and stored securely (NOT in git)
- [ ] Encryption key stored in production secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] .env file is in .gitignore (verify with `git check-ignore .env`)
- [ ] All API keys encrypted locally before deployment
- [ ] Migration script tested on copy of production database
- [ ] Rollback plan documented and verified

### Testing Verification
- [ ] All unit tests passing (pytest tests/ -v)
- [ ] All integration tests passing (pytest tests/test_config_routes.py -v)
- [ ] Test coverage ≥80% (pytest --cov)
- [ ] Code quality checks passing (flake8, black)
- [ ] No API keys logged in logs/errors (security review complete)
- [ ] Accessibility tests passing (pytest tests/test_accessibility.py -v)
- [ ] Performance tests passing (encryption overhead <5%)

### Code Quality Verification
- [ ] No type errors (mypy if applicable)
- [ ] No import errors (python -m py_compile on all files)
- [ ] All dependencies listed in requirements.txt
- [ ] No hardcoded API keys in source code (grep -r "sk-" src/)
- [ ] No debug print statements left (grep -r "print(" src/)
- [ ] Docstrings updated for modified functions

### Documentation Verification
- [ ] README.md updated with encryption setup instructions
- [ ] README.md updated with migration instructions
- [ ] .env.example created with all required variables
- [ ] Migration script documented in quickstart.md
- [ ] Rollback procedure documented
- [ ] Deployment checklist completed (this file)

---

## Database Backup & Dry Run

### Step 1: Backup Production Database
```bash
# PostgreSQL
pg_dump grading_app_production > grading_app_production_backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite
cp grading_app.db grading_app.db.backup_$(date +%Y%m%d_%H%M%S)

# MySQL
mysqldump -u user -p grading_app_production > grading_app_production_backup_$(date +%Y%m%d_%H%M%S).sql
```
- [ ] Backup location verified: __________
- [ ] Backup size reasonable: __________
- [ ] Backup tested to restore (dry run): Yes / No

### Step 2: Test Migration on Database Copy
```bash
# Create copy of production database for dry run
# Example with SQLite:
cp grading_app.db.backup grading_app_test.db

# Set test environment
export DB_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Test migration script
python migrations/encrypt_api_keys.py --database grading_app_test.db

# Verify migration succeeded
python -c "
from app import app, db
from models import Config
with app.app_context():
    config = Config.query.first()
    if config and config._openrouter_api_key and config._openrouter_api_key.startswith('gAAAAA'):
        print('✅ Migration successful - keys encrypted')
    else:
        print('❌ Migration failed - keys not encrypted')
"
```
- [ ] Dry run started at: __________
- [ ] Migration completed successfully
- [ ] All API keys encrypted (checked in database)
- [ ] Test database can still load configuration
- [ ] API key decryption works correctly

---

## Production Deployment

### Step 1: Pre-Deployment Notification
- [ ] Notify stakeholders of scheduled maintenance
- [ ] Schedule deployment window (low-traffic time)
- [ ] Ensure support team is available during deployment

### Step 2: Prepare Production Environment
```bash
# 1. Generate unique encryption key for production
export DB_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 2. Store in production secrets manager (do NOT use .env in production)
# Example (adjust for your secrets manager):
# AWS: aws secretsmanager create-secret --name grading-app-db-encryption-key --secret-string $DB_ENCRYPTION_KEY
# Vault: vault kv put secret/grading-app DB_ENCRYPTION_KEY=$DB_ENCRYPTION_KEY

# 3. Verify environment variable is accessible
python -c "import os; print('✅ Key set' if os.getenv('DB_ENCRYPTION_KEY') else '❌ Key missing')"
```
- [ ] DB_ENCRYPTION_KEY generated
- [ ] Key stored in secrets manager
- [ ] Key verified accessible to application

### Step 3: Stop Application Services
```bash
# Stop web application
systemctl stop grading-app

# Verify stopped
ps aux | grep python | grep -v grep
```
- [ ] Application stopped successfully
- [ ] Verify no connections to database

### Step 4: Deploy Code Changes
```bash
# Deploy new version with encryption support
git pull origin main  # or your deployment method
pip install -r requirements.txt  # Install new dependencies

# Verify migration script exists
test -f migrations/encrypt_api_keys.py && echo "✅ Migration script present"
```
- [ ] Code deployed successfully
- [ ] New dependencies installed (cryptography, Flask-Migrate)
- [ ] Migration script verified

### Step 5: Run Migration on Production Database
```bash
# Run migration script
python migrations/encrypt_api_keys.py

# Verify migration output shows completion
# Expected: "✅ Migration complete!"
```
- [ ] Migration started at: __________
- [ ] Migration completed successfully (check logs)
- [ ] No errors reported during migration
- [ ] Check database size unchanged (no data loss)

### Step 6: Verify Database State
```bash
# Verify all keys are encrypted
python -c "
from app import app, db
from models import Config
with app.app_context():
    config = Config.query.first()
    # Check sample encrypted keys
    fields = ['_openrouter_api_key', '_claude_api_key']
    for field in fields:
        value = getattr(config, field, None)
        if value:
            is_encrypted = value.startswith('gAAAAA')
            status = '✅ Encrypted' if is_encrypted else '❌ Not Encrypted'
            print(f'{field}: {status}')
"
```
- [ ] API keys are encrypted in database
- [ ] Empty keys handled correctly
- [ ] No decryption errors

### Step 7: Start Application Services
```bash
# Start web application
systemctl start grading-app

# Verify running
ps aux | grep python | grep -v grep
ps aux | grep gunicorn | grep -v grep  # if using Gunicorn
```
- [ ] Application started successfully
- [ ] Application logs show no errors
- [ ] Health check passes (curl http://localhost:5000/health)

### Step 8: Smoke Tests
```bash
# Test configuration load
curl -X GET http://localhost:5000/load_config
# Expected: 200 response with decrypted (masked) keys

# Test API key validation
curl -X POST http://localhost:5000/save_config \
  -d "openrouter_api_key=sk-or-v1-test123"
# Expected: validation response

# Test application basic functionality
python validate_bulk_upload_fix.py
```
- [ ] Configuration page loads
- [ ] API keys are properly masked (not visible in plaintext)
- [ ] API key validation works
- [ ] Bulk upload functionality works
- [ ] No decryption errors in logs

---

## Post-Deployment Verification

### Performance Monitoring
- [ ] Application response time normal (<500ms for config page)
- [ ] Database query performance acceptable
- [ ] No increased CPU usage from encryption operations
- [ ] No increased memory usage

### Security Monitoring
```bash
# Verify no API keys in logs
grep -r "sk-" /var/log/grading-app/ || echo "✅ No API keys in logs"

# Verify no API keys in error messages
grep -r "API key" /var/log/grading-app/ | grep -v "Invalid API key format" || echo "✅ Error messages safe"

# Check database access logs
# Ensure only application user can read database
ls -l grading_app.db  # Check file permissions
```
- [ ] No API keys found in logs
- [ ] Error messages don't expose sensitive data
- [ ] Database file permissions correct (600 or restricted)

### Functional Testing
- [ ] Load configuration → displays masked API keys ✅
- [ ] Save configuration → validates and encrypts keys ✅
- [ ] Edit configuration → keys remain encrypted ✅
- [ ] Export configuration → doesn't export keys in plaintext ✅
- [ ] Import configuration → properly encrypts imported keys ✅
- [ ] Test API Key button → works with encrypted keys ✅
- [ ] All provider sections visible with correct badges ✅
- [ ] Keyboard navigation works (Tab, Shift+Tab) ✅
- [ ] Screen reader announces ARIA labels ✅
- [ ] Focus indicators visible ✅

### Accessibility Verification
- [ ] Configuration page WCAG 2.1 Level AA compliant ✅
- [ ] Keyboard-only navigation works ✅
- [ ] Screen reader announces all content ✅
- [ ] Focus indicators visible and clear ✅
- [ ] Form validation errors announced ✅

---

## Rollback Plan (If Needed)

### Automatic Rollback Triggers
- [ ] Migration incomplete or errors
- [ ] Application fails to start
- [ ] Critical decryption failures in logs
- [ ] Response time degradation >50%
- [ ] Database corruption detected

### Manual Rollback Procedure
```bash
# 1. Stop application
systemctl stop grading-app

# 2. Restore from backup
# PostgreSQL:
psql grading_app < grading_app_production_backup_*.sql

# SQLite:
cp grading_app.db.backup_* grading_app.db

# MySQL:
mysql grading_app < grading_app_production_backup_*.sql

# 3. Revert code changes
git revert [commit-hash-of-encryption-feature]

# 4. Restart application
systemctl start grading-app

# 5. Verify rollback
curl http://localhost:5000/load_config
```
- [ ] Rollback initiated at: __________
- [ ] Database restored from backup
- [ ] Code reverted
- [ ] Application restarted successfully
- [ ] Verified working on old version

---

## Post-Deployment Documentation

### Update Production Runbooks
- [ ] Add encryption key rotation procedure
- [ ] Add backup/restore procedures for encrypted database
- [ ] Add troubleshooting guide for decryption errors
- [ ] Add disaster recovery procedures

### Monitor for Issues
```bash
# Tail application logs for first 24 hours
tail -f /var/log/grading-app/app.log | grep -i "error\|decryption\|migration"

# Check for decryption failures
grep "Decryption failed" /var/log/grading-app/app.log || echo "✅ No decryption failures"

# Monitor performance metrics
# - Response time for /load_config endpoint
# - Database query performance
# - System CPU/memory usage
```
- [ ] Logs monitored for 24 hours post-deployment
- [ ] No critical errors detected
- [ ] Performance metrics within acceptable range

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | ________ | ________ | ________ |
| QA/Tester | ________ | ________ | ________ |
| DevOps | ________ | ________ | ________ |
| Product Owner | ________ | ________ | ________ |

---

## Deployment Summary

**Deployment Date**: __________
**Deployment Time**: __________ - __________
**Total Duration**: __________
**Issues Encountered**: None / [describe]
**Rollback Required**: Yes / No
**Current Status**: ✅ Success / ❌ Failure

**Notes**:
```


```

---

## Future Maintenance

### Regular Tasks
- [ ] **Monthly**: Verify encryption key is securely backed up
- [ ] **Quarterly**: Rotate encryption key (requires data re-encryption)
- [ ] **As needed**: Monitor logs for decryption errors
- [ ] **On upgrades**: Re-run migration if database schema changes

### Key Rotation Procedure (Future)
```bash
# Generate new encryption key
NEW_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Re-encrypt all keys with new key (requires implementation)
python migrations/rotate_encryption_key.py --old-key $OLD_KEY --new-key $NEW_KEY

# Update DB_ENCRYPTION_KEY in secrets manager
# Update all application instances with new key
```

### Disaster Recovery
- [ ] Encryption key backed up in secure location (not with database)
- [ ] Database backups tested regularly for recovery
- [ ] Encryption key recovery procedure documented
- [ ] Consider encryption key escrow for critical systems

---

**Document Status**: ✅ **Complete** - Ready for production deployment
**Last Updated**: 2025-11-15
