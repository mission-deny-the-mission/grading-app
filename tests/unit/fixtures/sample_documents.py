"""
Sample Documents for Testing

Provides mock PDF, DOCX, and image files for document parsing tests.
"""

import os
import tempfile
from pathlib import Path


def create_sample_pdf(content: str = None) -> str:
    """
    Create a temporary PDF file for testing.

    Args:
        content: Text content to include in PDF

    Returns:
        str: Path to temporary PDF file
    """
    # TODO: Create PDF using reportlab or pypdf2 (T013)
    # For now, create a placeholder
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False)
    temp_file.write(content or "Sample PDF Document\n\nThis is a test document.")
    temp_file.close()
    return temp_file.name


def create_sample_docx(content: str = None) -> str:
    """
    Create a temporary DOCX file for testing.

    Args:
        content: Text content to include in DOCX

    Returns:
        str: Path to temporary DOCX file
    """
    # TODO: Create DOCX using python-docx (T013)
    # For now, create a placeholder
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.docx', delete=False)
    temp_file.write(content or "Sample DOCX Document\n\nThis is a test document.")
    temp_file.close()
    return temp_file.name


def create_sample_png() -> str:
    """
    Create a temporary PNG image file for testing.

    Returns:
        str: Path to temporary PNG file
    """
    # TODO: Create PNG using Pillow (T013)
    # For now, create a placeholder
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    # Write a minimal PNG header
    temp_file.write(b'\x89PNG\r\n\x1a\n')
    temp_file.close()
    return temp_file.name


def create_sample_jpg() -> str:
    """
    Create a temporary JPG image file for testing.

    Returns:
        str: Path to temporary JPG file
    """
    # TODO: Create JPG using Pillow (T013)
    # For now, create a placeholder
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    # Write a minimal JPG header
    temp_file.write(b'\xff\xd8\xff')
    temp_file.close()
    return temp_file.name


def create_sample_rubric_pdf() -> str:
    """
    Create a PDF with rubric content for LLM testing.

    Returns:
        str: Path to temporary PDF file with rubric text
    """
    rubric_content = """
    ESSAY GRADING RUBRIC

    Criterion 1: Organization (20 points)
    - Excellent (20): Clear introduction, body, and conclusion with logical flow
    - Good (15): Most sections present with mostly logical flow
    - Satisfactory (10): Basic structure but flow is unclear
    - Poor (5): Unclear structure or missing sections
    - Fail (0): No clear structure

    Criterion 2: Grammar and Mechanics (20 points)
    - Excellent (20): Virtually no errors
    - Good (15): Few errors that don't interfere with understanding
    - Satisfactory (10): Some errors but most sentences are correct
    - Poor (5): Many errors that sometimes interfere
    - Fail (0): Numerous errors preventing understanding
    """
    # TODO: Actually create PDF with reportlab (T013)
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False)
    temp_file.write(rubric_content)
    temp_file.close()
    return temp_file.name


def create_sample_rubric_docx() -> str:
    """
    Create a DOCX with rubric content for LLM testing.

    Returns:
        str: Path to temporary DOCX file with rubric text
    """
    rubric_content = """
    PROJECT GRADING RUBRIC

    Requirements Analysis (15 points)
    Complete requirements gathering with stakeholder input and documentation - Excellent
    Good requirements with minor gaps - Good
    Basic requirements but some missing - Satisfactory
    Incomplete or unclear requirements - Poor

    System Design (20 points)
    Excellent architecture with scalability - Excellent
    Good design with minor improvements needed - Good
    Adequate design but lacks optimization - Satisfactory
    Poor design with significant issues - Poor
    """
    # TODO: Actually create DOCX with python-docx (T013)
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.docx', delete=False)
    temp_file.write(rubric_content)
    temp_file.close()
    return temp_file.name


def cleanup_temp_file(file_path: str) -> None:
    """
    Clean up a temporary file.

    Args:
        file_path: Path to temporary file to delete
    """
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


def get_all_sample_documents():
    """
    Get paths to all sample documents (for cleanup).

    Returns:
        list: List of temporary file paths
    """
    # TODO: Track created files for cleanup (T013)
    return []
