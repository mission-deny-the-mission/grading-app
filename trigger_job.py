#!/usr/bin/env python3
"""
Script to manually trigger a job for processing
"""

import os
from dotenv import load_dotenv
from tasks import process_job
from models import db, GradingJob
from flask import Flask

# Load environment variables from .env file
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    db.init_app(app)
    return app

def trigger_job():
    app = create_app()
    with app.app_context():
        # Get the most recent job
        job = GradingJob.query.order_by(GradingJob.created_at.desc()).first()
        
        if not job:
            print("❌ No jobs found")
            return
        
        print(f"🚀 Triggering job: {job.job_name} (ID: {job.id})")
        print(f"   Status: {job.status}")
        print(f"   Submissions: {len(job.submissions)}")
        
        # Trigger the job
        result = process_job.delay(job.id)
        print(f"✅ Job queued with task ID: {result.id}")
        
        # Wait a moment and check status
        import time
        time.sleep(3)
        
        # Refresh job from database
        db.session.refresh(job)
        print(f"📊 Job status after 3 seconds: {job.status}")
        
        for submission in job.submissions:
            print(f"   - {submission.original_filename}: {submission.status}")
            if submission.error_message:
                print(f"     Error: {submission.error_message}")

if __name__ == "__main__":
    trigger_job()
