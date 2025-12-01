# Deployment Guide - Multi-User Authentication System

## Overview

This guide covers deploying the grading application in both single-user and multi-user modes. The application supports flexible deployment with zero-configuration single-user mode and optional multi-user authentication with user management.

## Prerequisites

- Python 3.13.7+
- PostgreSQL 12+ (recommended) or SQLite (development)
- Redis (optional, for session storage)
- SMTP server (for password reset emails in multi-user mode)

## Quick Start

### Single-User Mode (Default)

Single-user mode requires zero configuration and provides immediate access to all features without authentication.

1. **Install Dependencies**

```bash
pip install -r requirements.txt
```

2. **Set Environment Variables**

Create `.env` file:

```bash
SECRET_KEY=your-secure-random-key
DATABASE_URL=sqlite:///grading_app.db
DEPLOYMENT_MODE=single-user
```

3. **Initialize Database**

```bash
flask db upgrade
```

4. **Run Application**

```bash
flask run
```

Access at `http://localhost:5000` - no login required!

### Multi-User Mode

Multi-user mode enables authentication, user management, project sharing, and usage quotas.

1. **Install Dependencies**

```bash
pip install -r requirements.txt
```

2. **Configure Environment**

Create `.env` file:

```bash
# Required
SECRET_KEY=your-very-secure-random-key-min-32-chars
DATABASE_URL=postgresql://user:password@localhost:5432/grading_app
DEPLOYMENT_MODE=multi-user

# Optional - Email for password reset
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourdomain.com

# Optional - Security
SESSION_COOKIE_SECURE=True  # HTTPS only
REMEMBER_COOKIE_SECURE=True  # HTTPS only
```

3. **Initialize Database**

```bash
flask db upgrade
```

4. **Create First Admin User**

```python
from app import app
from services.auth_service import AuthService

with app.app_context():
    admin = AuthService.create_user(
        email="admin@yourdomain.com",
        password="SecurePassword123!",
        display_name="Admin User",
        is_admin=True
    )
    print(f"Admin user created: {admin.email}")
```

5. **Run Application**

```bash
# Development
flask run

# Production with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Access at `http://localhost:5000/auth/login`

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

**Docker Compose:**

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/grading_app
      - DEPLOYMENT_MODE=multi-user
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=grading_app
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | Flask secret key (min 32 chars) |
| `DATABASE_URL` | Yes | sqlite:/// | Database connection string |
| `DEPLOYMENT_MODE` | No | single-user | single-user or multi-user |
| `SESSION_COOKIE_SECURE` | No | True | HTTPS-only cookies |
| `REMEMBER_COOKIE_SECURE` | No | True | HTTPS-only remember me |
| `SMTP_SERVER` | No | - | SMTP server for emails |
| `SMTP_PORT` | No | 587 | SMTP port |
| `SMTP_USERNAME` | No | - | SMTP username |
| `SMTP_PASSWORD` | No | - | SMTP password |
| `SMTP_FROM` | No | - | From email address |

### Database Configuration

**PostgreSQL (Recommended for Production):**

```bash
DATABASE_URL=postgresql://username:password@localhost:5432/grading_app
```

**SQLite (Development Only):**

```bash
DATABASE_URL=sqlite:///grading_app.db
```

### Security Configuration

**Production Checklist:**

- [ ] Set strong `SECRET_KEY` (32+ random characters)
- [ ] Enable HTTPS (set `SESSION_COOKIE_SECURE=True`)
- [ ] Use PostgreSQL (not SQLite)
- [ ] Configure firewall (allow only 80/443)
- [ ] Set up SSL certificates
- [ ] Configure SMTP for password resets
- [ ] Enable logging and monitoring
- [ ] Regular database backups

## Switching Deployment Modes

### From Single-User to Multi-User

1. **Stop Application**

```bash
# Stop running application
```

2. **Update Environment**

```bash
# In .env
DEPLOYMENT_MODE=multi-user
```

3. **Create Admin User**

```python
from app import app
from services.auth_service import AuthService

with app.app_context():
    AuthService.create_user(
        email="admin@yourdomain.com",
        password="SecurePassword123!",
        is_admin=True
    )
```

4. **Restart Application**

All existing data is preserved. Users must now log in to access the system.

### From Multi-User to Single-User

1. **Stop Application**

2. **Update Environment**

```bash
# In .env
DEPLOYMENT_MODE=single-user
```

3. **Restart Application**

All data preserved, authentication bypassed. Anyone with access can use all features.

## Migration Guide

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description of changes"

# Review migration file
cat migrations/versions/xxxxx_description.py

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

### Backup and Restore

**PostgreSQL Backup:**

```bash
# Backup
pg_dump -U postgres grading_app > backup_$(date +%Y%m%d).sql

# Restore
psql -U postgres grading_app < backup_20250115.sql
```

**SQLite Backup:**

```bash
# Backup
cp grading_app.db grading_app_backup_$(date +%Y%m%d).db

# Restore
cp grading_app_backup_20250115.db grading_app.db
```

## Troubleshooting

### Common Issues

**Issue:** Login redirects to login page
**Solution:** Check `DEPLOYMENT_MODE=multi-user` and session cookies enabled

**Issue:** Password reset emails not sending
**Solution:** Verify SMTP configuration and credentials

**Issue:** Database connection errors
**Solution:** Verify `DATABASE_URL` format and database is running

**Issue:** Rate limiting triggers too early
**Solution:** Check rate limit configuration in `app.py`

### Logs

```bash
# View application logs
tail -f logs/app.log

# View Flask debug logs
FLASK_DEBUG=1 flask run
```

### Health Checks

```bash
# Check deployment mode
curl http://localhost:5000/api/config/deployment-mode

# Check application health
curl http://localhost:5000/api/config/health
```

## Performance Tuning

### Database Optimization

```python
# Add indexes for frequently queried fields
# models.py
owner_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
```

### Caching

```python
# Use Redis for session storage
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
```

### Rate Limiting

Adjust rate limits in `app.py`:

```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["2000 per day", "200 per hour"],  # Increased limits
    storage_uri="redis://localhost:6379"  # Use Redis for production
)
```

## Monitoring

### Metrics to Track

- Request rate and response times
- Authentication success/failure rates
- Database query performance
- Error rates by endpoint
- User session durations
- Quota usage and enforcement

### Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

## Security Best Practices

1. **Authentication:**
   - Enforce strong password requirements
   - Implement account lockout after failed attempts
   - Use secure session management

2. **Authorization:**
   - Verify ownership before granting access
   - Implement role-based access control
   - Validate permissions on every request

3. **Data Protection:**
   - Use HTTPS in production
   - Encrypt sensitive data at rest
   - Regular security audits

4. **Session Security:**
   - Secure, HTTP-only cookies
   - Session timeout enforcement
   - CSRF protection enabled

## Support

For additional help:
- API Documentation: `claudedocs/API_DOCUMENTATION.md`
- Testing Guide: `claudedocs/TESTING_GUIDE.md`
- Security Documentation: `claudedocs/SECURITY_*.md`
