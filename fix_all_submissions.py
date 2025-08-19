#!/usr/bin/env python3
"""
Script to fix all test submissions
"""

import os
from models import db, Submission, GradingJob
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    db.init_app(app)
    return app

def fix_all_submissions():
    app = create_app()
    with app.app_context():
        # Find all test submissions
        submissions = Submission.query.filter_by(original_filename='test_document.txt').all()
        
        print(f"Found {len(submissions)} test submissions:")
        
        for submission in submissions:
            print(f"\nSubmission ID: {submission.id}")
            print(f"  Filename: {submission.original_filename}")
            print(f"  File type: {submission.file_type}")
            print(f"  Status: {submission.status}")
            print(f"  Job ID: {submission.job_id}")
            
            # Fix the file type
            submission.file_type = 'txt'
            submission.status = 'pending'  # Reset status to try again
            print(f"  Updated file_type to: txt")
            print(f"  Reset status to: pending")
        
        db.session.commit()
        print(f"\n✅ Updated {len(submissions)} submissions")

if __name__ == "__main__":
    fix_all_submissions()
