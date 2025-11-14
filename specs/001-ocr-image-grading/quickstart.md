# Quickstart: OCR and Image Grading Development

**Feature Branch**: `001-ocr-image-grading`
**Date**: 2025-11-14

## Prerequisites

- Python 3.13.7
- PostgreSQL (or SQLite for development)
- Redis 5.0.1+ (for Celery)
- Docker + Docker Compose (recommended)
- Azure Computer Vision API key (or alternative OCR provider)

---

## Local Development Setup

### 1. Clone and Setup Repository

```bash
# Switch to feature branch
git checkout 001-ocr-image-grading

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install new dependencies for this feature
pip install opencv-python-headless==4.12.0.88 \
            azure-cognitiveservices-vision-computervision \
            msrest \
            python-magic \
            Pillow
```

### 2. Environment Configuration

Create or update `.env` file:

```bash
# Existing configuration
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=postgresql://admin:password@localhost/grading_platform
# or: DATABASE_URL=sqlite:///grading_app.db
REDIS_URL=redis://localhost:6379/0

# Existing AI provider keys
CLAUDE_API_KEY=your_claude_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# NEW: OCR Configuration
AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_VISION_KEY=your_azure_vision_key

# Optional: Alternative OCR providers
# GOOGLE_VISION_KEY=your_google_vision_key
# TESSERACT_PATH=/usr/bin/tesseract  # For self-hosted Tesseract

# NEW: Image Storage Configuration
UPLOAD_FOLDER=/app/uploads
MAX_CONTENT_LENGTH=52428800  # 50MB in bytes

# NEW: Image Quality Thresholds
BLUR_THRESHOLD=100.0  # Laplacian variance threshold
MIN_IMAGE_WIDTH=800
MIN_IMAGE_HEIGHT=600
```

### 3. Database Migrations

```bash
# Initialize Alembic (if not already initialized)
flask db init

# Generate migration for new tables
flask db migrate -m "Add OCR and image grading tables"

# Review migration file in migrations/versions/
# Ensure it creates: image_submissions, extracted_content,
# image_quality_metrics, image_validation_criteria, image_validation_results

# Apply migration
flask db upgrade

# Verify tables created
flask db current
```

### 4. Start Services

#### Option A: Docker Compose (Recommended)

```bash
# Start all services (Flask, PostgreSQL, Redis, Celery)
docker-compose up -d

# View logs
docker-compose logs -f flask_app
docker-compose logs -f celery_worker

# Stop services
docker-compose down
```

#### Option B: Manual Service Start

**Terminal 1: PostgreSQL**
```bash
# If not using Docker
postgres -D /usr/local/var/postgres
```

**Terminal 2: Redis**
```bash
redis-server
```

**Terminal 3: Celery Worker**
```bash
celery -A tasks worker --loglevel=info --concurrency=4
```

**Terminal 4: Flask App**
```bash
flask run --host=0.0.0.0 --port=5000
```

### 5. Create Upload Directory

```bash
# Create uploads directory with proper structure
mkdir -p uploads
chmod 755 uploads

# The application will automatically create subdirectories
# using two-level UUID hashing (e.g., uploads/F3/B1/)
```

---

## Development Workflow

### Test-Driven Development (TDD) Pattern

**Step 1: Write Tests First**
```bash
# Create test file for your feature
touch tests/test_image_processing.py
```

Example test structure:
```python
# tests/test_image_processing.py
import pytest
from models import ImageSubmission, ExtractedContent
from utils.image_processing import detect_blur, check_resolution

class TestImageUpload:
    def test_upload_valid_image(self, client, test_image_png):
        """Test uploading a valid PNG image"""
        response = client.post(
            '/api/submissions/test-sub-id/images',
            data={'image': (test_image_png, 'test.png')},
            content_type='multipart/form-data'
        )
        assert response.status_code == 201
        assert 'id' in response.json

class TestBlurDetection:
    def test_detect_sharp_image(self, sharp_test_image):
        """Test blur detection on sharp image"""
        result = detect_blur(sharp_test_image)
        assert result['is_blurry'] == False
        assert result['blur_score'] > 100.0

    def test_detect_blurry_image(self, blurry_test_image):
        """Test blur detection on blurry image"""
        result = detect_blur(blurry_test_image)
        assert result['is_blurry'] == True
        assert result['blur_score'] < 100.0
```

