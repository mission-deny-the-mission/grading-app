#!/usr/bin/env python3
"""
Migration script to add saved configurations tables.
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, SavedPrompt, SavedMarkingScheme

def create_app():
    """Create a Flask app for migration."""
    app = Flask(__name__)
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grading_app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    return app

def migrate():
    """Run the migration."""
    app = create_app()
    
    with app.app_context():
        print("Creating saved configurations tables...")
        
        # Create the new tables
        db.create_all()
        
        print("✓ Saved configurations tables created successfully!")
        print("\nNew tables created:")
        print("- saved_prompts")
        print("- saved_marking_schemes")
        print("\nNew columns added to grading_jobs:")
        print("- saved_prompt_id")
        print("- saved_marking_scheme_id")

if __name__ == '__main__':
    migrate()
