"""
File handling utilities.
This module provides common file operations and validations.
"""

import os
import uuid
from pathlib import Path

from PIL import Image
from werkzeug.utils import secure_filename


class ValidationError(Exception):
    """Custom exception for file validation errors."""

    pass


def determine_file_type(filename):
    """Determine file type based on filename extension."""
    if filename.lower().endswith(".docx"):
        return "docx"
    elif filename.lower().endswith(".pdf"):
        return "pdf"
    elif filename.lower().endswith(".txt"):
        return "txt"
    else:
        return None


def is_allowed_file(filename):
    """Check if file has an allowed extension."""
    return determine_file_type(filename) is not None


def cleanup_file(file_path):
    """Safely remove a file."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass  # Don't fail if file cleanup fails


def get_secure_filename(filename):
    """Get a secure version of the filename."""
    return secure_filename(filename)


def validate_file_upload(file):
    """Validate an uploaded file."""
    if not file or file.filename == "":
        return False, "No file selected"

    if not is_allowed_file(file.filename):
        return False, "Unsupported file type. Please upload .docx, .pdf, or .txt files."

    return True, None


# Image-specific validation and storage functions

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}
MAX_IMAGE_SIZE_BYTES = 52428800  # 50MB


def validate_uploaded_image(file):
    """
    Validate an uploaded image file.

    Args:
        file: FileStorage object from Flask request

    Returns:
        True if validation passes

    Raises:
        ValidationError: If validation fails with detailed error message
    """
    # Check if file exists
    if not file or file.filename == "":
        raise ValidationError("No file selected")

    # Check file extension
    filename_lower = file.filename.lower()
    file_ext = filename_lower.rsplit(".", 1)[1] if "." in filename_lower else ""

    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Invalid file extension '.{file_ext}'. " f"Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Check MIME type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise ValidationError(f"Invalid MIME type '{file.content_type}'. Must be image/*")

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > MAX_IMAGE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        raise ValidationError(f"File too large ({size_mb:.1f}MB). Maximum: 50MB")

    if file_size == 0:
        raise ValidationError("File is empty")

    # Verify actual image data using PIL
    try:
        file.seek(0)
        img = Image.open(file)
        img.verify()  # Verify it's a valid image
        file.seek(0)  # Reset after verify
    except Exception as e:
        raise ValidationError(f"Invalid image data: {str(e)}")

    return True


def generate_storage_path(file_extension, upload_folder="/app/uploads"):
    """
    Generate UUID-based storage path with two-level hashing.

    Args:
        file_extension: File extension (e.g., 'png', 'jpg')
        upload_folder: Base upload directory (default: /app/uploads)

    Returns:
        tuple: (storage_path, file_uuid)
               storage_path: Full path like /uploads/XX/YY/uuid.ext
               file_uuid: UUID string
    """
    # Generate UUID
    file_uuid = str(uuid.uuid4())

    # Two-level hashing using first 4 characters of UUID
    # e.g., "f3b1..." → /uploads/F3/B1/f3b1....png
    level1 = file_uuid[:2].upper()
    level2 = file_uuid[2:4].upper()

    # Construct storage path
    storage_dir = Path(upload_folder) / level1 / level2
    filename = f"{file_uuid}.{file_extension}"
    storage_path = storage_dir / filename

    # Create directories if they don't exist
    storage_dir.mkdir(parents=True, exist_ok=True)

    return str(storage_path), file_uuid
