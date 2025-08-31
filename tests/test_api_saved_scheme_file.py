"""
Test the file-upload path for creating saved marking schemes in routes.api.
"""

import io
import json


def test_create_saved_marking_scheme_via_file(client):
    """Test creating a saved marking scheme by uploading a file."""
    data = {
        "name": "File Scheme",
        "description": "Uploaded via file",
        "category": "essay",
        "marking_scheme": (io.BytesIO(b"RUBRIC: criteria 1, criteria 2"), "rubric.txt"),
    }
    resp = client.post("/api/saved-marking-schemes", data=data)
    assert resp.status_code == 200
    payload = json.loads(resp.data)
    assert payload["success"] is True
    assert "scheme" in payload
    assert payload["scheme"]["name"] == "File Scheme"