**Step 2: Run Tests (They Should Fail)**
```bash
# Run specific test file
pytest tests/test_image_processing.py -v

# Run with coverage
pytest tests/test_image_processing.py --cov=utils.image_processing --cov-report=term-missing
```

**Step 3: Implement Minimal Code**

Create `utils/image_processing.py`:
```python
import cv2
import numpy as np

def detect_blur(image_path, threshold=100.0):
    """Detect if image is blurry using Laplacian variance."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()

    return {
        'is_blurry': variance < threshold,
        'blur_score': variance,
        'threshold': threshold
    }
```

**Step 4: Run Tests Again (Should Pass)**
```bash
pytest tests/test_image_processing.py -v
```

**Step 5: Refactor (Keep Tests Passing)**
```bash
# Make improvements while ensuring tests still pass
pytest tests/test_image_processing.py -v
```

---

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```bash
# Test image processing utilities
pytest tests/test_utils.py::TestImageProcessing -v

# Test OCR extraction
pytest tests/test_utils.py::TestOCRExtraction -v

# Test database models
pytest tests/test_models.py::TestImageSubmission -v
pytest tests/test_models.py::TestExtractedContent -v
```

### Integration Tests

Test component interactions:

```bash
# Test image upload → storage → database
pytest tests/test_routes.py::TestImageUpload -v

# Test Celery task processing
pytest tests/test_tasks.py::TestOCRProcessing -v

# Test API endpoints
pytest tests/test_api.py::TestImageGradingAPI -v
```

### Contract Tests

Test external service integrations:

```bash
# Test Azure Vision API integration
pytest tests/test_llm_providers.py::TestAzureVisionOCR -v

# Test Gemini Vision API integration
pytest tests/test_llm_providers.py::TestGeminiVision -v
```

### Test Fixtures

Create reusable test data:

```python
# tests/conftest.py
import pytest
from PIL import Image
import io

@pytest.fixture
def test_image_png():
    """Create a test PNG image"""
    img = Image.new('RGB', (1024, 768), color='white')
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

@pytest.fixture
def blurry_test_image(tmp_path):
    """Create a blurry test image"""
    img = Image.new('RGB', (800, 600), color='gray')
    # Apply blur filter
    img = img.filter(ImageFilter.GaussianBlur(radius=10))
    path = tmp_path / "blurry.png"
    img.save(path)
    return str(path)
```

### Running All Tests

```bash
# Run all tests for feature
pytest tests/test_image_*.py tests/test_ocr_*.py -v

# Run with coverage report
pytest --cov=utils.image_processing \
       --cov=models \
       --cov=routes \
       --cov-report=html \
       --cov-report=term-missing

# View coverage report
open htmlcov/index.html
```

---

## API Testing

### Using curl

**Upload Image**:
```bash
curl -X POST http://localhost:5000/api/submissions/{submission_id}/images \
  -F "image=@test_screenshot.png" \
  -F "description=Terminal output screenshot" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Get OCR Results**:
```bash
curl -X GET http://localhost:5000/api/images/{image_id}/ocr \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Get Quality Metrics**:
```bash
curl -X GET http://localhost:5000/api/images/{image_id}/quality \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Validate Against Criteria**:
```bash
curl -X POST http://localhost:5000/api/images/{image_id}/validate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "criteria_ids": ["criteria-uuid-1", "criteria-uuid-2"]
  }'
```

### Using Postman/Insomnia

1. Import OpenAPI spec from `contracts/image-grading-api.yaml`
2. Configure environment variables (base URL, JWT token)
3. Test all endpoints systematically

---

## Debugging

### Enable Debug Logging

```python
# Add to app.py or relevant module
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### Celery Task Debugging

```bash
# Run Celery worker with increased verbosity
celery -A tasks worker --loglevel=debug

# Inspect active tasks
celery -A tasks inspect active

# Check registered tasks
celery -A tasks inspect registered

# Purge all tasks from queue
celery -A tasks purge
```

