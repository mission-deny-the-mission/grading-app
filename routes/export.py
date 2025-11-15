"""Blueprint for exporting grading results in various formats."""
from flask import Blueprint

export_bp = Blueprint('export', __name__, url_prefix='/api/export')
