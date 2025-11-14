"""
Integration tests for image upload and OCR processing.
Tests the complete workflow: upload → queue → process → extract text.
"""

import io
import os
import time
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw, ImageFont

from models import ExtractedContent, ImageSubmission, Submission


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
                model_name="test-model",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                file_path="/tmp/test.txt",
                student_name="Test Student",
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

    @patch("utils.llm_providers.extract_text_from_image_azure")
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
                model_name="test-model",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                file_path="/tmp/test.txt",
                student_name="Test Student",
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

    @patch("utils.llm_providers.extract_text_from_image_azure")
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
                model_name="test-model",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                file_path="/tmp/test.txt",
                student_name="Test Student",
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

    @patch("utils.llm_providers.extract_text_from_image_azure")
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
                model_name="test-model",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                file_path="/tmp/test.txt",
                student_name="Test Student",
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
                model_name="test-model",
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                file_path="/tmp/test.txt",
                student_name="Test Student",
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
