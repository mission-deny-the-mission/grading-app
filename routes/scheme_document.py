"""
Document Upload & Conversion Routes

Handles document-based rubric uploads and LLM-powered conversion.
Implements User Story 3 (Document Upload & Convert).
"""

import logging
import json
from io import BytesIO
from datetime import datetime
import tempfile
import os

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import db, MarkingScheme, DocumentUploadLog, DocumentConversionResult
from services.document_parser import get_document_type

logger = logging.getLogger(__name__)

scheme_document_bp = Blueprint('scheme_document', __name__, url_prefix='/api/schemes')


def get_upload_dir():
    """Get or create uploads directory."""
    upload_dir = os.path.join(current_app.instance_path, 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


@scheme_document_bp.route('/<scheme_id>/documents/upload', methods=['POST'])
@login_required
def upload_document(scheme_id):
    """
    Upload a document for rubric extraction via LLM.

    POST /schemes/{id}/documents/upload
    - Accept multipart/form-data with document file
    - Validate file size: < 50MB
    - Validate file type: PDF, DOCX, PNG, JPG only
    - Create DocumentUploadLog record
    - Create DocumentConversionResult placeholder (PENDING)
    - Queue Celery task: process_document_rubric
    - Return 202 Accepted with conversion_id

    Response:
        202: {conversion_id, status: "PENDING", estimated_seconds}
        400: invalid format
        413: file too large
    """
    try:
        # Get scheme by ID from database
        scheme = MarkingScheme.query.get(scheme_id)
        if not scheme:
            return jsonify({
                "error": "Scheme not found",
                "message": f"No marking scheme found with ID {scheme_id}"
            }), 404

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

        # Validate file type
        filename_lower = file.filename.lower()
        try:
            doc_type = get_document_type(filename_lower)
        except ValueError:
            return jsonify({
                "error": "Invalid file type",
                "message": "Only PDF, DOCX, PNG, and JPG files are accepted"
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

        # Validate file size (< 50MB)
        file_size = len(file_content)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            return jsonify({
                "error": "File too large",
                "message": f"Maximum file size is 50MB, got {file_size / 1024 / 1024:.2f}MB"
            }), 413

        # Save file temporarily
        upload_dir = get_upload_dir()
        safe_filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, safe_filename)

        # Ensure unique filename
        import uuid
        if os.path.exists(file_path):
            name_parts = safe_filename.rsplit('.', 1)
            if len(name_parts) == 2:
                safe_filename = f"{name_parts[0]}_{uuid.uuid4().hex[:8]}.{name_parts[1]}"
            else:
                safe_filename = f"{safe_filename}_{uuid.uuid4().hex[:8]}"
            file_path = os.path.join(upload_dir, safe_filename)

        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {str(e)}")
            return jsonify({
                "error": "File save failed",
                "message": "Could not save the uploaded file"
            }), 500

        # Create DocumentUploadLog record
        try:
            upload_log = DocumentUploadLog(
                user_id=current_user.id,
                file_name=file.filename,
                mime_type=f"application/{doc_type}" if doc_type in ['pdf', 'docx'] else f"image/{doc_type}",
                file_size_bytes=file_size,
                llm_provider="pending",  # Will be set during processing
                llm_model="pending",
                conversion_status="PENDING"
            )
            db.session.add(upload_log)
            db.session.flush()

            # Create DocumentConversionResult placeholder (PENDING)
            conversion_result = DocumentConversionResult(
                upload_log_id=upload_log.id,
                status="PENDING"
            )
            db.session.add(conversion_result)
            db.session.commit()

            logger.info(f"Created conversion job {conversion_result.id} for file {file.filename}")

            # Queue async task to process the document
            try:
                from tasks import process_document_rubric
                from desktop.task_queue import task_queue

                task_queue.submit(
                    process_document_rubric,
                    upload_id=str(upload_log.id),
                    file_path=file_path,
                    document_type=doc_type,
                    max_retries=2
                )
                logger.info(f"Queued document processing task for {upload_log.id}")
            except Exception as e:
                logger.error(f"Failed to queue document processing task: {str(e)}")
                # Return warning that async processing failed
                return jsonify({
                    "conversion_id": str(conversion_result.id),
                    "status": "PENDING",
                    "warning": "Automatic processing could not be started. Please retry later.",
                    "error": str(e)
                }), 202

            # Return 202 Accepted with conversion_id
            return jsonify({
                "conversion_id": str(conversion_result.id),
                "status": "PENDING",
                "estimated_seconds": 30,
                "file_name": file.filename
            }), 202

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create conversion job: {str(e)}")
            return jsonify({
                "error": "Database error",
                "message": f"Failed to create conversion job: {str(e)}"
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error uploading document: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@scheme_document_bp.route('/<scheme_id>/documents/<conversion_id>/status', methods=['GET'])
@login_required
def get_conversion_status(scheme_id, conversion_id):
    """
    Poll conversion status.

    GET /schemes/{id}/documents/{conversion_id}/status
    - Retrieve DocumentConversionResult by conversion_id
    - Return current status (PENDING, PROCESSING, SUCCESS, FAILED)
    - Return progress percentage (estimated)
    - If SUCCESS: include extracted_scheme and uncertainty_flags
    - If FAILED: include error_code and error_message

    Response:
        200: {status, progress, extracted_scheme?, uncertainty_flags?, error_code?, error_message?}
        404: conversion not found
    """
    try:
        # Get scheme by ID from database
        scheme = MarkingScheme.query.get(scheme_id)
        if not scheme:
            return jsonify({
                "error": "Scheme not found",
                "message": f"No marking scheme found with ID {scheme_id}"
            }), 404

        # Get conversion result (conversion_id is a UUID string)
        conversion = DocumentConversionResult.query.get(conversion_id)
        if not conversion:
            return jsonify({
                "error": "Conversion not found",
                "message": f"No conversion found with ID {conversion_id}"
            }), 404

        # Build response
        response_data = {
            "conversion_id": conversion.id,
            "status": conversion.status,
            "progress": 0
        }

        # Set progress based on status
        if conversion.status == "PENDING":
            response_data["progress"] = 0
        elif conversion.status == "PROCESSING":
            response_data["progress"] = 50
        elif conversion.status == "SUCCESS":
            response_data["progress"] = 100
            if conversion.extracted_scheme:
                response_data["extracted_scheme"] = conversion.extracted_scheme
            if conversion.uncertainty_flags:
                response_data["uncertainty_flags"] = conversion.uncertainty_flags
        elif conversion.status == "FAILED":
            response_data["progress"] = 0
            if conversion.error_code:
                response_data["error_code"] = conversion.error_code
            if conversion.error_message:
                response_data["error_message"] = conversion.error_message

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting conversion status: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@scheme_document_bp.route('/<scheme_id>/documents/<conversion_id>/result', methods=['GET'])
@login_required
def get_conversion_result(scheme_id, conversion_id):
    """
    Retrieve completed conversion result.

    GET /schemes/{id}/documents/{conversion_id}/result
    - Retrieve DocumentConversionResult after completion
    - Return: extracted_scheme, uncertainty_flags, llm_provider, conversion_time_ms
    - Return 202 if still processing
    - Return 400 if conversion failed

    Response:
        200: {extracted_scheme, uncertainty_flags, llm_provider, conversion_time_ms}
        202: still processing
        400: conversion failed
        404: not found
    """
    try:
        # Get scheme by ID from database
        scheme = MarkingScheme.query.get(scheme_id)
        if not scheme:
            return jsonify({
                "error": "Scheme not found",
                "message": f"No marking scheme found with ID {scheme_id}"
            }), 404

        # Get conversion result (conversion_id is a UUID string)
        conversion = DocumentConversionResult.query.get(conversion_id)
        if not conversion:
            return jsonify({
                "error": "Conversion not found",
                "message": f"No conversion found with ID {conversion_id}"
            }), 404

        # Check status
        if conversion.status == "PENDING" or conversion.status == "PROCESSING":
            return jsonify({
                "status": conversion.status,
                "message": "Conversion is still in progress"
            }), 202

        if conversion.status == "FAILED":
            return jsonify({
                "error": "Conversion failed",
                "error_code": conversion.error_code or "UNKNOWN_ERROR",
                "message": conversion.error_message or "Conversion failed without details"
            }), 400

        # Return success result
        result = {
            "extracted_scheme": conversion.extracted_scheme or {},
            "uncertainty_flags": conversion.uncertainty_flags or []
        }

        # Get llm_provider from related upload_log
        upload_log = DocumentUploadLog.query.get(conversion.upload_log_id)
        if upload_log and upload_log.llm_provider and upload_log.llm_provider != "pending":
            result["llm_provider"] = upload_log.llm_provider

        # Calculate conversion time if available
        if conversion.created_at and conversion.updated_at:
            conversion_time = (conversion.updated_at - conversion.created_at).total_seconds() * 1000
            result["conversion_time_ms"] = int(conversion_time)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting conversion result: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@scheme_document_bp.route('/<scheme_id>/documents/<conversion_id>/accept', methods=['POST'])
@login_required
def accept_conversion(scheme_id, conversion_id):
    """
    Accept and finalize extracted scheme from conversion.

    POST /schemes/{id}/documents/{conversion_id}/accept
    - Retrieve DocumentConversionResult
    - Accept optionally modified extracted_scheme from request body
    - Validate against JSON schema
    - Create new MarkingScheme from extracted data
    - Save to database
    - Return 201 with new scheme_id

    Response:
        201: {scheme_id, name, criteria_count}
        422: validation failure
        404: not found
    """
    try:
        # Get scheme by ID from database
        scheme = MarkingScheme.query.get(scheme_id)
        if not scheme:
            return jsonify({
                "error": "Scheme not found",
                "message": f"No marking scheme found with ID {scheme_id}"
            }), 404

        # Get conversion result (conversion_id is a UUID string)
        conversion = DocumentConversionResult.query.get(conversion_id)
        if not conversion:
            return jsonify({
                "error": "Conversion not found",
                "message": f"No conversion found with ID {conversion_id}"
            }), 404

        # Get extracted scheme (use optionally provided override)
        extracted_scheme = conversion.extracted_scheme
        if request.is_json:
            request_data = request.get_json()
            if "extracted_scheme" in request_data:
                extracted_scheme = request_data["extracted_scheme"]

        if not extracted_scheme:
            return jsonify({
                "error": "No extracted scheme",
                "message": "Conversion result does not contain extracted scheme"
            }), 422

        # Create new MarkingScheme from extracted data
        try:
            from services.scheme_deserializer import MarkingSchemeDecoder

            # Validate the extracted scheme
            decoder = MarkingSchemeDecoder()
            json_str = json.dumps(extracted_scheme)
            validated_data = decoder.deserialize(json_str)

            # Create MarkingScheme object in database
            new_scheme = MarkingScheme(
                name=validated_data['name'],
                description=validated_data.get('description'),
                filename=f"converted_{datetime.utcnow().isoformat()}.json",
                original_filename=f"conversion_{conversion_id}.json",
                file_size=len(json_str),
                file_type='json',
                content=json_str
            )

            db.session.add(new_scheme)
            db.session.flush()

            # Update conversion result status
            conversion.status = "ACCEPTED"
            conversion.updated_at = datetime.utcnow()
            db.session.commit()

            # Count criteria for response
            criteria_count = len(validated_data.get('criteria', []))

            logger.info(f"Accepted conversion {conversion_id}, created scheme {new_scheme.id}")

            return jsonify({
                "scheme_id": new_scheme.id,
                "name": new_scheme.name,
                "criteria_count": criteria_count
            }), 201

        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"Validation failed for conversion {conversion_id}: {error_msg}")
            return jsonify({
                "error": "Validation failed",
                "message": error_msg
            }), 422
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create marking scheme from conversion: {str(e)}")
            return jsonify({
                "error": "Database error",
                "message": f"Failed to save scheme: {str(e)}"
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error accepting conversion: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500
