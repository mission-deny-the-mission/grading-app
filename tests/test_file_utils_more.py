"""
Additional tests for utils.file_utils to increase branch coverage.
"""

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from utils import file_utils as fu


class TestDetermineAndAllow:
    def test_determine_file_type_all_extensions(self):
        assert fu.determine_file_type('report.DOCX') == 'docx'
        assert fu.determine_file_type('paper.pdf') == 'pdf'
        assert fu.determine_file_type('notes.TXT') == 'txt'
        assert fu.determine_file_type('archive.zip') is None

    def test_is_allowed_file(self):
        assert fu.is_allowed_file('a.txt') is True
        assert fu.is_allowed_file('a.docx') is True
        assert fu.is_allowed_file('a.pdf') is True
        assert fu.is_allowed_file('a.jpg') is False


class TestSecureAndCleanup:
    def test_get_secure_filename(self):
        # Includes spaces and path traversal characters
        assert fu.get_secure_filename('../../weird name.pdf').endswith('weird_name.pdf')

    def test_cleanup_file_when_exists(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        assert os.path.exists(path)
        fu.cleanup_file(path)
        assert not os.path.exists(path)

    def test_cleanup_file_ignores_errors(self):
        # Simulate an exception in os.remove
        with patch('utils.file_utils.os.path.exists', return_value=True), \
             patch('utils.file_utils.os.remove', side_effect=OSError('boom')):
            # Should not raise
            fu.cleanup_file('/tmp/fake')


class TestValidateFileUpload:
    def test_validate_file_upload_no_file(self):
        ok, err = fu.validate_file_upload(None)
        assert ok is False and 'No file selected' in err

    def test_validate_file_upload_empty_filename(self):
        fake = SimpleNamespace(filename='')
        ok, err = fu.validate_file_upload(fake)
        assert ok is False and 'No file selected' in err

    def test_validate_file_upload_unsupported_type(self):
        fake = SimpleNamespace(filename='image.png')
        ok, err = fu.validate_file_upload(fake)
        assert ok is False and 'Unsupported file type' in err

    def test_validate_file_upload_supported_type(self):
        fake = SimpleNamespace(filename='essay.pdf')
        ok, err = fu.validate_file_upload(fake)
        assert ok is True and err is None


