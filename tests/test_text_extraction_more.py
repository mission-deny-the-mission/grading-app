"""
Additional tests for utils.text_extraction to increase branch coverage.
"""

import os
import tempfile

from utils import text_extraction as te


class TestDocxExtraction:
    """Test DOCX text extraction functionality."""

    def test_extract_text_from_docx_empty_document(self):
        """Test text extraction from empty DOCX document."""
        from docx import Document

        doc = Document()
        # Add empty paragraph to ensure paragraphs exist but text is empty
        doc.add_paragraph("")

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            doc.save(f.name)
            path = f.name

        try:
            result = te.extract_text_from_docx(path)
            assert "Error reading Word document" in result
        finally:
            os.unlink(path)


class TestPdfExtraction:
    """Test PDF text extraction functionality."""

    def test_extract_text_from_pdf_empty_pages(self, sample_pdf_file):
        """Test text extraction from PDF with empty pages."""
        # sample_pdf_file from conftest creates zero-page PDF
        result = te.extract_text_from_pdf(sample_pdf_file)
        assert "Error reading PDF" in result


class TestTxtExtraction:
    """Test TXT text extraction functionality."""

    def test_extract_text_from_txt_empty(self):
        """Test text extraction from empty TXT file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("   \n\n")
            path = f.name
        try:
            result = te.extract_text_from_txt(path)
            assert "Error reading text file" in result
        finally:
            os.unlink(path)


class TestDispatchers:
    """Test text extraction dispatcher functionality."""

    def test_extract_marking_scheme_content_dispatch(self, sample_text_file):
        """Test marking scheme content extraction dispatch."""
        assert isinstance(
            te.extract_marking_scheme_content(sample_text_file, "txt"), str
        )

    def test_extract_marking_scheme_content_unsupported(self):
        """Test marking scheme content extraction for unsupported file type."""
        result = te.extract_marking_scheme_content("/tmp/whatever", "csv")
        assert "Unsupported file type" in result

    def test_extract_text_by_file_type_dispatch(self, sample_text_file):
        """Test text extraction by file type dispatch."""
        assert isinstance(te.extract_text_by_file_type(sample_text_file, "txt"), str)

    def test_extract_text_by_file_type_unsupported(self):
        """Test text extraction for unsupported file type."""
        result = te.extract_text_by_file_type("/tmp/whatever", "csv")
        assert "Unsupported file type" in result
