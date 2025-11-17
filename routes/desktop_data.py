"""
Desktop data portability routes for export/import functionality.
Handles backup and restore operations for the desktop application.
"""

import logging
import os
import tempfile
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from desktop import data_export

logger = logging.getLogger(__name__)

desktop_data_bp = Blueprint("desktop_data", __name__)


@desktop_data_bp.route("/desktop/data")
def show_data_management():
    """
    Display data management page with export/import options.

    Returns:
        Rendered template with data management interface
    """
    try:
        # Get information about existing data
        from models import GradingScheme, GradedSubmission, GradingJob, db
        from flask import current_app

        num_schemes = GradingScheme.query.filter_by(is_deleted=False).count()
        num_submissions = GradedSubmission.query.count()
        num_jobs = GradingJob.query.count()

        # Get database size
        db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "").replace("sqlite:///", "")
        database_size = 0
        if db_path and os.path.exists(db_path):
            database_size = os.path.getsize(db_path)

        # Get uploads size
        uploads_path = current_app.config.get("UPLOAD_FOLDER", "uploads")
        uploads_size = 0
        if os.path.exists(uploads_path):
            for root, dirs, files in os.walk(uploads_path):
                uploads_size += sum(os.path.getsize(os.path.join(root, f)) for f in files)

        statistics = {
            "num_schemes": num_schemes,
            "num_submissions": num_submissions,
            "num_jobs": num_jobs,
            "database_size": format_bytes(database_size),
            "database_size_bytes": database_size,
            "uploads_size": format_bytes(uploads_size),
            "uploads_size_bytes": uploads_size,
            "total_size": format_bytes(database_size + uploads_size),
            "total_size_bytes": database_size + uploads_size
        }

        # Check for last backup (if stored in user data directory)
        # For now, we don't track this - it will be None
        last_backup = None

        return render_template(
            "desktop_data.html",
            statistics=statistics,
            last_backup=last_backup
        )

    except Exception as e:
        logger.error(f"Error loading data management page: {e}", exc_info=True)
        return render_template(
            "desktop_data.html",
            statistics=None,
            last_backup=None,
            error="Failed to load data statistics"
        )


@desktop_data_bp.route("/desktop/data/export", methods=["GET"])
def export_all_data():
    """
    Export all application data as a downloadable ZIP bundle.

    Returns:
        ZIP file download with database and uploads
        or JSON error response if export fails
    """
    try:
        logger.info("Starting data export")

        from flask import current_app

        # Get database and uploads paths
        db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "").replace("sqlite:///", "")
        uploads_path = current_app.config.get("UPLOAD_FOLDER", "uploads")

        # Create temp output file
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"grading-app-backup-{timestamp}.zip"
        output_path = os.path.join(tempfile.gettempdir(), filename)

        # Export data
        data_export.export_data(
            database_path=db_path,
            uploads_path=uploads_path,
            output_path=output_path
        )

        logger.info(f"Sending backup bundle: {filename}")

        # Send file as download
        return send_file(
            output_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error during data export: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Export failed: {str(e)}"
        }), 500


@desktop_data_bp.route("/desktop/data/import", methods=["POST"])
def import_all_data():
    """
    Import data from an uploaded backup bundle.

    Accepts file upload (ZIP bundle), validates it, and restores the data.
    Shows warning if overwrite would occur.

    Request:
        - File upload: 'backup_file' (ZIP format)
        - Optional: 'overwrite' (boolean, default False)

    Returns:
        JSON response with success status and message
    """
    try:
        # Check if file was uploaded
        if 'backup_file' not in request.files:
            return jsonify({
                "success": False,
                "message": "No backup file provided"
            }), 400

        backup_file = request.files['backup_file']

        if backup_file.filename == '':
            return jsonify({
                "success": False,
                "message": "No file selected"
            }), 400

        # Validate file is a ZIP
        if not backup_file.filename.endswith('.zip'):
            return jsonify({
                "success": False,
                "message": "Invalid file format. Please upload a ZIP backup file."
            }), 400

        # Save uploaded file to temp directory
        temp_dir = tempfile.gettempdir()
        temp_filename = secure_filename(backup_file.filename)
        temp_path = os.path.join(temp_dir, temp_filename)

        backup_file.save(temp_path)
        logger.info(f"Backup file uploaded to {temp_path}")

        # Validate the bundle
        valid, validation_message = data_export.validate_backup_bundle(temp_path)

        if not valid:
            # Clean up temp file
            os.remove(temp_path)
            return jsonify({
                "success": False,
                "message": f"Invalid backup bundle: {validation_message}"
            }), 400

        # Read metadata from bundle for display
        import zipfile
        import json as json_module
        with zipfile.ZipFile(temp_path, 'r') as zipf:
            metadata_content = zipf.read('metadata.json').decode('utf-8')
            metadata = json_module.loads(metadata_content)

        # Check if data exists and get overwrite preference
        from flask import current_app
        db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "").replace("sqlite:///", "")
        data_exists = os.path.exists(db_path)

        # Get overwrite parameter (default False)
        overwrite = request.form.get('overwrite', 'false').lower() == 'true'

        # If data exists and overwrite is not confirmed, return warning
        if data_exists and not overwrite:
            # Clean up temp file
            os.remove(temp_path)

            # Get current data statistics for comparison
            from models import GradingScheme, GradedSubmission, GradingJob

            current_schemes = GradingScheme.query.filter_by(is_deleted=False).count()
            current_submissions = GradedSubmission.query.count()
            current_jobs = GradingJob.query.count()

            return jsonify({
                "success": False,
                "requires_confirmation": True,
                "message": "Importing this backup will overwrite your existing data. Please confirm to proceed.",
                "current_data": {
                    "schemes": current_schemes,
                    "submissions": current_submissions,
                    "jobs": current_jobs
                },
                "backup_data": {
                    "schemes": metadata.get("statistics", {}).get("num_schemes", 0),
                    "submissions": metadata.get("statistics", {}).get("num_submissions", 0),
                    "jobs": metadata.get("statistics", {}).get("num_jobs", 0),
                    "created_at": metadata.get("created_at", "unknown"),
                    "app_version": metadata.get("app_version", "unknown")
                }
            }), 409  # Conflict status code

        # Perform import
        logger.info(f"Importing data from {temp_path} (overwrite={overwrite})")

        from flask import current_app
        db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "").replace("sqlite:///", "")
        uploads_path = current_app.config.get("UPLOAD_FOLDER", "uploads")

        try:
            data_export.import_data(
                bundle_path=temp_path,
                database_path=db_path,
                uploads_path=uploads_path,
                backup_existing=True
            )
            import_message = f"Data imported successfully. {metadata.get('statistics', {}).get('num_submissions', 0)} submissions restored."

            # Clean up temp file
            os.remove(temp_path)

            logger.info("Data import completed successfully")

            return jsonify({
                "success": True,
                "message": import_message,
                "backup_info": {
                    "created_at": metadata.get("created_at", "unknown"),
                    "app_version": metadata.get("app_version", "unknown"),
                    "statistics": metadata.get("statistics", {})
                }
            })
        except Exception as import_error:
            # Clean up temp file
            os.remove(temp_path)
            return jsonify({
                "success": False,
                "message": f"Import failed: {str(import_error)}"
            }), 500

    except Exception as e:
        logger.error(f"Error during data import: {e}", exc_info=True)
        # Try to clean up temp file if it exists
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

        return jsonify({
            "success": False,
            "message": f"Import failed: {str(e)}"
        }), 500


def format_bytes(size_bytes: int) -> str:
    """
    Format byte size to human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
