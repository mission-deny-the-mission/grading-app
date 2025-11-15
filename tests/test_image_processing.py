"""
Integration tests for image upload and OCR processing.
Tests the complete workflow: upload → queue → process → extract text.
"""

import io
import os
import time
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from models import ExtractedContent, ImageQualityMetrics, ImageSubmission, Submission, db
from utils.image_processing import detect_blur, check_resolution, check_completeness, ScreenshotQualityChecker


class TestImageUploadAndOCR:
    """Integration tests for complete image processing workflow."""

    def create_test_image_with_text(self, text="Hello World", width=800, height=200):
        """Create a test PNG image with text rendered on it."""
        # Create white background
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        # Draw text (use default font)
        try:
            # Try to use a larger font if available
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except Exception:
            # Fallback to default font
            font = ImageFont.load_default()

        # Calculate text position (centered)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((width - text_width) // 2, (height - text_height) // 2)

        # Draw black text
        draw.text(position, text, fill="black", font=font)

        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        return img_bytes

    def test_upload_png_creates_image_submission(self, client, app):
        """Test: Upload PNG with text → verify ImageSubmission created."""
        with app.app_context():
            # Create a test submission
            from models import GradingJob

            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Test grading prompt",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                filename="test.txt", original_filename="test.txt",
            )
            db.session.add(submission)
            db.session.commit()
            submission_id = submission.id

        # Create test image
        test_image = self.create_test_image_with_text("Test Document")
        test_image.name = "test_screenshot.png"

        # Upload image
        response = client.post(
            f"/api/submissions/{submission_id}/images",
            data={"image": (test_image, "test_screenshot.png")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "image" in data

        # Verify ImageSubmission created in database
        with app.app_context():
            image_submission = ImageSubmission.query.filter_by(
                submission_id=submission_id
            ).first()
            assert image_submission is not None
            assert image_submission.original_filename == "test_screenshot.png"
            assert image_submission.mime_type == "image/png"
            assert image_submission.processing_status == "queued"
            assert image_submission.file_size_bytes > 0
            assert os.path.exists(image_submission.storage_path)

            # Cleanup
            try:
                os.remove(image_submission.storage_path)
            except Exception:
                pass

    @patch("tasks.extract_text_from_image_azure")
    def test_ocr_processing_creates_extracted_content(
        self, mock_azure_ocr, client, app
    ):
        """Test: Wait for OCR completion → verify ExtractedContent exists."""
        # Mock Azure OCR response
        mock_azure_ocr.return_value = {
            "status": "success",
            "text": "Test Document\nThis is a test image",
            "confidence": 0.95,
            "text_regions": [
                {
                    "text": "Test Document",
                    "confidence": 0.96,
                    "bounding_box": [100, 50, 300, 80],
                }
            ],
            "processing_time_ms": 1500,
        }

        with app.app_context():
            # Create test submission and image
            from models import GradingJob

            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Test grading prompt",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                filename="test.txt", original_filename="test.txt",
            )
            db.session.add(submission)
            db.session.commit()

        # Upload image
        test_image = self.create_test_image_with_text("Test Document")
        response = client.post(
            f"/api/submissions/{submission.id}/images",
            data={"image": (test_image, "test_ocr.png")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 201
        image_data = response.get_json()["image"]
        image_id = image_data["id"]

        # Manually trigger OCR processing (instead of waiting for Celery)
        with app.app_context():
            from tasks import process_image_ocr

            # Run the task synchronously
            process_image_ocr(image_id)

            # Verify ExtractedContent was created
            extracted = ExtractedContent.query.filter_by(
                image_submission_id=image_id
            ).first()
            assert extracted is not None
            assert extracted.extracted_text == "Test Document\nThis is a test image"
            assert float(extracted.confidence_score) == 0.95

            # Verify ImageSubmission status updated
            image_submission = ImageSubmission.query.get(image_id)
            assert image_submission.processing_status == "completed"
            assert image_submission.ocr_completed_at is not None

            # Cleanup
            try:
                os.remove(image_submission.storage_path)
            except Exception:
                pass

    @patch("tasks.extract_text_from_image_azure")
    def test_extracted_text_matches_expected_content(
        self, mock_azure_ocr, client, app
    ):
        """Test: Verify extracted text matches expected content."""
        expected_text = "Hello World\nThis is a test"

        mock_azure_ocr.return_value = {
            "status": "success",
            "text": expected_text,
            "confidence": 0.92,
            "text_regions": [],
            "processing_time_ms": 1200,
        }

        with app.app_context():
            # Create test submission
            from models import GradingJob

            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Test grading prompt",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                filename="test.txt", original_filename="test.txt",
            )
            db.session.add(submission)
            db.session.commit()
            submission_id = submission.id

        # Upload and process
        test_image = self.create_test_image_with_text("Hello World")
        response = client.post(
            f"/api/submissions/{submission_id}/images",
            data={"image": (test_image, "test.png")},
            content_type="multipart/form-data",
        )

        image_id = response.get_json()["image"]["id"]

        with app.app_context():
            from tasks import process_image_ocr

            process_image_ocr(image_id)

            # Get OCR results via API
            ocr_response = client.get(f"/api/images/{image_id}/ocr")
            assert ocr_response.status_code == 200

            ocr_data = ocr_response.get_json()
            assert ocr_data["success"] is True
            assert ocr_data["status"] == "completed"
            assert ocr_data["content"]["extracted_text"] == expected_text

            # Cleanup
            image_submission = ImageSubmission.query.get(image_id)
            try:
                os.remove(image_submission.storage_path)
            except Exception:
                pass

    @patch("tasks.extract_text_from_image_azure")
    def test_confidence_score_meets_threshold(self, mock_azure_ocr, client, app):
        """Test: Verify confidence score ≥ 0.9 for clear image."""
        # Mock high-confidence OCR result
        mock_azure_ocr.return_value = {
            "status": "success",
            "text": "Clear Text Document",
            "confidence": 0.97,  # High confidence for clear image
            "text_regions": [
                {"text": "Clear Text Document", "confidence": 0.97, "bounding_box": []}
            ],
            "processing_time_ms": 1000,
        }

        with app.app_context():
            # Create test submission
            from models import GradingJob

            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Test grading prompt",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                filename="test.txt", original_filename="test.txt",
            )
            db.session.add(submission)
            db.session.commit()
            submission_id = submission.id

        # Upload clear image
        test_image = self.create_test_image_with_text("Clear Text Document")
        response = client.post(
            f"/api/submissions/{submission_id}/images",
            data={"image": (test_image, "clear_image.png")},
            content_type="multipart/form-data",
        )

        image_id = response.get_json()["image"]["id"]

        with app.app_context():
            from tasks import process_image_ocr

            process_image_ocr(image_id)

            # Verify confidence score
            extracted = ExtractedContent.query.filter_by(
                image_submission_id=image_id
            ).first()
            assert extracted is not None
            confidence = float(extracted.confidence_score)
            assert confidence >= 0.9, f"Confidence {confidence} below 0.9 threshold"
            assert confidence == 0.97

            # Cleanup
            image_submission = ImageSubmission.query.get(image_id)
            try:
                os.remove(image_submission.storage_path)
            except Exception:
                pass

    def test_ocr_status_progression(self, client, app):
        """Test OCR status progression: uploaded → queued → processing → completed."""
        with app.app_context():
            # Create test submission
            from models import GradingJob

            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Test grading prompt",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                filename="test.txt", original_filename="test.txt",
            )
            db.session.add(submission)
            db.session.commit()
            submission_id = submission.id

        # Upload image
        test_image = self.create_test_image_with_text("Status Test")
        response = client.post(
            f"/api/submissions/{submission_id}/images",
            data={"image": (test_image, "status_test.png")},
            content_type="multipart/form-data",
        )

        image_id = response.get_json()["image"]["id"]

        # Check initial status (should be queued)
        with app.app_context():
            image = ImageSubmission.query.get(image_id)
            assert image.processing_status == "queued"

            # Simulate processing
            image.processing_status = "processing"
            db.session.commit()

            image = ImageSubmission.query.get(image_id)
            assert image.processing_status == "processing"

            # Simulate completion
            image.processing_status = "completed"
            db.session.commit()

            image = ImageSubmission.query.get(image_id)
            assert image.processing_status == "completed"

            # Cleanup
            try:
                os.remove(image.storage_path)
            except Exception:
                pass


