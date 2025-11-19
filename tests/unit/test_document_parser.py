"""
Unit Tests for Document Parser Service

Tests document parsing functionality for PDF, DOCX, and image files,
and LLM integration for converting rubrics to marking schemes.

Implements T060-T066 test requirements.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from services.document_parser import (
    DocumentParser,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_image,
    parse_llm_response,
    get_document_type,
)
from tests.unit.fixtures.sample_documents import (
    create_sample_pdf,
    create_sample_docx,
    create_sample_png,
    create_sample_jpg,
    create_sample_rubric_pdf,
    create_sample_rubric_docx,
    cleanup_temp_file,
)


class TestDocumentTypeDetection:
    """Test document type detection from file extensions and content."""

    def test_detect_pdf_from_extension(self):
        """Test detecting PDF from .pdf extension."""
        file_path = create_sample_pdf()
        try:
            doc_type = get_document_type(file_path)
            assert doc_type == "pdf"
        finally:
            cleanup_temp_file(file_path)

    def test_detect_docx_from_extension(self):
        """Test detecting DOCX from .docx extension."""
        file_path = create_sample_docx()
        try:
            doc_type = get_document_type(file_path)
            assert doc_type == "docx"
        finally:
            cleanup_temp_file(file_path)

    def test_detect_png_from_extension(self):
        """Test detecting PNG from .png extension."""
        file_path = create_sample_png()
        try:
            doc_type = get_document_type(file_path)
            assert doc_type == "image"
        finally:
            cleanup_temp_file(file_path)

    def test_detect_jpg_from_extension(self):
        """Test detecting JPG from .jpg extension."""
        file_path = create_sample_jpg()
        try:
            doc_type = get_document_type(file_path)
            assert doc_type == "image"
        finally:
            cleanup_temp_file(file_path)

    def test_unsupported_file_type_raises_error(self):
        """Test that unsupported file types raise ValueError."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.xyz', delete=False)
        temp_file.write(b'unsupported file type')
        temp_file.close()

        try:
            with pytest.raises(ValueError) as exc_info:
                get_document_type(temp_file.name)
            assert "unsupported" in str(exc_info.value).lower()
        finally:
            cleanup_temp_file(temp_file.name)


class TestPDFExtraction:
    """Test PDF text extraction functionality."""

    def test_extract_text_from_pdf_basic(self):
        """Test extracting text from a basic PDF file."""
        file_path = create_sample_pdf("Test PDF Content\n\nMultiple lines")
        try:
            text = extract_text_from_pdf(file_path)
            assert text is not None
            assert len(text) > 0
            # Should contain some recognizable text
            assert any(word in text.lower() for word in ['test', 'pdf', 'content', 'line'])
        finally:
            cleanup_temp_file(file_path)

    def test_extract_text_from_pdf_returns_string(self):
        """Test that PDF extraction returns a string."""
        file_path = create_sample_pdf()
        try:
            text = extract_text_from_pdf(file_path)
            assert isinstance(text, str)
        finally:
            cleanup_temp_file(file_path)

    def test_extract_text_from_pdf_rubric(self):
        """Test extracting text from a rubric PDF."""
        file_path = create_sample_rubric_pdf()
        try:
            text = extract_text_from_pdf(file_path)
            assert isinstance(text, str)
            # Should contain rubric-related keywords
            assert any(word in text.lower() for word in ['rubric', 'excellent', 'organization', 'grammar'])
        finally:
            cleanup_temp_file(file_path)

    def test_extract_text_from_nonexistent_pdf_raises_error(self):
        """Test that extracting from nonexistent file raises error."""
        with pytest.raises((FileNotFoundError, IOError)):
            extract_text_from_pdf("/nonexistent/file.pdf")

    def test_extract_text_from_corrupted_pdf_handles_gracefully(self):
        """Test that corrupted PDF is handled gracefully."""
        # Create a file with .pdf extension but invalid content
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_file.write(b'This is not a valid PDF')
        temp_file.close()

        try:
            # Should either return empty string or raise a handled exception
            result = extract_text_from_pdf(temp_file.name)
            assert isinstance(result, str)
        except Exception as e:
            # If it raises, should be a clear exception
            assert "corrupt" in str(e).lower() or "invalid" in str(e).lower()
        finally:
            cleanup_temp_file(temp_file.name)


