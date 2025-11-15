"""Blueprint for applying grading schemes to submissions."""
from flask import Blueprint

grading_bp = Blueprint('grading', __name__, url_prefix='/api/grading')
