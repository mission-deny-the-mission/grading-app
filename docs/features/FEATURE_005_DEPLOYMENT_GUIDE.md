# Feature 005: Marking Schemes as Files - Deployment Guide

## Prerequisites

### System Requirements
- Python 3.9+
- PostgreSQL 12+ (production) or SQLite 3.35+ (development/desktop)
- Redis 6+ (for Celery task queue)
- 2GB RAM minimum for web server
- 50MB disk space for exports directory

### Dependencies
All dependencies are listed in `requirements.txt`:
- Flask 2.3.3+
- Flask-SQLAlchemy 3.0.5+
- Celery 5.x (for async document processing)
- PyPDF2 3.0.1 (PDF parsing)
- python-docx 0.8.11 (Word document parsing)
- Pillow (image handling)

## Installation Steps

### 1. Install Python Dependencies

```bash
# From project root
pip install -r requirements.txt

# Or install specific dependencies
pip install PyPDF2==3.0.1 python-docx==0.8.11 Pillow celery[redis]
```

### 2. Configure Environment Variables

Create or update `.env` file:

```bash
# AI Provider Configuration
OPENROUTER_API_KEY=your_openrouter_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here_min_32_chars
FLASK_ENV=production

# Database
DATABASE_URL=postgresql://user:pass@localhost/grading_db  # Production
# DATABASE_URL=sqlite:///instance/grading.db               # Development

# File Upload Settings
MAX_UPLOAD_SIZE=10485760  # 10 MB in bytes
UPLOAD_FOLDER=./uploads
EXPORT_FOLDER=./exports

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Task Queue Settings
CELERY_TASK_TRACK_STARTED=True
CELERY_TASK_TIME_LIMIT=600  # 10 minutes max per task
```

### 3. Create Required Directories

```bash
# Create directories for file storage
mkdir -p uploads exports

# Set appropriate permissions
chmod 755 uploads exports

# For production with separate user
chown www-data:www-data uploads exports  # Adjust user as needed
```

### 4. Database Setup

No new migrations are required for Feature 005 - it uses the existing schema.

```bash
# If running migrations anyway
flask db upgrade

# Verify tables exist
flask db current
```

### 5. Start Celery Worker (Required for Document Processing)

**Development:**
```bash
# Single worker for development
celery -A tasks worker --loglevel=info

# With concurrency control
celery -A tasks worker --loglevel=info --concurrency=2
```

**Production (systemd service):**

Create `/etc/systemd/system/celery-grading-app.service`:

```ini
[Unit]
Description=Celery Worker for Grading App
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/grading-app
Environment="PATH=/var/www/grading-app/venv/bin"
ExecStart=/var/www/grading-app/venv/bin/celery multi start worker \
    -A tasks \
    --pidfile=/var/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log \
    --loglevel=info \
    --concurrency=4
ExecStop=/var/www/grading-app/venv/bin/celery multi stopwait worker \
    --pidfile=/var/run/celery/%n.pid
ExecReload=/var/www/grading-app/venv/bin/celery multi restart worker \
    --pidfile=/var/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log \
    --loglevel=info \
    --concurrency=4

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-grading-app
sudo systemctl start celery-grading-app
sudo systemctl status celery-grading-app
```

### 6. Configure Web Server

**Flask Development Server:**
```bash
flask run --host=0.0.0.0 --port=5000
```

**Production (Gunicorn):**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app
```

**Production (systemd service):**

Create `/etc/systemd/system/grading-app.service`:

```ini
[Unit]
Description=Grading App Web Service
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/grading-app
Environment="PATH=/var/www/grading-app/venv/bin"
ExecStart=/var/www/grading-app/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --timeout 120 \
    --log-level info \
    --access-logfile /var/log/grading-app/access.log \
    --error-logfile /var/log/grading-app/error.log \
    app:app

[Install]
WantedBy=multi-user.target
```

## Configuration Details

### File Upload Limits

```python
# In your Flask app configuration
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
```

### Export File Naming

Exports are automatically named with:
- Scheme name (sanitized)
- Timestamp (ISO 8601 date)
- Random 8-character hex suffix

Example: `Essay_Rubric_2025-11-18_a1b2c3d4.json`

### File Storage

**Development/Desktop:**
- Uploads: `./uploads/`
- Exports: `./exports/`

**Production:**
- Uploads: `/var/www/grading-app/uploads/`
- Exports: `/var/www/grading-app/exports/`

Consider using S3 or similar for production:
```python
# Example S3 configuration
AWS_ACCESS_KEY_ID='your_key'
AWS_SECRET_ACCESS_KEY='your_secret'
AWS_S3_BUCKET='grading-app-exports'
```

## Security Configuration

### File Validation

Ensure MIME type checking is enabled:

```python
# In routes/scheme_document.py
import magic

def validate_file(file):
    mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)
    return mime in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
```

### Path Traversal Prevention

Filenames are sanitized automatically:

```python
from werkzeug.utils import secure_filename

safe_filename = secure_filename(user_provided_filename)
```

### Authentication

All endpoints require authentication:

```python
from flask_login import login_required

