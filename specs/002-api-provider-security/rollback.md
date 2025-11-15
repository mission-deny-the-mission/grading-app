# Rollback Procedure: API Provider Configuration Security

**Feature**: API Provider Configuration Security & UX Improvements (US1-6)
**Date**: 2025-11-15
**Purpose**: Steps to safely rollback the encryption feature if deployment fails

---

## Overview

If the production deployment of API key encryption encounters critical issues, follow this procedure to safely restore the previous version. This guide covers:
- **Automatic rollback triggers** (when to rollback immediately)
- **Manual rollback steps** (detailed restoration procedure)
- **Verification checks** (confirming rollback success)
- **Post-rollback monitoring** (ensuring stability)

---

## When to Rollback (Automatic Triggers)

Initiate rollback immediately if ANY of these conditions occur:

| Condition | Severity | Action |
|-----------|----------|--------|
| Application fails to start | 🔴 Critical | ROLLBACK IMMEDIATELY |
| DB_ENCRYPTION_KEY missing → application crash | 🔴 Critical | ROLLBACK IMMEDIATELY |
| Database connection failures after migration | 🔴 Critical | ROLLBACK IMMEDIATELY |
| Cannot decrypt API keys (many failures in logs) | 🔴 Critical | ROLLBACK IMMEDIATELY |
| Configuration page returns 500 errors | 🔴 Critical | ROLLBACK IMMEDIATELY |
| API key test/validation endpoints failing | 🟠 High | ROLLBACK IMMEDIATELY |
| Performance degradation >50% (encryption overhead) | 🟠 High | ROLLBACK IMMEDIATELY |
| Database integrity errors detected | 🔴 Critical | ROLLBACK IMMEDIATELY |
| Rollback test/dry-run failed | 🔴 Critical | DO NOT DEPLOY |

---

## Pre-Deployment Setup for Safe Rollback

**Do these BEFORE deploying to production:**

### 1. Backup Database
```bash
# PostgreSQL
pg_dump grading_app_production --format=plain > backup_$(date +%Y%m%d_%H%M%S).sql
gzip backup_*.sql  # Compress for storage

# SQLite
cp grading_app.db grading_app.db.backup_$(date +%Y%m%d_%H%M%S)
tar czf grading_app.db.backup_*.tar.gz  # Compress for storage

# MySQL
mysqldump -u root -p grading_app_production > backup_$(date +%Y%m%d_%H%M%S).sql
gzip backup_*.sql
```

**Verification**:
- [ ] Backup file created
- [ ] Backup size > 0 bytes
- [ ] Backup stored in secure location (not on app server)
- [ ] Backup tested to restore (dry-run)

### 2. Tag Current Code
```bash
git tag -a rollback-point-$(date +%Y%m%d_%H%M%S) \
    -m "Rollback point before encryption feature deployment"
git push origin rollback-point-$(date +%Y%m%d_%H%M%S)
```

### 3. Document Current State
```bash
# Record current state for comparison
git log --oneline -5 > deployment_record.txt
git status >> deployment_record.txt
ps aux | grep python >> deployment_record.txt
```

---

## Rollback Procedure (Step-by-Step)

### Step 1: Assess Situation (5-10 minutes)

```bash
# 1. Check application status
systemctl status grading-app

# 2. Check error logs
tail -100 /var/log/grading-app/app.log | grep -i "error\|failed\|decryption"

# 3. Check database connectivity
python -c "from app import app, db; app.app_context().push(); db.session.execute('SELECT 1')"

# 4. Check if DB_ENCRYPTION_KEY is set
python -c "import os; print('KEY SET' if os.getenv('DB_ENCRYPTION_KEY') else 'KEY MISSING')"
```

**Decision Tree**:
- Application won't start → Go to Step 2
- Decryption failures in logs → Go to Step 3
- Performance issues → Go to Step 4
- Database corruption → Go to Step 5

### Step 2: Immediate Response

**Notify stakeholders** (if not already done):
```
INCIDENT: API key encryption deployment failed
ACTION: Rolling back to previous version
IMPACT: Feature temporarily unavailable, but application will restore to previous state
ETA: 15-30 minutes
```

