# Security Incident Response Procedures

## Overview

This document outlines procedures for responding to security incidents in the grading application authentication system.

## Incident Classification

### Critical (P0)
- Data breach affecting user credentials
- Unauthorized admin access
- Encryption key compromise
- System-wide authentication bypass

### High (P1)
- Multiple failed login attempts across accounts
- Unauthorized access to user data
- Session hijacking attempts
- Suspicious admin activity

### Medium (P2)
- Individual account compromise
- Password reset abuse
- API rate limit bypass
- XSS/CSRF attempts

### Low (P3)
- Failed login attempts (normal brute force)
- Invalid token submissions
- Minor configuration issues

## Immediate Response Steps

### Step 1: Detection and Triage (0-15 minutes)

1. **Identify the incident type**:
   - Check system logs (`/logs`)
   - Review authentication logs (`services/auth_service.py`)
   - Monitor rate limiter alerts
   - Check Redis for suspicious patterns

2. **Assess severity**:
   - Number of affected users
   - Type of data accessed
   - Current ongoing status
   - Potential impact

3. **Initial containment**:
   ```bash
   # For critical incidents, consider temporary shutdown
   systemctl stop grading-app

   # Or disable specific features
   export DISABLE_REGISTRATION=true
   export DISABLE_PASSWORD_RESET=true
   ```

### Step 2: Investigation (15-60 minutes)

1. **Collect evidence**:
   ```bash
   # Export authentication logs
   grep "Authentication failed" /var/log/grading-app.log > incident_auth.log

   # Check database for compromised accounts
   sqlite3 grading_app.db "SELECT * FROM users WHERE locked_until IS NOT NULL"

   # Review Redis for suspicious tokens
   redis-cli KEYS "password_reset:*"
   ```

2. **Identify attack vector**:
   - SQL injection attempts
   - CSRF token bypass
   - Session fixation
   - Credential stuffing
   - API abuse

3. **Document timeline**:
   - First detection time
   - Attack start time (from logs)
   - Actions taken
   - Current status

### Step 3: Containment (Within 1 hour)

#### Data Breach Response

1. **Lock affected accounts**:
   ```python
   from models import User, db
   from datetime import datetime, timedelta, timezone

   # Lock specific user
   user = User.query.filter_by(email='compromised@example.com').first()
   user.locked_until = datetime.now(timezone.utc) + timedelta(hours=24)
   db.session.commit()
   ```

2. **Invalidate sessions**:
   ```bash
   # Clear all sessions in Redis (if using Redis for sessions)
   redis-cli FLUSHDB

   # Or force logout all users by clearing Flask sessions
   # Restart application to clear in-memory sessions
   ```

3. **Disable compromised features**:
   ```python
   # In app.py or via environment variable
   if INCIDENT_MODE:
       # Disable registration
       # Disable password reset
       # Enable strict rate limiting
   ```

#### Unauthorized Access Response

1. **Revoke admin privileges**:
   ```python
   user = User.query.filter_by(email='suspicious@example.com').first()
   user.is_admin = False
   db.session.commit()
   ```

2. **Review access logs**:
   ```bash
   # Find all actions by suspicious user
   grep "user_id: SUSPICIOUS_ID" /var/log/grading-app.log
   ```

3. **Audit data access**:
   ```sql
   -- Check what data was accessed
   SELECT * FROM usage_records WHERE user_id = 'SUSPICIOUS_ID';
   SELECT * FROM project_shares WHERE granted_by = 'SUSPICIOUS_ID';
   ```

### Step 4: Eradication (1-4 hours)

1. **Patch vulnerabilities**:
   - Apply security updates
   - Fix identified code issues
   - Update dependencies

2. **Reset compromised credentials**:
   - Force password resets for affected users
   - Rotate encryption keys if necessary
   - Regenerate SECRET_KEY if compromised

3. **Clean malicious data**:
   - Remove unauthorized accounts
   - Delete suspicious project shares
   - Clear malicious usage records

### Step 5: Recovery (4-24 hours)

1. **Restore normal operations**:
   ```bash
   # Re-enable services
   export DISABLE_REGISTRATION=false
   export DISABLE_PASSWORD_RESET=false

   # Restart application
   systemctl start grading-app
   ```

2. **Unlock legitimate accounts**:
   ```python
   # Unlock all locked accounts after investigation
   locked_users = User.query.filter(User.locked_until.isnot(None)).all()
   for user in locked_users:
       user.locked_until = None
       user.failed_login_attempts = 0
   db.session.commit()
   ```

3. **Monitor closely**:
   - Watch for repeat attempts
   - Monitor error rates
   - Check authentication success rates

## Specific Incident Procedures

### Breach Response