@bp.route('/api/schemes/<scheme_id>/export')
@login_required
def export_scheme(scheme_id):
    # ...
```

### File Cleanup

Set up a cron job to clean old exports:

```bash
# /etc/cron.daily/cleanup-exports
#!/bin/bash
find /var/www/grading-app/exports -type f -mtime +30 -delete
```

## Monitoring & Logging

### Application Logs

```python
# Configure logging in app.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/grading-app/app.log'),
        logging.StreamHandler()
    ]
)
```

### Celery Logs

Monitor Celery worker status:

```bash
# Check worker status
celery -A tasks inspect active

# Monitor queue depth
celery -A tasks inspect reserved

# View worker stats
celery -A tasks inspect stats
```

### Export Metrics

Track export/import activity:

```sql
-- Query export statistics
SELECT
    DATE(created_at) as export_date,
    COUNT(*) as exports_count
FROM scheme_exports
GROUP BY DATE(created_at)
ORDER BY export_date DESC;
```

## Performance Tuning

### Database Connection Pool

```python
# In app.py
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20
```

### Celery Concurrency

Adjust based on CPU cores:

```bash
# 2x CPU cores for I/O-bound tasks
celery -A tasks worker --concurrency=8
```

### File Processing Timeout

```python
# In tasks.py
@app.task(time_limit=600)  # 10 minutes
def process_document(file_path, scheme_id):
    # ...
```

## Backup & Recovery

### Export Directory Backup

```bash
# Daily backup of exports
tar -czf exports_backup_$(date +%Y%m%d).tar.gz exports/

# Upload to S3 or similar
aws s3 cp exports_backup_*.tar.gz s3://backups/grading-app/
```

### Database Backup

```bash
# Backup PostgreSQL
pg_dump grading_db > grading_db_backup_$(date +%Y%m%d).sql

# Restore if needed
psql grading_db < grading_db_backup_20251118.sql
```

## Scaling Considerations

### Horizontal Scaling

1. **Multiple Web Servers**: Use load balancer (Nginx, HAProxy)
2. **Shared File Storage**: Use S3, NFS, or distributed storage
3. **Celery Workers**: Run workers on separate servers
4. **Redis Cluster**: For high availability

### Vertical Scaling

1. **Database**: Increase connection pool size
2. **Celery**: Increase worker concurrency
3. **Web Servers**: Add more Gunicorn workers

## Troubleshooting

### Common Issues

**"Celery worker not processing tasks"**
```bash
# Check Redis connection
redis-cli ping

# Restart Celery
sudo systemctl restart celery-grading-app

# Check logs
tail -f /var/log/celery/worker1.log
```

**"File upload fails with 413 Payload Too Large"**
```python
# Increase max upload size in Nginx
client_max_body_size 10M;

# Reload Nginx
sudo systemctl reload nginx
```

**"Export files not accessible"**
```bash
# Check permissions
ls -la exports/

# Fix permissions
chmod 755 exports/
chown www-data:www-data exports/
```

**"Document processing timeout"**
```python
# Increase task time limit
@app.task(time_limit=1200)  # 20 minutes
```

## Health Checks

### Endpoint Health

```bash
# Check API availability
curl -f http://localhost:5000/health || exit 1
```

### Celery Health

```bash
# Check worker heartbeat
celery -A tasks inspect ping

# Expected output:
# worker1@hostname: OK
```

### Storage Health

```bash
# Check disk space
df -h /var/www/grading-app/exports

# Alert if > 80% full
```

## Rollback Procedure

If deployment fails:

```bash
# 1. Stop services
sudo systemctl stop grading-app celery-grading-app

# 2. Rollback code
git checkout previous_release_tag

# 3. Restore database (if needed)
psql grading_db < backup_before_deployment.sql

# 4. Restart services
sudo systemctl start grading-app celery-grading-app

# 5. Verify health
curl http://localhost:5000/health
```

## Post-Deployment Verification

### Smoke Tests

```bash
# 1. Export a scheme
curl -X GET "http://localhost:5000/api/schemes/test-id/export" \
  -H "Authorization: Bearer $TOKEN" \
  -o test_export.json

# 2. Import the scheme
curl -X POST "http://localhost:5000/api/schemes/import" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_export.json

# 3. Upload a test document
curl -X POST "http://localhost:5000/api/schemes/test-id/upload-document" \
  -H "Authorization: Bearer $TOKEN" \
  -F "document=@test.pdf"
```

### Monitoring Checklist

- [ ] Web server responding (200 OK)
- [ ] Celery workers active
- [ ] Redis connection stable
- [ ] Database connection pool healthy
- [ ] Export directory writable
- [ ] Upload directory writable
- [ ] Logs being written
- [ ] No error spikes in logs

## Support

For deployment issues:
- Check logs: `/var/log/grading-app/`
- Review systemd status: `systemctl status grading-app celery-grading-app`
- Contact DevOps: devops@example.com

---

*Last Updated*: 2025-11-18
*Feature*: 005 - Marking Schemes as Files
*Environment*: Production | Staging | Development
