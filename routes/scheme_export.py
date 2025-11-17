"""
Scheme Export & Import Routes

Handles marking scheme export to JSON and import from JSON files.
Implements User Story 1 (Export) and User Story 2 (Import).
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
import json
import os
import uuid
import tempfile
import logging
from datetime import datetime
from werkzeug.utils import secure_filename

from models import MarkingScheme, db
from services.scheme_serializer import MarkingSchemeSerializer
from services.scheme_deserializer import MarkingSchemeDecoder

logger = logging.getLogger(__name__)

scheme_export_bp = Blueprint('scheme_export', __name__, url_prefix='/api/schemes')


def sanitize_filename(name):
    """
    Sanitize a name for use in filenames.

    Args:
        name: The name to sanitize

    Returns:
        str: Sanitized filename-safe string
    """
    # Remove or replace invalid characters
    safe_name = secure_filename(name)
    # If the result is empty after sanitization, use a default
    if not safe_name:
        safe_name = "scheme"
    return safe_name


def get_exports_dir():
    """
    Get or create the exports directory.

    Returns:
        str: Path to the exports directory
    """
    # Use app instance path for exports
    exports_dir = os.path.join(current_app.instance_path, 'exports')
    if not os.path.exists(exports_dir):
        os.makedirs(exports_dir, exist_ok=True)
    return exports_dir


@scheme_export_bp.route('/<scheme_id>/export', methods=['POST'])
@login_required
def export_scheme(scheme_id):
    """
    Export a marking scheme to JSON format.

    POST /schemes/{id}/export
    - Verify user authorization (owner check)
    - Call serializer to convert scheme to JSON
    - Generate file name (scheme_name_YYYY-MM-DD.json)
    - Store file (filesystem for now, database column for web version)
    - Return response with file_url, file_name, export_date

    Response:
        200: {file_url, file_name, export_date, criteria_count, scheme_id}
        404: scheme not found
        403: unauthorized
        500: serialization failure
    """
    try:
        # Get scheme by ID from database
        scheme = MarkingScheme.query.get(scheme_id)

        if not scheme:
            return jsonify({
                "error": "Scheme not found",
                "message": f"No marking scheme found with ID {scheme_id}"
            }), 404

        # Authorization check (if owner_id field exists)
        # Note: MarkingScheme model currently doesn't have owner_id field
        # This check is prepared for future multi-user support
        if hasattr(scheme, 'owner_id') and scheme.owner_id:
            if not current_user or not current_user.is_authenticated:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Authentication required"
                }), 403
            if scheme.owner_id != current_user.id:
                return jsonify({
                    "error": "Forbidden",
                    "message": "You do not have permission to export this scheme"
                }), 403

        # Use MarkingSchemeSerializer to convert scheme to JSON
        serializer = MarkingSchemeSerializer()
        try:
            scheme_dict = serializer.to_dict(scheme)
            json_content = serializer.to_json_string(scheme, pretty=True)
        except Exception as e:
            logger.error(f"Failed to serialize scheme {scheme_id}: {str(e)}")
            return jsonify({
                "error": "Serialization failed",
                "message": f"Failed to convert scheme to JSON: {str(e)}"
            }), 500

        # Generate filename: scheme_name_YYYY-MM-DD.json (sanitized)
        safe_name = sanitize_filename(scheme.name)
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        base_filename = f"{safe_name}_{date_str}.json"

        # Get exports directory
        exports_dir = get_exports_dir()
        file_path = os.path.join(exports_dir, base_filename)

        # Generate unique file name using UUID if file already exists
        if os.path.exists(file_path):
            unique_id = str(uuid.uuid4())[:8]
            base_filename = f"{safe_name}_{date_str}_{unique_id}.json"
            file_path = os.path.join(exports_dir, base_filename)

        # Save JSON to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            logger.info(f"Exported scheme {scheme_id} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to write export file for scheme {scheme_id}: {str(e)}")
            return jsonify({
                "error": "File write failed",
                "message": f"Failed to save export file: {str(e)}"
            }), 500

        # Count criteria
        criteria_count = 0
        if scheme_dict and 'criteria' in scheme_dict:
            criteria_count = len(scheme_dict.get('criteria', []))

        # Generate file URL for download
        file_url = f"/api/schemes/{scheme_id}/download"

        # Return success response
        return jsonify({
            "file_url": file_url,
            "file_name": base_filename,
            "export_date": datetime.utcnow().isoformat(),
            "criteria_count": criteria_count,
            "scheme_id": scheme_id
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error exporting scheme {scheme_id}: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@scheme_export_bp.route('/<scheme_id>/download', methods=['GET'])
@login_required
def download_scheme(scheme_id):
    """
    Download a previously exported JSON file.

    GET /schemes/{id}/download
    - Retrieve previously exported JSON file
    - Return with appropriate Content-Disposition header (attachment)

    Response:
        200: JSON file content
        404: file not found
        403: access denied
    """
    try:
        # Get scheme by ID from database
        scheme = MarkingScheme.query.get(scheme_id)

        if not scheme:
            return jsonify({
                "error": "Scheme not found",
                "message": f"No marking scheme found with ID {scheme_id}"
            }), 404

        # Authorization check (if owner_id field exists)
        # Note: MarkingScheme model currently doesn't have owner_id field
        # This check is prepared for future multi-user support
        if hasattr(scheme, 'owner_id') and scheme.owner_id:
            if not current_user or not current_user.is_authenticated:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Authentication required"
                }), 403
            if scheme.owner_id != current_user.id:
                return jsonify({
                    "error": "Forbidden",
                    "message": "You do not have permission to download this scheme"
                }), 403

        # Generate the export on-the-fly since we don't persist export files
        # This ensures we always have the latest version
        serializer = MarkingSchemeSerializer()
        try:
            json_content = serializer.to_json_string(scheme, pretty=True)
        except Exception as e:
            logger.error(f"Failed to serialize scheme {scheme_id} for download: {str(e)}")
            return jsonify({
                "error": "Serialization failed",
                "message": f"Failed to convert scheme to JSON: {str(e)}"
            }), 500

        # Generate filename for download
        safe_name = sanitize_filename(scheme.name)
        download_filename = f"{safe_name}.json"

        # Create a temporary file for sending
        # We use BytesIO to avoid filesystem operations
        from io import BytesIO
        file_obj = BytesIO(json_content.encode('utf-8'))
        file_obj.seek(0)

        # Return file with proper headers
        return send_file(
            file_obj,
            mimetype='application/json',
            as_attachment=True,
            download_name=download_filename
        )

    except Exception as e:
        logger.error(f"Unexpected error downloading scheme {scheme_id}: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@scheme_export_bp.route('/import', methods=['POST'])
@login_required
def import_scheme():
    """
    Import a marking scheme from JSON file.

    POST /schemes/import
    - Accept multipart/form-data file upload
    - Validate file type: must be JSON
    - Validate file size: < 10MB
    - Parse JSON
    - Call validator and deserializer
    - Create new MarkingScheme object in database

    Response:
        201: created scheme_id, name, criteria_count
        400: validation errors
    """
    try:
        # Check if file was included in request
        if 'file' not in request.files:
            return jsonify({
                "error": "Missing file",
                "message": "No file provided in request"
            }), 400

        file = request.files['file']

        # Check if file has a filename
        if not file or file.filename == '':
            return jsonify({
                "error": "Invalid file",
                "message": "No file selected for uploading"
            }), 400

        # Validate file type (must be JSON)
        if not file.filename.lower().endswith('.json'):
            return jsonify({
                "error": "Invalid file type",
                "message": "Only .json files are accepted"
            }), 400

        # Read file content
        try:
            file_content = file.read()
        except Exception as e:
            logger.error(f"Failed to read uploaded file: {str(e)}")
            return jsonify({
                "error": "File read failed",
                "message": "Could not read the uploaded file"
            }), 500

        # Validate file size (< 10MB)
        file_size = len(file_content)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return jsonify({
                "error": "File too large",
                "message": f"Maximum file size is 10MB, got {file_size / 1024 / 1024:.2f}MB"
            }), 413

        # Parse JSON content
        try:
            json_string = file_content.decode('utf-8')
        except UnicodeDecodeError:
            return jsonify({
                "error": "Invalid encoding",
                "message": "File must be UTF-8 encoded JSON"
            }), 400

        # First, validate JSON syntax
        try:
            json_data = json.loads(json_string)
        except json.JSONDecodeError as e:
            return jsonify({
                "error": "Invalid JSON",
                "message": f"JSON parsing error: {str(e)}"
            }), 400

        # Then deserialize and validate schema
        decoder = MarkingSchemeDecoder()
        try:
            scheme_data = decoder.deserialize(json_string)
        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"Import validation failed: {error_msg}")
            return jsonify({
                "error": "Validation failed",
                "message": error_msg,
                "details": decoder.collect_validation_errors(json_data)
            }), 400

        # Create MarkingScheme object in database
        try:
            new_scheme = MarkingScheme(
                name=scheme_data['name'],
                description=scheme_data.get('description'),
                filename=file.filename,
                original_filename=file.filename,
                file_size=file_size,
                file_type='json',
                content=json_string
            )

            db.session.add(new_scheme)
            db.session.commit()

            # Count criteria for response
            criteria_count = len(scheme_data.get('criteria', []))

            logger.info(f"Successfully imported scheme '{new_scheme.name}' with ID {new_scheme.id}")

            return jsonify({
                "scheme_id": new_scheme.id,
                "name": new_scheme.name,
                "criteria_count": criteria_count
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create marking scheme in database: {str(e)}")
            return jsonify({
                "error": "Database error",
                "message": f"Failed to save imported scheme: {str(e)}"
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error importing scheme: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500
