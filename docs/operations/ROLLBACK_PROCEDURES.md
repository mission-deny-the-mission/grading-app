# Rollback Procedures

## Overview

This document provides step-by-step procedures for rolling back deployments, database changes, and recovering from critical failures.

## Emergency Rollback Decision Tree

```
Incident Detected
    ├─ Authentication broken? → Database Rollback
    ├─ Application won't start? → Deployment Rollback
    ├─ Data corruption? → Database Recovery + Deployment Rollback
    └─ Performance degradation? → Deployment Rollback (test first)
```

## Pre-Rollback Checklist

Before initiating any rollback:

- [ ] Identify root cause if possible
- [ ] Notify stakeholders (users, team)
- [ ] Backup current state
- [ ] Document incident details
- [ ] Verify rollback target is stable

## Deployment Rollback

### Quick Rollback (Docker/Container)

**Scenario**: Application deployment failed or causing issues

**Time to rollback**: 2-5 minutes

```bash
# 1. List recent deployments
docker ps -a --filter "name=grading-app" --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.CreatedAt}}"

# 2. Stop current deployment
docker stop grading-app

# 3. Start previous version
# Option A: Re-run previous container
docker start <PREVIOUS_CONTAINER_ID>

# Option B: Pull and run previous image tag
docker pull myregistry/grading-app:v1.2.0
docker run -d --name grading-app \
  --env-file .env \
  -p 5000:5000 \
  myregistry/grading-app:v1.2.0

# 4. Verify rollback
curl http://localhost:5000/health
docker logs grading-app --tail 50
```

### Git-Based Rollback

**Scenario**: Direct deployment from git repository

**Time to rollback**: 5-10 minutes

```bash
# 1. Identify last working commit
git log --oneline -10

# 2. Checkout previous version
git checkout <LAST_WORKING_COMMIT>

# 3. Reinstall dependencies (if requirements changed)
pip install -r requirements.txt

# 4. Restart application
systemctl restart grading-app

# 5. Verify
curl http://localhost:5000/health
tail -f /var/log/grading-app.log

# 6. If successful, update main branch
git reset --hard <LAST_WORKING_COMMIT>
git push --force origin main  # CAUTION: Only if authorized
```

### Kubernetes Rollback

**Scenario**: Kubernetes deployment

**Time to rollback**: 1-3 minutes

```bash
# 1. Check rollout history
kubectl rollout history deployment/grading-app

# 2. Rollback to previous revision
kubectl rollout undo deployment/grading-app

# 3. Or rollback to specific revision
kubectl rollout undo deployment/grading-app --to-revision=3

# 4. Monitor rollout
kubectl rollout status deployment/grading-app

# 5. Verify pods
kubectl get pods -l app=grading-app
kubectl logs -l app=grading-app --tail=50
```

## Database Rollback

### SQLite Rollback (Development/Small Deployments)

**Scenario**: Database migration caused issues

**Time to rollback**: 1-2 minutes

```bash
# 1. Stop application
systemctl stop grading-app

# 2. Backup current state (corrupted but preserve evidence)
cp grading_app.db grading_app.db.corrupted.$(date +%Y%m%d_%H%M%S)

# 3. Restore from backup
cp backups/grading_app.db.2024-11-15_10-00-00 grading_app.db

# 4. Verify database integrity
sqlite3 grading_app.db "PRAGMA integrity_check;"

# 5. Check migration state
sqlite3 grading_app.db "SELECT * FROM alembic_version;"

# 6. Restart application
systemctl start grading-app

# 7. Verify
curl http://localhost:5000/api/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

### Alembic Migration Rollback

**Scenario**: Database migration needs to be reversed

**Time to rollback**: 2-5 minutes

```bash
# 1. Check current migration
flask db current

# 2. View migration history
flask db history

# 3. Downgrade to specific version
flask db downgrade <REVISION_ID>

# Or downgrade one step
flask db downgrade -1

# 4. Verify database state
sqlite3 grading_app.db <<EOF
SELECT name FROM sqlite_master WHERE type='table';
SELECT * FROM alembic_version;
EOF

# 5. Restart application
systemctl restart grading-app
```

### PostgreSQL Rollback (Production)

**Scenario**: Production database needs rollback

**Time to rollback**: 10-30 minutes (depends on size)

```bash
# 1. Stop application to prevent new writes
systemctl stop grading-app

# 2. Create snapshot of current state (if not corrupted)
pg_dump -U postgres -h localhost grading_app > \
  backups/grading_app.corrupted.$(date +%Y%m%d_%H%M%S).sql

# 3. Drop current database
psql -U postgres -c "DROP DATABASE grading_app;"

# 4. Create fresh database
psql -U postgres -c "CREATE DATABASE grading_app;"

# 5. Restore from backup
psql -U postgres -h localhost grading_app < \
  backups/grading_app.2024-11-15_10-00-00.sql

# 6. Verify data
psql -U postgres -d grading_app -c "SELECT COUNT(*) FROM users;"
psql -U postgres -d grading_app -c "SELECT version_num FROM alembic_version;"

# 7. Restart application
systemctl start grading-app
```

## Encryption Key Recovery

### Scenario: DB_ENCRYPTION_KEY Lost or Corrupted

**Critical**: Without encryption key, encrypted data is UNRECOVERABLE

#### If You Have Key Backup

```bash
# 1. Stop application
systemctl stop grading-app

# 2. Restore key from secure backup
cp /secure/backup/encryption.key /etc/grading-app/DB_ENCRYPTION_KEY

