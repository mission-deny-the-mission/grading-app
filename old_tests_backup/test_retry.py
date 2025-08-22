#!/usr/bin/env python3
"""
Test script for retry functionality
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models import db, GradingJob, Submission

# Load environment variables
load_dotenv()

def test_retry_functionality():
    """Test the retry functionality."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['UPLOAD_FOLDER'] = 'uploads'
    db.init_app(app)
    
    with app.app_context():
        print("🧪 Testing Retry Functionality...")
        
        # Get the test job
        job = GradingJob.query.get('9301c623-5729-4e81-b090-1aaed55b6a23')
        if not job:
            print("❌ Test job not found")
            return False
        
        print(f"📋 Job: {job.job_name}")
        print(f"   Status: {job.status}")
        print(f"   Can retry: {job.can_retry_failed_submissions()}")
        
        # Check submissions
        submissions = job.submissions
        print(f"📄 Submissions: {len(submissions)}")
        
        for submission in submissions:
            print(f"   - {submission.original_filename}")
            print(f"     Status: {submission.status}")
            print(f"     Retry count: {submission.retry_count}")
            print(f"     Can retry: {submission.can_retry()}")
        
        # Test retry functionality
        if job.can_retry_failed_submissions():
            print("\n🔄 Testing retry functionality...")
            retried_count = job.retry_failed_submissions()
            print(f"✅ Retried {retried_count} submissions")
            
            # Check updated status
            db.session.refresh(job)
            print(f"   New job status: {job.status}")
            
            for submission in job.submissions:
                if submission.status == 'pending':
                    print(f"   - {submission.original_filename}: {submission.status} (retry_count: {submission.retry_count})")
        else:
            print("\nℹ️  No failed submissions can be retried")
        
        return True

if __name__ == "__main__":
    test_retry_functionality()
