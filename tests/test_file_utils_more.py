"""
Additional tests for utils.file_utils to increase branch coverage.
"""

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

# Import PIL.ImageFile to avoid isinstance errors in Python 3.13
try:
    from PIL import ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except ImportError:
    pass

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


class TestImageValidation:
    """Test image-specific file validation functionality."""

    def create_mock_image_file(self, filename="test.png", mime_type="image/png", file_size=1024 * 100):
        """Create a mock file object for testing."""
        import io

        from PIL import Image

        # Create a real PNG image
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Create mock with required attributes
        mock_file = SimpleNamespace(
            filename=filename,
            content_type=mime_type,
            tell=lambda: file_size,
            seek=lambda *args: None,
            read=lambda: img_bytes.getvalue(),
        )

        # Make it work with PIL Image.open
        mock_file._bytes = img_bytes.getvalue()

        return mock_file, img_bytes

    def test_valid_png_passes_validation(self):
        """Test: Valid PNG passes validation."""
        import io

        from PIL import Image

        # Create a real PNG image
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Create file-like object
        class MockFile:
            def __init__(self, data):
                self._data = data
                self.filename = "test.png"
                self.content_type = "image/png"
                # Get the size
                data.seek(0, 2)  # Seek to end
                self._size = data.tell()
                data.seek(0)  # Reset to beginning

            def seek(self, pos, whence=0):
                if whence == 2:  # SEEK_END
                    self._data.seek(0, 2)
                else:
                    self._data.seek(pos, whence)

            def tell(self):
                return self._data.tell()

            def read(self, size=-1):
                return self._data.read(size)

        mock_file = MockFile(img_bytes)

        # Should not raise ValidationError
        result = fu.validate_uploaded_image(mock_file)
        assert result is True

    def test_invalid_extension_rejected(self):
        """Test: Invalid extension rejected."""

        class MockFile:
            filename = "test.exe"
            content_type = "application/x-executable"

        with patch("utils.file_utils.os.SEEK_END", 2):
            try:
                fu.validate_uploaded_image(MockFile())
                assert False, "Should have raised ValidationError"
            except fu.ValidationError as e:
                assert "Invalid file extension" in str(e)

    def test_file_over_50mb_rejected(self):
        """Test: File > 50MB rejected."""
        import io

        from PIL import Image

        # Create a valid image but mock size > 50MB
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        class MockFile:
            def __init__(self):
                self.filename = "large.png"
                self.content_type = "image/png"
                self._data = img_bytes
                self._size = 52428801  # 50MB + 1 byte

            def seek(self, pos, whence=0):
                if whence == 2:  # SEEK_END
                    return self._size
                self._data.seek(pos, whence)

            def tell(self):
                return self._size

            def read(self, size=-1):
                return self._data.read(size)

        with patch("utils.file_utils.os.SEEK_END", 2):
            try:
                fu.validate_uploaded_image(MockFile())
                assert False, "Should have raised ValidationError"
            except fu.ValidationError as e:
                assert "File too large" in str(e)
                assert "50MB" in str(e)

    def test_non_image_mime_type_rejected(self):
        """Test: Non-image MIME type rejected."""

        class MockFile:
            filename = "document.png"
            content_type = "application/pdf"

        with patch("utils.file_utils.os.SEEK_END", 2):
            try:
                fu.validate_uploaded_image(MockFile())
                assert False, "Should have raised ValidationError"
            except fu.ValidationError as e:
                assert "Invalid MIME type" in str(e)
                assert "application/pdf" in str(e)

    def test_corrupted_image_data_rejected(self):
        """Test: Corrupted image data rejected."""
        import io

        # Create corrupted image data (not a valid image)
        corrupted_data = io.BytesIO(b"This is not an image file")

        class MockFile:
            def __init__(self):
                self.filename = "corrupted.png"
                self.content_type = "image/png"
                self._data = corrupted_data

            def seek(self, pos, whence=0):
                self._data.seek(pos, whence)

            def tell(self):
                return len(b"This is not an image file")

            def read(self, size=-1):
                return self._data.read(size)

        with patch("utils.file_utils.os.SEEK_END", 2):
            try:
                fu.validate_uploaded_image(MockFile())
                assert False, "Should have raised ValidationError"
            except fu.ValidationError as e:
                assert "Invalid image data" in str(e)

    def test_empty_file_rejected(self):
        """Test: Empty file is rejected."""

        class MockFile:
            filename = "empty.png"
            content_type = "image/png"

            def seek(self, pos, whence=0):
                pass

            def tell(self):
                return 0

        with patch("utils.file_utils.os.SEEK_END", 2):
            try:
                fu.validate_uploaded_image(MockFile())
                assert False, "Should have raised ValidationError"
            except fu.ValidationError as e:
                assert "File is empty" in str(e)

    def test_jpeg_format_accepted(self):
        """Test: JPEG format is accepted."""
        import io

        from PIL import Image

        # Create JPEG image
        img = Image.new("RGB", (50, 50), color="green")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=95)
        img_data = img_bytes.getvalue()

        class MockFile:
            def __init__(self):
                self.filename = "test.jpg"
                self.content_type = "image/jpeg"
                self._data = io.BytesIO(img_data)

            def seek(self, pos, whence=0):
                self._data.seek(pos, whence)

            def tell(self):
                return len(img_data)

            def read(self, size=-1):
                return self._data.read(size)

        with patch("utils.file_utils.os.SEEK_END", 2):
            result = fu.validate_uploaded_image(MockFile())
            assert result is True


class TestGenerateStoragePath:
    """Test UUID-based storage path generation."""

    def test_generates_two_level_hash_structure(self):
        """Test that storage path uses two-level hashing."""
        import re
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path, uuid = fu.generate_storage_path("png", tmpdir)

            # Should match pattern: tmpdir/XX/YY/uuid.png
            # Use flexible pattern that works with temp directories
            pattern = r".*/[A-F0-9]{2}/[A-F0-9]{2}/[a-f0-9-]+\.png"
            assert re.match(pattern, path), f"Path {path} doesn't match expected pattern"

    def test_uuid_is_valid_format(self):
        """Test that generated UUID is valid."""
        import re
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path, uuid = fu.generate_storage_path("jpg", tmpdir)

            # UUID4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
            uuid_pattern = r"^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$"
            assert re.match(uuid_pattern, uuid), f"UUID {uuid} is not valid format"

    def test_creates_directory_structure(self):
        """Test that directories are created."""
        import os
        import shutil
        import tempfile

        # Use a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            path, uuid = fu.generate_storage_path("png", tmpdir)

            # Directory should exist
            parent_dir = os.path.dirname(path)
            assert os.path.exists(parent_dir), f"Directory {parent_dir} was not created"

    def test_different_uuids_generated(self):
        """Test that each call generates a unique UUID."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path1, uuid1 = fu.generate_storage_path("png", tmpdir)
            path2, uuid2 = fu.generate_storage_path("png", tmpdir)

            assert uuid1 != uuid2, "UUIDs should be unique"
            assert path1 != path2, "Paths should be unique"
