# Integration Tests for OCR Image Grading Feature

## Overview

I've created comprehensive integration tests for the OCR image grading feature in `/home/harry/grading-app/tests/test_integration_image_grading.py`.

## Tests Covered

### Phase 3 (US1) - Image Upload and OCR Flow

**Test Class**: `TestImageUploadAndOCRIntegration`

1. **test_complete_upload_and_ocr_flow** - Complete end-to-end test
   - Upload PNG with text → verify ImageSubmission created
   - Trigger OCR processing
   - Verify ExtractedContent exists
   - Verify text matches expected content
   - Verify confidence score ≥ 0.9 for clear images

2. **test_multiple_images_in_single_submission** - Multi-image handling
   - Tests that multiple images in a single submission are all processed
   - Verifies all images get OCR'd successfully

3. **test_ocr_processing_time_within_threshold** - Performance test
   - Verifies OCR processing completes within 30 seconds
   - Measures actual processing time

### Phase 4 (US2) - Quality Assessment Flow

**Test Class**: `TestQualityAssessmentIntegration`

1. **test_blurry_image_quality_assessment**
   - Upload blurry image → quality metrics show `is_blurry=true`
   - Verifies blur detection algorithm works
   - Checks that quality flags are set correctly

2. **test_low_resolution_image_quality_assessment**
   - Upload low-res image (640x480) → quality metrics show `meets_min_resolution=false`
   - Verifies resolution checking against 800x600 minimum

3. **test_cropped_image_completeness_detection**
   - Upload cropped image → quality metrics show `likely_cropped=true`
   - Tests edge density detection for incomplete screenshots

4. **test_high_quality_image_passes_all_checks**
   - Verifies high-quality images (sharp, good resolution) pass all checks
   - Ensures `passes_quality_check=True` for good images

5. **test_quality_indicators_displayed_for_each_image**
   - Tests that quality indicators are available via API for each image
   - Verifies `/api/images/<id>/quality` endpoint returns complete metrics

## Coverage Mapping to tasks.md

### T027 - Upload and OCR Flow
✅ Test: Upload PNG with text → verify ImageSubmission created
✅ Test: Wait for OCR completion → verify ExtractedContent exists
✅ Test: Verify extracted text matches expected content
✅ Test: Verify confidence score ≥ 0.9 for clear image

### T038 - Quality Assessment Flow
✅ Test: Upload blurry image → quality metrics show is_blurry=true
✅ Test: Upload low-res image → quality metrics show meets_min_resolution=false
✅ Test: Upload cropped image → quality metrics show likely_cropped=true

## Fixed Issues

### Issue 1: Submission Model Field Names
**Problem**: Tests were using incorrect field names (`file_path`, `student_name`)
**Solution**: Updated to use correct fields (`filename`, `original_filename`, `file_type`)

### Issue 2: Upload Folder Configuration
**Problem**: `/routes/api.py` was using `os.getenv('UPLOAD_FOLDER')` which doesn't work in tests
**Error**: `[Errno 13] Permission denied: '/app'`
**Solution**: Changed to `current_app.config.get('UPLOAD_FOLDER')` to respect Flask app configuration

## Test Execution

Run all integration tests:
```bash
python -m pytest tests/test_integration_image_grading.py -v
```

Run specific test class:
```bash
python -m pytest tests/test_integration_image_grading.py::TestImageUploadAndOCRIntegration -v
python -m pytest tests/test_integration_image_grading.py::TestQualityAssessmentIntegration -v
```

## Current Status

- ✅ Test file created with all required tests
- ✅ Submission model fields corrected
- ✅ Upload folder configuration fixed
- ⚠️ Tests need minor adjustments for proper mocking in Celery task context
- ⚠️ Image upload working, OCR execution needs app context refinement

## Next Steps

1. **Adjust mock placement** for Celery task execution context
2. **Add transaction handling** to ensure test isolation
3. **Verify database cleanup** between tests
4. **Run full test suite** to ensure no regressions

## Test Structure

Each test follows this pattern:
1. **Setup**: Create test job and submission in database
2. **Upload**: POST image to `/api/submissions/<id>/images`
3. **Process**: Trigger OCR or quality assessment task
4. **Verify**: Check database records and API responses
5. **Cleanup**: Remove test files from filesystem

## Dependencies

Tests use:
- PIL (Pillow) for image generation
- pytest fixtures from `conftest.py`
- Mocked Azure Vision OCR (`utils.llm_providers.extract_text_from_image_azure`)
- Temporary file storage for image uploads