### Step 3: Stop Application (2-5 minutes)

```bash
# Stop web application
systemctl stop grading-app

# Stop background workers if applicable
systemctl stop grading-app-worker

# Verify all processes stopped
ps aux | grep python | grep grading-app

# Should output: nothing (or only your grep command itself)
```

**Verification**:
- [ ] Application stopped successfully
- [ ] No connections to port 5000
- [ ] Database connections released

### Step 4: Restore Database (5-15 minutes)

**Choose restoration method based on what was backed up:**

#### Option A: Restore from SQL Backup (PostgreSQL)
```bash
# Create new database to restore into
createdb grading_app_restored

# Restore from backup
psql grading_app_restored < backup_20251115_140000.sql

# Verify restore
psql grading_app_restored -c "SELECT COUNT(*) FROM config;"

# Delete old database
dropdb grading_app_production

# Rename restored database
psql -c "ALTER DATABASE grading_app_restored RENAME TO grading_app_production;"
```

#### Option B: Restore from Binary Backup (PostgreSQL)
```bash
# Restore from binary backup
pg_restore -d grading_app_production -Fc backup_20251115_140000.dump
```

#### Option C: Restore SQLite Database
```bash
# Simple file copy
cp grading_app.db grading_app.db.encrypted_failed
cp grading_app.db.backup_20251115_140000 grading_app.db

# Verify database integrity
sqlite3 grading_app.db "PRAGMA integrity_check;"
# Should output: ok
```

#### Option D: Restore MySQL Database
```bash
# Drop current database
mysql -u root -p -e "DROP DATABASE grading_app_production;"

# Create new database
mysql -u root -p -e "CREATE DATABASE grading_app_production;"

# Restore from backup
mysql -u root -p grading_app_production < backup_20251115_140000.sql

# Verify restore
mysql -u root -p -e "USE grading_app_production; SELECT COUNT(*) FROM config;"
```

**Verification**:
- [ ] Database restore completed successfully
- [ ] No restore errors in output
- [ ] Database tables present and contain data
- [ ] Database integrity verified

### Step 5: Revert Code Changes (2-5 minutes)

**Option A: Revert to Previous Git Commit**
```bash
# Find commit to revert to (before encryption feature)
git log --oneline | grep -E "encryption|security|API key" | head -5

# Revert to previous commit (e.g., abc1234)
git revert abc1234  # Creates new commit that undoes changes
# OR revert to known good tag
git checkout main~1  # Go back one commit
# OR revert to specific tag
git checkout v1.0.0-before-encryption
```

**Option B: Revert via Reset (more aggressive)**
```bash
# Only if commits not pushed, or for emergency
git reset --hard HEAD~1  # Undo last 1 commit
# OR reset to specific commit
git reset --hard abc1234
```

**Option C: Remove Feature Conditionally** (if partial rollback needed)
```bash
# If using feature flags, disable encryption
# In .env:
ENCRYPTION_ENABLED=false
DB_ENCRYPTION_KEY=  # Remove key

# In app.py, add:
if os.getenv('ENCRYPTION_ENABLED') != 'true':
    # Use plaintext keys instead
```

**Verification**:
- [ ] Code reverted to pre-encryption version
- [ ] Encryption-related imports removed/disabled
- [ ] No encryption code in application
- [ ] All dependencies match previous version

### Step 6: Remove Encryption Environment Variable (1 minute)

```bash
# Remove DB_ENCRYPTION_KEY from production
unset DB_ENCRYPTION_KEY

# Remove from systemd service if stored there
systemctl edit grading-app
# Remove: Environment="DB_ENCRYPTION_KEY=..."

# Verify it's not set
python -c "import os; print('KEY REMOVED' if not os.getenv('DB_ENCRYPTION_KEY') else 'KEY STILL SET')"

# For secrets manager, delete the secret:
# AWS: aws secretsmanager delete-secret --secret-id grading-app-db-encryption-key
# Vault: vault kv destroy secret/grading-app DB_ENCRYPTION_KEY
```

