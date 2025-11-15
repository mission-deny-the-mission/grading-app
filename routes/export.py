"""Blueprint for exporting grading data in CSV and JSON formats."""
from flask import Blueprint, request, jsonify, make_response
from datetime import datetime, timezone

from models import db, GradingScheme, GradedSubmission
from utils.export_formatters import format_csv, format_json

export_bp = Blueprint('export', __name__, url_prefix='/api/export')


@export_bp.route('/schemes/<scheme_id>', methods=['GET'])
def export_scheme(scheme_id):
    """
    Export grading data for a scheme in CSV or JSON format.

    Query Parameters:
    - format: 'csv' or 'json' (default: 'json')
    - include_incomplete: 'true' or 'false' (default: 'true')
    - start_date: ISO format date string (optional)
    - end_date: ISO format date string (optional)

    Returns:
    - CSV: text/csv with file download
    - JSON: application/json with structured data
    - 400: Invalid format parameter
    - 404: Scheme not found
    """
    try:
        # Validate and get scheme
        scheme = GradingScheme.query.filter_by(id=scheme_id).first()
        if not scheme:
            return jsonify({"error": "Grading scheme not found"}), 404
        if scheme.is_deleted:
            return jsonify({"error": "Grading scheme has been deleted"}), 404

        # Get format parameter
        format_type = request.args.get('format', 'json').lower()
        if format_type not in ['csv', 'json']:
            return jsonify({
                "error": f"Invalid format '{format_type}'. Must be 'csv' or 'json'"
            }), 400

        # Get filter parameters
        include_incomplete = request.args.get('include_incomplete', 'true').lower() == 'true'

        # Query submissions for this scheme
        query = GradedSubmission.query.filter_by(scheme_id=scheme.id)

        # Filter by completion status
        if not include_incomplete:
            query = query.filter_by(is_complete=True)

        # Filter by date range if provided
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(GradedSubmission.created_at >= start_dt)
            except ValueError:
                return jsonify({
                    "error": f"Invalid start_date format. Use ISO format (YYYY-MM-DD)"
                }), 400

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                query = query.filter(GradedSubmission.created_at <= end_dt)
            except ValueError:
                return jsonify({
                    "error": f"Invalid end_date format. Use ISO format (YYYY-MM-DD)"
                }), 400

        # Get all submissions
        submissions = query.all()

        # Convert to dict format for export
        submissions_data = []
        for submission in submissions:
            submission_dict = submission.to_dict()
            submission_dict['scheme_name'] = scheme.name
            submissions_data.append(submission_dict)

        # Format data
        if format_type == 'csv':
            output = format_csv(submissions_data)
            response = make_response(output)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = (
                f'attachment; filename="export_{scheme_id}.csv"'
            )
            return response
        else:  # json
            output = format_json(submissions_data)
            response = make_response(output)
            response.headers['Content-Type'] = 'application/json'
            return response

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
