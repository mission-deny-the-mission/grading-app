#!/usr/bin/env python3
"""
Script to fix file type for test submission
"""

import os
from models import db, Submission
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    db.init_app(app)
    return app

def fix_file_type():
    app = create_app()
    with app.app_context():
        # Find the test submission
        submission = Submission.query.filter_by(original_filename='test_document.txt').first()
        
        if submission:
            print(f"Found submission: {submission.original_filename}")
            print(f"Current file_type: {submission.file_type}")
            
            # Fix the file type
            submission.file_type = 'txt'
            submission.status = 'pending'  # Reset status to try again
            db.session.commit()
            
            print(f"Updated file_type to: {submission.file_type}")
            print(f"Reset status to: {submission.status}")
        else:
            print("No test submission found")

if __name__ == "__main__":
    fix_file_type()