1. **Immediate Actions**:
   - Activate incident response team
   - Preserve evidence (logs, database snapshots)
   - Notify affected users within 72 hours (GDPR requirement)
   - Contact legal/compliance teams

2. **Data Assessment**:
   ```python
   # Identify exposed data
   affected_users = User.query.filter(
       User.last_login.between(incident_start, incident_end)
   ).all()

   print(f"Affected users: {len(affected_users)}")
   print(f"Data exposed: [emails, hashed_passwords, projects, usage_data]")
   ```

3. **User Communication**:
   - Email all affected users
   - Provide password reset instructions
   - Explain what data was exposed
   - Offer support resources

### Password Reset Abuse

1. **Detect abuse pattern**:
   ```bash
   # Check for mass password reset requests
   redis-cli KEYS "password_reset:*" | wc -l
   ```

2. **Rate limit enforcement**:
   ```python
   # Tighten rate limits temporarily
   from app import limiter

   @limiter.limit("1 per hour")
   @app.route("/api/auth/password-reset")
   def password_reset():
       # ...
   ```

3. **Clear suspicious tokens**:
   ```bash
   # Remove all password reset tokens
   redis-cli KEYS "password_reset:*" | xargs redis-cli DEL
   ```

### Account Lockout Mass Event

1. **Identify cause**:
   - Automated attack
   - Configuration error
   - Bug in lockout logic

2. **Bulk unlock if false positive**:
   ```python
   from models import User, db

   # If lockout was triggered by bug
   User.query.update({
       'locked_until': None,
       'failed_login_attempts': 0
   })
   db.session.commit()
   ```

3. **Prevent recurrence**:
   - Fix lockout logic
   - Add better detection
   - Implement unlock API for admins

### Encryption Key Compromise

**CRITICAL**: If DB_ENCRYPTION_KEY is compromised, all encrypted data must be re-encrypted.

1. **Generate new key**:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Re-encrypt data**:
   ```python
   from cryptography.fernet import Fernet
   from models import User, db

   old_key = Fernet(OLD_DB_ENCRYPTION_KEY.encode())
   new_key = Fernet(NEW_DB_ENCRYPTION_KEY.encode())

   # Re-encrypt all encrypted fields
   # NOTE: Implementation depends on which fields are encrypted
   # This is a placeholder for the process
   users = User.query.all()
   for user in users:
       if hasattr(user, 'encrypted_field'):
           decrypted = old_key.decrypt(user.encrypted_field.encode())
           user.encrypted_field = new_key.encrypt(decrypted).decode()
   db.session.commit()
   ```

3. **Update environment**:
   ```bash
   # Update .env file
   export DB_ENCRYPTION_KEY="NEW_KEY_HERE"

   # Restart application
   systemctl restart grading-app
   ```

## Post-Incident Activities

### 1. Root Cause Analysis (Within 7 days)

Document:
- What happened
- How it was detected
- What was the root cause
- What was the impact
- How it was resolved
- What was learned

### 2. Preventive Measures

Implement:
- Additional monitoring
- Enhanced logging
- Improved rate limiting
- Security patches
- Code reviews

### 3. User Communication

Follow-up:
- Send resolution notification
- Explain preventive measures
- Restore user confidence
- Offer support

### 4. Security Improvements

Update:
- Security policies
- Response procedures
- Monitoring systems
- Testing procedures

## Escalation Contacts

### Internal Team
- **Security Lead**: security@example.com
- **System Admin**: admin@example.com
- **On-Call Engineer**: oncall@example.com

### External
- **Cloud Provider**: AWS/GCP/Azure support
- **Legal Counsel**: legal@example.com
- **Data Protection Officer**: dpo@example.com

## Tools and Resources

### Monitoring
- Application logs: `/var/log/grading-app.log`
- Authentication logs: `grep "Authentication" logs`
- Database: `sqlite3 grading_app.db`
- Redis: `redis-cli`

### Scripts
- `scripts/verify_env.py`: Check configuration
- `scripts/generate_secrets.sh`: Generate new keys
- Manual recovery scripts (create as needed)

## Testing Response Procedures

### Quarterly Drills
1. Simulate breach scenario
2. Test response timeline
3. Verify communication channels
4. Update procedures based on learnings

### Annual Review
- Review all incidents
- Update procedures
- Train team members
- Test disaster recovery

## Compliance Requirements

### Data Protection (GDPR)
- Breach notification within 72 hours
- Document all incidents
- Report to supervisory authority
- Notify affected data subjects

### Industry Standards
- Follow NIST incident response framework
- Comply with SOC 2 requirements
- Maintain audit trail
- Preserve evidence

## Version History

- v1.0 (2025-11-15): Initial incident response procedures
