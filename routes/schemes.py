"""Blueprint for grading scheme CRUD operations."""

from flask import Blueprint

schemes_bp = Blueprint("schemes", __name__, url_prefix="/api/schemes")