# 3. Update environment
export DB_ENCRYPTION_KEY=$(cat /etc/grading-app/DB_ENCRYPTION_KEY)

# 4. Verify key format
python3 <<EOF
from cryptography.fernet import Fernet
try:
    Fernet(open('/etc/grading-app/DB_ENCRYPTION_KEY').read().strip().encode())
    print("Key valid")
except Exception as e:
    print(f"Key invalid: {e}")
EOF

# 5. Restart application
systemctl start grading-app

# 6. Test encryption
curl -X POST http://localhost:5000/api/test-encryption
```

#### If Key is Lost (DISASTER SCENARIO)

**WARNING**: Encrypted data CANNOT be recovered without the key.

```bash
# 1. Assess data loss
# - Which fields are encrypted?
# - Can users re-enter this data?
# - Is there any backup with old key?

# 2. If no recovery possible, generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 3. Update .env
export DB_ENCRYPTION_KEY="NEW_KEY"

# 4. Clear encrypted fields (they're unrecoverable)
sqlite3 grading_app.db <<EOF
-- Example: Clear encrypted fields
-- UPDATE users SET encrypted_field = NULL;
EOF

# 5. Notify users
# - Send email explaining data loss
# - Request re-entry of affected data
# - Provide support resources
```

## Emergency Access Procedures

### Locked Out of Admin Account

```bash
# 1. Access database directly
sqlite3 grading_app.db

# 2. Unlock admin account
UPDATE users
SET locked_until = NULL, failed_login_attempts = 0
WHERE email = 'admin@example.com';

# 3. Or create emergency admin
INSERT INTO users (id, email, password_hash, is_admin, is_active, created_at)
VALUES (
  lower(hex(randomblob(16))),
  'emergency@localhost',
  -- Password: EmergencyPass123!
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeD.e4hIxjVFUwjVC',
  1,
  1,
  datetime('now')
);

# 4. Exit database
.exit

# 5. Login with emergency account
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"emergency@localhost","password":"EmergencyPass123!"}'
```

### Reset All User Passwords (Mass Breach)

```bash
# 1. Stop application to prevent logins during reset
systemctl stop grading-app

# 2. Invalidate all password reset tokens
redis-cli FLUSHDB

# 3. Lock all accounts temporarily
sqlite3 grading_app.db <<EOF
UPDATE users
SET locked_until = datetime('now', '+1 day'),
    failed_login_attempts = 0
WHERE email != 'emergency@localhost';
EOF

# 4. Send password reset emails to all users
# (Implement bulk email script)
python scripts/send_mass_password_reset.py

# 5. Restart application
systemctl start grading-app

# 6. Monitor password reset activity
tail -f /var/log/grading-app.log | grep "password_reset"
```

## Redis Recovery

### Clear All Sessions (Force Logout)

```bash
# 1. Backup Redis state (optional)
redis-cli --rdb backups/redis_$(date +%Y%m%d_%H%M%S).rdb

# 2. Flush database (clears all sessions and password reset tokens)
redis-cli FLUSHDB

# 3. Verify
redis-cli DBSIZE
# Should return: (integer) 0

# 4. Users will need to log in again
# Password reset tokens are cleared
```

### Recover Password Reset Tokens

```bash
# If you need to restore tokens after accidental flush

# 1. Stop generating new tokens
# (Disable password reset endpoint temporarily)

# 2. Restore from Redis backup
redis-cli --rdb backups/redis_TIMESTAMP.rdb

# 3. Re-enable password reset
```

## Rollback Verification

### Post-Rollback Checks

```bash
# 1. Health Check
curl http://localhost:5000/health

# 2. Authentication Test
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}'

# 3. Database Integrity
sqlite3 grading_app.db "PRAGMA integrity_check;"

# 4. Check Logs for Errors
tail -100 /var/log/grading-app.log | grep -i error

# 5. Monitor Application
watch -n 1 'systemctl status grading-app'

# 6. User Acceptance Test
# - Login as admin
# - Login as regular user
# - Create test project
# - Submit test grading job
```

## Documentation After Rollback

After successful rollback, document:

1. **Incident Details**:
   - What failed?
   - When was it detected?
   - What was the impact?

2. **Rollback Actions**:
   - Which rollback procedure was used?
   - How long did it take?
   - Were there any issues?

3. **Root Cause**:
   - What caused the failure?
   - How can we prevent it?

4. **Preventive Measures**:
   - Additional testing needed?
   - Monitoring improvements?
   - Process changes?

## Rollback Testing

### Quarterly Rollback Drills

```bash
# Practice rollback in staging environment

# 1. Deploy new version
git tag rollback-test-v1.0.0
docker build -t grading-app:rollback-test .

# 2. Introduce intentional failure
# (Simulated database corruption, config error, etc.)

# 3. Execute rollback procedure
# (Follow procedures above)

# 4. Time the rollback
# - Start time
# - Detection time
# - Rollback completion
# - Verification completion

# 5. Document lessons learned
```

## Escalation Contacts

If rollback fails or you need assistance:

- **Primary On-Call**: oncall@example.com
- **Database Admin**: dba@example.com
- **DevOps Lead**: devops@example.com
- **CTO (Emergency)**: cto@example.com

## Backup Schedule

Ensure backups are available for rollback:

- **Database**: Hourly backups, retained 7 days
- **Application**: Tagged releases in git/Docker registry
- **Configuration**: Version controlled in git
- **Encryption Keys**: Secured in vault, backed up offline

## Version History

- v1.0 (2025-11-15): Initial rollback procedures
