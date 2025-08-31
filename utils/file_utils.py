"""
File handling utilities.
This module provides common file operations and validations.
"""

import os

from werkzeug.utils import secure_filename


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