### Database Debugging

```bash
# Connect to PostgreSQL
psql -U admin -d grading_platform

# View image submissions
SELECT id, original_filename, processing_status, created_at
FROM image_submissions
ORDER BY created_at DESC
LIMIT 10;

# View OCR results
SELECT is.original_filename, ec.extracted_text, ec.confidence_score
FROM image_submissions is
JOIN extracted_content ec ON is.id = ec.image_submission_id
WHERE ec.confidence_score < 0.9;

# View quality issues
SELECT is.original_filename, iq.overall_quality, iq.issues
FROM image_submissions is
JOIN image_quality_metrics iq ON is.id = iq.image_submission_id
WHERE iq.passes_quality_check = false;
```

### File System Debugging

```bash
# Check uploads directory structure
tree uploads/ | head -20

# Find images by UUID
find uploads/ -name "*{partial-uuid}*"

# Check disk usage
du -sh uploads/
du -sh uploads/*/* | sort -h | tail -20
```

---

## Performance Testing

### Load Testing with Locust

Create `locustfile.py`:
```python
from locust import HttpUser, task, between
import io
from PIL import Image

class ImageUploadUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login and get JWT token
        response = self.client.post("/api/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        self.token = response.json()["token"]

    @task
    def upload_image(self):
        # Create test image
        img = Image.new('RGB', (1024, 768), color='white')
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        # Upload image
        self.client.post(
            "/api/submissions/test-sub-id/images",
            files={"image": ("test.png", img_io, "image/png")},
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

Run load test:
```bash
# Install locust
pip install locust

# Run with 100 users, spawn rate of 10 users/second
locust -f locustfile.py --host=http://localhost:5000 --users=100 --spawn-rate=10
```

---

## Code Quality

### Linting

```bash
# Run flake8
flake8 utils/image_processing.py routes/api.py

# Run black formatter
black utils/image_processing.py routes/api.py --check

# Apply black formatting
black utils/image_processing.py routes/api.py

# Run isort (import sorting)
isort utils/image_processing.py routes/api.py --check-only
```

### Type Checking (Optional)

```bash
# Install mypy
pip install mypy

# Run type checker
mypy utils/image_processing.py --strict
```

---

## Troubleshooting

### Common Issues

**Issue**: `FileNotFoundError: [Errno 2] No such file or directory: '/app/uploads/...'`
**Solution**: Ensure upload directory exists and has correct permissions
```bash
mkdir -p /app/uploads
chmod 755 /app/uploads
```

**Issue**: `ImportError: cannot import name 'ComputerVisionClient'`
**Solution**: Install Azure Computer Vision SDK
```bash
pip install azure-cognitiveservices-vision-computervision msrest
```

**Issue**: `cv2.error: OpenCV(4.x) error: (-215:Assertion failed)`
**Solution**: Ensure image file exists and is valid
```python
if not os.path.exists(image_path):
    raise FileNotFoundError(f"Image not found: {image_path}")
```

**Issue**: Celery tasks not processing
**Solution**: Check Redis connection and Celery worker status
```bash
redis-cli ping  # Should return PONG
celery -A tasks inspect active
```

**Issue**: `ERROR: Could not build wheels for opencv-python-headless`
**Solution**: Install system dependencies
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev libopencv-dev

# macOS
brew install opencv
```

---

## Next Steps

1. **Complete Implementation**: Follow TDD workflow for all features
2. **Integration Testing**: Test complete upload → OCR → validation flow
3. **Performance Optimization**: Profile and optimize slow operations
4. **Documentation**: Update API docs with real examples
5. **Deployment**: Prepare production deployment with migrations

---

## Resources

- [OpenCV Documentation](https://docs.opencv.org/4.x/)
- [Azure Computer Vision API Reference](https://learn.microsoft.com/en-us/azure/cognitive-services/computer-vision/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/)
- [pytest Documentation](https://docs.pytest.org/)

---

## Support

For questions or issues:
1. Check existing tests in `tests/` directory
2. Review API contract in `contracts/image-grading-api.yaml`
3. Consult research findings in `research.md`
4. Review data model in `data-model.md`
