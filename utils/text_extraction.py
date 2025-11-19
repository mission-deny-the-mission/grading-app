"""
Text extraction utilities for processing various file formats.
This module consolidates all text extraction logic to eliminate redundancy.

DEPRECATED: This module is deprecated and will be removed in a future version.
Please use services.document_parser instead.
"""

import PyPDF2
from docx import Document


def extract_text_from_docx(file_path):
    """Extract text from a Word document."""
    try:
        doc = Document(file_path)
        text = []
        for paragraph in doc.paragraphs:
            text.append(paragraph.text)
        extracted_text = "\n".join(text)

        if not extracted_text.strip():
            return "Error reading Word document: Document appears to be empty or contains no readable text."

        return extracted_text
    except Exception as e:
        return f"Error reading Word document: {str(e)}"


def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    try:
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)

            if len(pdf_reader.pages) == 0:
                return "Error reading PDF: Document appears to be empty or corrupted."

            text = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)

            extracted_text = "\n".join(text)

            if not extracted_text.strip():
                return "Error reading PDF: Document appears to be empty or contains no readable text."

            return extracted_text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


def extract_text_from_txt(file_path):
    """Extract text from a text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            return "Error reading text file: File appears to be empty."

        return text
    except Exception as e:
        return f"Error reading text file: {str(e)}"


def extract_marking_scheme_content(file_path, file_type):
    """Extract content from marking scheme file."""
    try:
        if file_type == "docx":
            return extract_text_from_docx(file_path)
        elif file_type == "pdf":
            return extract_text_from_pdf(file_path)
        elif file_type == "txt":
            return extract_text_from_txt(file_path)
        else:
            return f"Unsupported file type: {file_type}"
    except Exception as e:
        return f"Error reading marking scheme file: {str(e)}"


def extract_text_by_file_type(file_path, file_type):
    """Extract text from a file based on its type."""
    if file_type == "docx":
        return extract_text_from_docx(file_path)
    elif file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type == "txt":
        return extract_text_from_txt(file_path)
    else:
        return f"Unsupported file type: {file_type}"