class TestDOCXExtraction:
    """Test DOCX text extraction functionality."""

    def test_extract_text_from_docx_basic(self):
        """Test extracting text from a basic DOCX file."""
        file_path = create_sample_docx("Test DOCX Content\n\nMultiple paragraphs")
        try:
            text = extract_text_from_docx(file_path)
            assert text is not None
            assert isinstance(text, str)
            assert len(text) > 0
        finally:
            cleanup_temp_file(file_path)

    def test_extract_text_from_docx_returns_string(self):
        """Test that DOCX extraction returns a string."""
        file_path = create_sample_docx()
        try:
            text = extract_text_from_docx(file_path)
            assert isinstance(text, str)
        finally:
            cleanup_temp_file(file_path)

    def test_extract_text_from_docx_rubric(self):
        """Test extracting text from a rubric DOCX."""
        file_path = create_sample_rubric_docx()
        try:
            text = extract_text_from_docx(file_path)
            assert isinstance(text, str)
            # Should contain rubric-related keywords
            assert any(word in text.lower() for word in ['rubric', 'analysis', 'design', 'excellent'])
        finally:
            cleanup_temp_file(file_path)

    def test_extract_text_from_nonexistent_docx_raises_error(self):
        """Test that extracting from nonexistent file raises error."""
        with pytest.raises((FileNotFoundError, IOError)):
            extract_text_from_docx("/nonexistent/file.docx")

    def test_extract_text_from_invalid_docx_handles_gracefully(self):
        """Test that invalid DOCX is handled gracefully."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_file.write(b'Not a valid DOCX file')
        temp_file.close()

        try:
            # Should either return empty string or raise a handled exception
            result = extract_text_from_docx(temp_file.name)
            assert isinstance(result, str)
        except Exception as e:
            # If it raises, should be a clear exception
            assert any(word in str(e).lower() for word in ['invalid', 'corrupt', 'docx'])
        finally:
            cleanup_temp_file(temp_file.name)


class TestImageExtraction:
    """Test image text extraction (OCR) functionality."""

    def test_extract_text_from_png_returns_string(self):
        """Test that PNG extraction returns a string (even if empty)."""
        file_path = create_sample_png()
        try:
            text = extract_text_from_image(file_path)
            assert isinstance(text, str)
            # For a blank image, text might be empty, which is okay
        finally:
            cleanup_temp_file(file_path)

    def test_extract_text_from_jpg_returns_string(self):
        """Test that JPG extraction returns a string (even if empty)."""
        file_path = create_sample_jpg()
        try:
            text = extract_text_from_image(file_path)
            assert isinstance(text, str)
        finally:
            cleanup_temp_file(file_path)

    def test_extract_text_from_nonexistent_image_raises_error(self):
        """Test that extracting from nonexistent image raises error."""
        with pytest.raises((FileNotFoundError, IOError)):
            extract_text_from_image("/nonexistent/file.png")

    def test_extract_text_from_invalid_image_handles_gracefully(self):
        """Test that invalid image is handled gracefully."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_file.write(b'Not a valid image')
        temp_file.close()

        try:
            # Should either return empty string or raise a handled exception
            result = extract_text_from_image(temp_file.name)
            assert isinstance(result, str)
        except Exception as e:
            # If it raises, should be a clear exception
            assert any(word in str(e).lower() for word in ['image', 'invalid', 'corrupt'])
        finally:
            cleanup_temp_file(temp_file.name)

    def test_extract_text_from_unsupported_image_format_raises_error(self):
        """Test that unsupported image format raises error."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.bmp', delete=False)
        temp_file.write(b'BM')  # BMP header
        temp_file.close()

        try:
            with pytest.raises((ValueError, IOError)):
                extract_text_from_image(temp_file.name)
        finally:
            cleanup_temp_file(temp_file.name)


class TestLLMResponseParsing:
    """Test LLM response parsing for marking scheme extraction."""

    def test_parse_llm_json_response(self):
        """Test parsing LLM response in JSON format."""
        llm_response = json.dumps({
            "extracted_scheme": {
                "name": "Test Rubric",
                "metadata": {
                    "name": "Test Rubric",
                    "description": "Extracted from document"
                },
                "criteria": [
                    {
                        "name": "Organization",
                        "description": "Structure and flow",
                        "weight": 0.3,
                        "descriptors": [
                            {
                                "level": "excellent",
                                "description": "Clear and logical structure"
                            },
                            {
                                "level": "good",
                                "description": "Mostly clear structure"
                            }
                        ]
                    }
                ],
                "version": "1.0.0"
            },
            "uncertainty_flags": []
        })

        result = parse_llm_response(llm_response)
        assert "extracted_scheme" in result
        assert result["extracted_scheme"]["name"] == "Test Rubric"
        assert len(result["extracted_scheme"]["criteria"]) == 1
        assert "uncertainty_flags" in result

    def test_parse_llm_response_with_uncertainty_flags(self):
        """Test parsing LLM response with uncertainty flags."""
        llm_response = json.dumps({
            "extracted_scheme": {
                "name": "Test Rubric",
                "metadata": {"name": "Test Rubric"},
                "criteria": [
                    {
                        "name": "Criterion 1",
                        "descriptors": [
                            {"level": "excellent", "description": "Good"}
                        ]
                    }
                ],
                "version": "1.0.0"
            },
            "uncertainty_flags": [
                {
                    "field": "criteria[0].weight",
                    "confidence": 0.4,
                    "reason": "Not explicitly stated in rubric"
                },
                {
                    "field": "criteria[0].point_value",
                    "confidence": 0.5,
                    "reason": "Ambiguous point allocation"
                }
            ]
        })

        result = parse_llm_response(llm_response)
        assert len(result["uncertainty_flags"]) == 2
        assert result["uncertainty_flags"][0]["field"] == "criteria[0].weight"
        assert result["uncertainty_flags"][0]["confidence"] == 0.4

    def test_parse_llm_free_text_response(self):
        """Test parsing LLM response in free text format."""
        llm_response = """
        The rubric includes the following criteria:

        1. Organization (20 points)
           - Excellent: Clear introduction and conclusion
           - Good: Adequate structure
           - Poor: Unclear structure

        2. Grammar (15 points)
           - Excellent: Few errors
           - Good: Some errors
        """

        # This should attempt to extract structure from free text
        result = parse_llm_response(llm_response)
        assert "extracted_scheme" in result
        # The extraction might be partial for free text, but should be present
        assert isinstance(result.get("uncertainty_flags"), list)

    def test_parse_invalid_json_response_handles_gracefully(self):
        """Test that invalid JSON is handled gracefully."""
        invalid_response = "This is not valid JSON {broken"

        result = parse_llm_response(invalid_response)
        # Should return a result even if parsing failed
        assert "extracted_scheme" in result or "error" in result
        assert isinstance(result.get("uncertainty_flags", []), list)

    def test_parse_empty_response_returns_defaults(self):
        """Test that empty response returns default structure."""
        result = parse_llm_response("")
        assert "extracted_scheme" in result or "error" in result
        assert isinstance(result.get("uncertainty_flags", []), list)

    def test_parse_response_with_confidence_scores(self):
        """Test parsing response with confidence scores for fields."""
        llm_response = json.dumps({
            "extracted_scheme": {
                "name": "Test Rubric",
                "metadata": {"name": "Test Rubric"},
                "criteria": [
                    {
                        "name": "Quality",
                        "weight": 0.5,
                        "point_value": 50,
                        "descriptors": [
                            {"level": "excellent", "description": "Excellent work"}
                        ]
                    }
                ],
                "version": "1.0.0"
            },
            "confidence_scores": {
                "criteria[0].weight": 0.95,
                "criteria[0].point_value": 0.8
            },
            "uncertainty_flags": [
                {
                    "field": "criteria[0].point_value",
                    "confidence": 0.8,
                    "reason": "Inferred from context"
                }
            ]
        })

        result = parse_llm_response(llm_response)
        assert len(result["uncertainty_flags"]) >= 1
        # Low confidence field should be flagged
        flagged_fields = [f["field"] for f in result["uncertainty_flags"]]
        assert "criteria[0].point_value" in flagged_fields


class TestDocumentParser:
    """Test the DocumentParser service class."""

    def test_document_parser_initialization(self):
        """Test DocumentParser can be initialized."""
        parser = DocumentParser()
        assert parser is not None

    def test_parse_document_returns_dict(self):
        """Test that parse_document returns a dictionary."""
        parser = DocumentParser()
        file_path = create_sample_pdf("Test content")

        try:
            result = parser.parse_document(file_path)
            assert isinstance(result, dict)
            assert "extracted_text" in result
        finally:
            cleanup_temp_file(file_path)

    def test_parse_pdf_document(self):
        """Test parsing a PDF document."""
        parser = DocumentParser()
        file_path = create_sample_rubric_pdf()

        try:
            result = parser.parse_document(file_path)
            assert "extracted_text" in result
            assert isinstance(result["extracted_text"], str)
            assert result["document_type"] == "pdf"
        finally:
            cleanup_temp_file(file_path)

    def test_parse_docx_document(self):
        """Test parsing a DOCX document."""
        parser = DocumentParser()
        file_path = create_sample_rubric_docx()

        try:
            result = parser.parse_document(file_path)
            assert "extracted_text" in result
            assert isinstance(result["extracted_text"], str)
            assert result["document_type"] == "docx"
        finally:
            cleanup_temp_file(file_path)

    def test_parse_image_document(self):
        """Test parsing an image document."""
        parser = DocumentParser()
        file_path = create_sample_png()

        try:
            result = parser.parse_document(file_path)
            assert "extracted_text" in result
            assert isinstance(result["extracted_text"], str)
            assert result["document_type"] == "image"
        finally:
            cleanup_temp_file(file_path)

    def test_convert_document_to_scheme_calls_llm(self):
        """Test that convert_document_to_scheme returns extracted scheme and flags."""
        # Create a mock provider
        mock_provider = MagicMock()
        mock_provider.grade_document.return_value = {
            "success": True,
            "grade": json.dumps({
                "extracted_scheme": {
                    "name": "Generated Rubric",
                    "metadata": {"name": "Generated Rubric"},
                    "criteria": [],
                    "version": "1.0.0"
                },
                "uncertainty_flags": []
            })
        }

        parser = DocumentParser()
        file_path = create_sample_pdf("Test rubric text")

        try:
            # Test with provided provider (avoids need to mock get_llm_provider)
            result = parser.convert_document_to_scheme(file_path, provider=mock_provider)
            assert "extracted_scheme" in result
            assert isinstance(result["extracted_scheme"], dict)
            # Verify provider was called
            assert mock_provider.grade_document.called
        finally:
            cleanup_temp_file(file_path)

    @patch('services.document_parser.get_llm_provider')
    def test_convert_with_uncertainty_flags(self, mock_get_provider):
        """Test conversion result includes uncertainty flags."""
        mock_provider = MagicMock()
        mock_provider.grade_document.return_value = {
            "success": True,
            "grade": json.dumps({
                "extracted_scheme": {
                    "name": "Test",
                    "metadata": {"name": "Test"},
                    "criteria": [{"name": "C1", "descriptors": []}],
                    "version": "1.0.0"
                },
                "uncertainty_flags": [
                    {"field": "criteria[0].weight", "confidence": 0.3}
                ]
            })
        }
        mock_get_provider.return_value = mock_provider

        parser = DocumentParser()
        file_path = create_sample_pdf()

        try:
            result = parser.convert_document_to_scheme(file_path)
            assert len(result["uncertainty_flags"]) > 0
        finally:
            cleanup_temp_file(file_path)