class TestBlurDetection:
    """Unit tests for blur detection functionality."""

    def create_sharp_image(self, width=800, height=600):
        """Create a sharp test image with clear text and edges."""
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        # Draw clear black text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except Exception:
            font = ImageFont.load_default()

        draw.text((50, 50), "Sharp Text Example", fill="black", font=font)

        # Draw some shapes for edge detection
        draw.rectangle([200, 200, 400, 400], outline="black", width=3)
        draw.line([(100, 500), (700, 500)], fill="black", width=2)

        return img

    def create_blurry_image(self, width=800, height=600):
        """Create a blurry test image."""
        # Start with a sharp image
        img = self.create_sharp_image(width, height)

        # Apply Gaussian blur to make it blurry
        img = img.filter(ImageFilter.GaussianBlur(radius=10))

        return img

    def test_sharp_image_has_high_blur_score(self, tmp_path):
        """Test: Sharp image has blur_score > 100."""
        # Create and save sharp image
        sharp_img = self.create_sharp_image()
        sharp_path = tmp_path / "sharp_test.png"
        sharp_img.save(sharp_path)

        # Test blur detection
        result = detect_blur(str(sharp_path))

        assert result['blur_score'] > 100, f"Sharp image blur score {result['blur_score']} should be > 100"
        assert result['is_blurry'] is False
        assert result['threshold'] == 100.0

    def test_blurry_image_has_low_blur_score(self, tmp_path):
        """Test: Blurry image has blur_score < 100."""
        # Create and save blurry image
        blurry_img = self.create_blurry_image()
        blurry_path = tmp_path / "blurry_test.png"
        blurry_img.save(blurry_path)

        # Test blur detection
        result = detect_blur(str(blurry_path))

        assert result['blur_score'] < 100, f"Blurry image blur score {result['blur_score']} should be < 100"
        assert result['is_blurry'] is True
        assert result['threshold'] == 100.0

    def test_blur_detection_returns_correct_structure(self, tmp_path):
        """Test: Blur detection returns correct dictionary structure."""
        sharp_img = self.create_sharp_image()
        test_path = tmp_path / "structure_test.png"
        sharp_img.save(test_path)

        result = detect_blur(str(test_path))

        # Check all required keys are present
        assert 'is_blurry' in result
        assert 'blur_score' in result
        assert 'threshold' in result

        # Check types
        assert isinstance(result['is_blurry'], bool)
        assert isinstance(result['blur_score'], (int, float))
        assert isinstance(result['threshold'], (int, float))

    def test_resolution_check_detects_low_resolution(self, tmp_path):
        """Test: Low-resolution image fails meets_minimum check."""
        # Create small image (below 800x600 minimum)
        small_img = Image.new("RGB", (640, 480), color="white")
        small_path = tmp_path / "small.png"
        small_img.save(small_path)

        result = check_resolution(str(small_path), min_width=800, min_height=600)

        assert result['width'] == 640
        assert result['height'] == 480
        assert result['meets_minimum'] is False
        assert result['is_valid'] is False

    def test_resolution_check_accepts_high_resolution(self, tmp_path):
        """Test: High-resolution image passes meets_minimum check."""
        # Create large image (above 800x600 minimum)
        large_img = Image.new("RGB", (1920, 1080), color="white")
        large_path = tmp_path / "large.png"
        large_img.save(large_path)

        result = check_resolution(str(large_path), min_width=800, min_height=600)

        assert result['width'] == 1920
        assert result['height'] == 1080
        assert result['meets_minimum'] is True
        assert result['is_valid'] is True


