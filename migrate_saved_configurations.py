#!/usr/bin/env python3
"""
Migration script to add saved configurations tables.
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, SavedPrompt, SavedMarkingScheme, GradingJob

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
        
        # Add columns to existing grading_jobs table if they don't exist
        try:
            # Check if columns already exist
            result = db.session.execute(text("PRAGMA table_info(grading_jobs)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'saved_prompt_id' not in columns:
                print("Adding saved_prompt_id column to grading_jobs table...")
                db.session.execute(text("ALTER TABLE grading_jobs ADD COLUMN saved_prompt_id VARCHAR(36)"))
            
            if 'saved_marking_scheme_id' not in columns:
                print("Adding saved_marking_scheme_id column to grading_jobs table...")
                db.session.execute(text("ALTER TABLE grading_jobs ADD COLUMN saved_marking_scheme_id VARCHAR(36)"))
            
            db.session.commit()
            print("✓ Database migration completed successfully!")
            
        except Exception as e:
            print(f"Warning: Could not add columns to grading_jobs table: {e}")
            print("This might be because the columns already exist or the table doesn't exist yet.")
        
        print("\nNew tables created:")
        print("- saved_prompts")
        print("- saved_marking_schemes")
        print("\nColumns in grading_jobs:")
        print("- saved_prompt_id")
        print("- saved_marking_scheme_id")

if __name__ == '__main__':
    migrate()
