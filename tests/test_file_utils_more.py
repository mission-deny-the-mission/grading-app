"""
Additional tests for utils.file_utils to increase branch coverage.
"""

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from utils import file_utils as fu


class TestDetermineAndAllow:
    """Test file type determination and file validation functionality."""

    def test_determine_file_type_all_extensions(self):
        """Test file type detection for all supported extensions."""
        assert fu.determine_file_type("report.DOCX") == "docx"
        assert fu.determine_file_type("paper.pdf") == "pdf"
        assert fu.determine_file_type("notes.TXT") == "txt"
        assert fu.determine_file_type("archive.zip") is None

    def test_is_allowed_file(self):
        """Test file type validation for allowed file types."""
        assert fu.is_allowed_file("a.txt") is True
        assert fu.is_allowed_file("a.docx") is True
        assert fu.is_allowed_file("a.pdf") is True
        assert fu.is_allowed_file("a.jpg") is False

    def test_determine_file_type_uppercase_extensions(self):
        """Test file type determination with uppercase extensions"""
        assert fu.determine_file_type("file.TXT") == "txt"
        assert fu.determine_file_type("file.DOCX") == "docx"
        assert fu.determine_file_type("file.PDF") == "pdf"

    def test_is_allowed_file_edge_cases(self):
        """Test allowed file validation with edge cases"""
        # Empty filename
        assert fu.is_allowed_file("") is False
        # No extension
        assert fu.is_allowed_file("file") is False
        # Dot file without extension
        assert fu.is_allowed_file(".hidden") is False
        # Multiple dots
        assert fu.is_allowed_file("file.name.txt") is True


class TestSecureAndCleanup:
    """Test filename security and file cleanup functionality."""

    def test_get_secure_filename(self):
        """Test filename sanitization to prevent path traversal."""
        # Includes spaces and path traversal characters
        result = fu.get_secure_filename("../../weird name.pdf")
        assert result.endswith("weird_name.pdf")

    def test_cleanup_file_when_exists(self):
        """Test successful file cleanup when file exists."""
        fd, path = tempfile.mkstemp()
        os.close(fd)
        assert os.path.exists(path)
        fu.cleanup_file(path)
        assert not os.path.exists(path)

    def test_cleanup_file_ignores_errors(self):
        """Test that cleanup handles errors gracefully."""
        # Simulate an exception in os.remove
        with patch("utils.file_utils.os.path.exists", return_value=True), patch(
            "utils.file_utils.os.remove", side_effect=OSError("boom")
        ):
            # Should not raise
            fu.cleanup_file("/tmp/fake")


class TestValidateFileUpload:
    """Test file upload validation functionality."""

    def test_validate_file_upload_no_file(self):
        """Test validation when no file is provided."""
        ok, err = fu.validate_file_upload(None)
        assert ok is False and "No file selected" in err

    def test_validate_file_upload_empty_filename(self):
        """Test validation when filename is empty."""
        fake = SimpleNamespace(filename="")
        ok, err = fu.validate_file_upload(fake)
        assert ok is False and "No file selected" in err

    def test_validate_file_upload_unsupported_type(self):
        """Test validation for unsupported file types."""
        fake = SimpleNamespace(filename="image.png")
        ok, err = fu.validate_file_upload(fake)
        assert ok is False and "Unsupported file type" in err

    def test_validate_file_upload_supported_type(self):
        """Test validation for supported file types."""
        fake = SimpleNamespace(filename="essay.pdf")
        ok, err = fu.validate_file_upload(fake)
        assert ok is True and err is None