**Verification**:
- [ ] DB_ENCRYPTION_KEY not accessible to application
- [ ] No encrypted keys being used
- [ ] Application configured to use plaintext keys

### Step 7: Start Application (1-2 minutes)

```bash
# Start with rollback version
systemctl start grading-app

# Verify startup
sleep 10  # Wait for application to start
systemctl status grading-app

# Should show: active (running)

# Check application is responding
curl http://localhost:5000/health
# Should get: 200 response

# Tail logs for startup messages
tail -50 /var/log/grading-app/app.log | grep -v "DEBUG"
```

**Verification**:
- [ ] Application started successfully
- [ ] No errors in startup logs
- [ ] Health check passing
- [ ] Application listening on port 5000

### Step 8: Smoke Tests (5-10 minutes)

```bash
# Test 1: Configuration page loads
curl -I http://localhost:5000/config
# Expected: 200 OK

# Test 2: API key loading works
curl http://localhost:5000/load_config
# Expected: 200 with form data

# Test 3: Basic functionality
curl -X POST http://localhost:5000/save_config \
    -d "openrouter_api_key=test"
# Expected: 200 with success message

# Test 4: Database queries work
python -c "
from app import app, db
from models import Config
with app.app_context():
    config = Config.query.first()
    print(f'Config loaded: {config is not None}')
"
# Expected: Config loaded: True
```

**Verification**:
- [ ] All HTTP endpoints responding with 200
- [ ] Configuration page renders
- [ ] API key save/load works
- [ ] Database queries successful

### Step 9: Check Logs for Errors (5 minutes)

```bash
# Check for decryption errors
grep -i "decryption\|decrypt" /var/log/grading-app/app.log
# Should output: nothing (or only from old entries before rollback)

# Check for import errors
grep -i "import\|module" /var/log/grading-app/app.log | grep -i "error"
# Should output: nothing

# Check for database errors
grep -i "database\|connection" /var/log/grading-app/app.log | grep -i "error"
# Should output: nothing

# Overall error count (should be low)
tail -1000 /var/log/grading-app/app.log | grep -i "error" | wc -l
# Should output: < 10
```

**Verification**:
- [ ] No decryption errors in logs
- [ ] No import errors
- [ ] No database errors
- [ ] Error count minimal

---

## Post-Rollback Verification (15-30 minutes)

### Performance Metrics
```bash
# Check response time for configuration page
time curl http://localhost:5000/load_config > /dev/null
# Should be < 200ms

# Check CPU usage
top -b -n 1 | grep python

# Check memory usage
ps aux | grep python | grep grading-app

# Database query time
python -c "
import time
from app import app, db
from models import Config
with app.app_context():
    start = time.time()
    config = Config.query.first()
    elapsed = time.time() - start
    print(f'Query time: {elapsed*1000:.2f}ms')
"
# Should be < 50ms
```

**Verification**:
- [ ] Response time normal (<500ms)
- [ ] CPU usage normal (< 20%)
- [ ] Memory usage normal (< 200MB)
- [ ] Database queries fast

### Functional Verification
```bash
# Test each provider section loads
providers = ["openrouter", "claude", "openai", "gemini", "zai", "nanogpt", "chutes", "lm_studio", "ollama"]

for provider in providers:
    # Check provider form loads
    # Check provider badges display correctly
    # Test API key save/load for each

echo "✅ All providers functional"
```

**Verification**:
- [ ] Configuration page renders all providers
- [ ] All input fields work
- [ ] API key save/load for all providers
- [ ] Form validation works

### Security Verification
```bash
# Verify no encrypted data in database
sqlite3 grading_app.db "SELECT * FROM config WHERE _openrouter_api_key LIKE 'gAAAAA%';"
# Should return: empty (no gAAAAA-prefixed encrypted values)

# Verify API keys are plaintext (or as stored before)
sqlite3 grading_app.db "SELECT _openrouter_api_key FROM config LIMIT 1;"
# Should show plaintext key, not encrypted

# Verify no encryption-related errors in logs
grep -c "Decryption failed" /var/log/grading-app/app.log
# Should output: 0
```