class TestQualityAssessmentFlow:
    """Integration tests for complete quality assessment workflow."""

    def create_test_image(self, quality="sharp", width=800, height=600):
        """Create test images with different quality levels."""
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except Exception:
            font = ImageFont.load_default()

        draw.text((50, 50), "Test Image", fill="black", font=font)
        draw.rectangle([100, 100, 300, 300], outline="black", width=2)

        if quality == "blurry":
            img = img.filter(ImageFilter.GaussianBlur(radius=10))

        return img

    @patch("tasks.assess_image_quality.delay")
    @patch("tasks.extract_text_from_image_azure")
    def test_quality_assessment_triggered_after_ocr(
        self, mock_azure_ocr, mock_quality_task, client, app
    ):
        """Test: Quality assessment task is queued after OCR completes."""
        mock_azure_ocr.return_value = {
            "status": "success",
            "text": "Test Image",
            "confidence": 0.95,
            "text_regions": [],
            "processing_time_ms": 1000,
        }

        with app.app_context():
            # Create test submission
            from models import GradingJob

            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Test grading prompt",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                filename="test.txt", original_filename="test.txt",
            )
            db.session.add(submission)
            db.session.commit()
            submission_id = submission.id

        # Upload image
        test_img = self.create_test_image()
        img_bytes = io.BytesIO()
        test_img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        response = client.post(
            f"/api/submissions/{submission_id}/images",
            data={"image": (img_bytes, "test.png")},
            content_type="multipart/form-data",
        )

        image_id = response.get_json()["image"]["id"]

        # Run OCR task
        with app.app_context():
            from tasks import process_image_ocr

            process_image_ocr(image_id)

            # Verify quality assessment was queued
            mock_quality_task.assert_called_once_with(image_id)

            # Cleanup
            image = ImageSubmission.query.get(image_id)
            try:
                os.remove(image.storage_path)
            except Exception:
                pass

    @patch("tasks.extract_text_from_image_azure")
    def test_blurry_image_quality_metrics_show_is_blurry_true(
        self, mock_azure_ocr, client, app
    ):
        """Test: Upload blurry image → quality metrics show is_blurry=true."""
        mock_azure_ocr.return_value = {
            "status": "success",
            "text": "Blurry Test",
            "confidence": 0.75,
            "text_regions": [],
            "processing_time_ms": 1000,
        }

        with app.app_context():
            # Create test submission
            from models import GradingJob

            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Test grading prompt",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                filename="test.txt", original_filename="test.txt",
            )
            db.session.add(submission)
            db.session.commit()
            submission_id = submission.id

        # Create and upload blurry image
        blurry_img = self.create_test_image(quality="blurry")
        img_bytes = io.BytesIO()
        blurry_img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        response = client.post(
            f"/api/submissions/{submission_id}/images",
            data={"image": (img_bytes, "blurry.png")},
            content_type="multipart/form-data",
        )

        image_id = response.get_json()["image"]["id"]

        # Run quality assessment
        with app.app_context():
            from tasks import assess_image_quality

            result = assess_image_quality(image_id)

            assert result['status'] == 'success'
            assert result['overall_quality'] in ['good', 'poor', 'rejected']

            # Check quality metrics in database
            quality_metrics = ImageQualityMetrics.query.filter_by(
                image_submission_id=image_id
            ).first()

            assert quality_metrics is not None
            assert quality_metrics.is_blurry is True
            assert float(quality_metrics.blur_score) < 100

            # Cleanup
            image = ImageSubmission.query.get(image_id)
            try:
                os.remove(image.storage_path)
            except Exception:
                pass