**Verification**:
- [ ] No encrypted data in restored database
- [ ] API keys are in previous format
- [ ] No decryption errors in logs

---

## Notifying Stakeholders

### Rollback Complete Notification
```
ROLLBACK COMPLETE

Feature: API key encryption
Status: ROLLED BACK to previous version
Database: RESTORED from backup
Application: RESTARTED and verified

All systems operational. Feature will be redeployed after investigation.

Duration: XX minutes
Services Affected: Configuration page (now working)
Users Impacted: None (full restore)

Next Steps:
1. Investigate root cause
2. Fix issues
3. Re-test on staging
4. Redeploy to production
```

---

## Post-Rollback Analysis

### Document What Happened
- [ ] Create incident report with timeline
- [ ] Document all symptoms observed
- [ ] Record all error messages from logs
- [ ] Note any data issues found/fixed
- [ ] List all rollback steps taken

### Investigation Checklist
- [ ] Review deployment logs
- [ ] Check for environment variable issues
- [ ] Verify database state before/after
- [ ] Check for code issues
- [ ] Review test results
- [ ] Identify root cause

### Prevent Future Issues
- [ ] Add more pre-deployment tests
- [ ] Improve error messaging
- [ ] Add monitoring/alerting
- [ ] Create automated rollback script
- [ ] Document lessons learned

---

## Rollback Script (Automated)

For future rollbacks, use this automated script:

```bash
#!/bin/bash
# rollback.sh - Automated rollback procedure

set -e  # Exit on any error

echo "🔴 INITIATING ROLLBACK..."

# 1. Stop application
echo "Stopping application..."
systemctl stop grading-app
sleep 5

# 2. Restore database
echo "Restoring database from backup..."
if [ -f "grading_app.db.backup_*" ]; then
    cp grading_app.db grading_app.db.failed
    cp grading_app.db.backup_* grading_app.db
    echo "✅ Database restored"
else
    echo "❌ Backup file not found!"
    exit 1
fi

# 3. Revert code
echo "Reverting code changes..."
git reset --hard HEAD~1
echo "✅ Code reverted"

# 4. Remove encryption key
echo "Removing encryption key..."
unset DB_ENCRYPTION_KEY
systemctl edit grading-app --drop-in=clear
echo "✅ Key removed"

# 5. Restart application
echo "Restarting application..."
systemctl start grading-app
sleep 10

# 6. Verify
echo "Verifying rollback..."
if curl -f http://localhost:5000/health > /dev/null; then
    echo "✅ ROLLBACK SUCCESSFUL"
    exit 0
else
    echo "❌ ROLLBACK FAILED - Application not responding"
    exit 1
fi
```

**Usage**:
```bash
chmod +x rollback.sh
./rollback.sh
```

---

## Contact Information for Emergency Support

If rollback fails or additional issues arise:

| Role | Name | Phone | Email |
|------|------|-------|-------|
| On-Call DBA | ________ | ________ | ________ |
| On-Call DevOps | ________ | ________ | ________ |
| Engineering Lead | ________ | ________ | ________ |
| CTO | ________ | ________ | ________ |

---

## Appendix: Database Restoration Troubleshooting

### Issue: "Database is locked"
```bash
# Stop all connections
systemctl stop grading-app
fuser -k 5432/tcp  # Kill connections to PostgreSQL port
# Retry restore
```

### Issue: "Duplicate key" errors
```bash
# Truncate tables and retry
psql grading_app -c "TRUNCATE TABLE config CASCADE;"
# Retry restore from backup
```

### Issue: "Not enough disk space"
```bash
# Check disk usage
df -h /
# Free up space (delete old backups, logs, etc.)
# Retry restore
```

### Issue: "Permission denied"
```bash
# Check file permissions
ls -l grading_app.db*
# Fix permissions
chmod 644 grading_app.db
chown postgres:postgres grading_app.db  # PostgreSQL
```

---

**Document Status**: ✅ **Complete** - Ready for emergency use
**Last Updated**: 2025-11-15
**Test Date**: [Should test rollback quarterly]
