#!/usr/bin/env python3
"""
Test script to check Celery task processing
"""

import os
import sys
from dotenv import load_dotenv
from tasks import process_job, process_submission_sync
from models import db, GradingJob, Submission
from flask import Flask

# Load environment variables from .env file
load_dotenv()

def create_test_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    db.init_app(app)
    return app

def test_celery_connection():
    """Test if Celery can connect to Valkey/Redis."""
    try:
        from celery import current_app
        result = current_app.control.inspect().active()
        print("✅ Celery connection successful")
        return True
    except Exception as e:
        print(f"❌ Celery connection failed: {e}")
        return False

def test_task_execution():
    """Test if a simple task can be executed."""
    try:
        from tasks import celery_app
        
        # Test a simple task
        result = celery_app.send_task('tasks.process_job', args=['test-job-id'])
        print(f"✅ Task queued successfully: {result.id}")
        return True
    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        return False

def check_api_keys():
    """Check if API keys are configured."""
    print("\n🔑 Checking API Keys:")
    
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    claude_key = os.getenv('CLAUDE_API_KEY')
    lm_studio_url = os.getenv('LM_STUDIO_URL')
    
    print(f"OpenRouter API Key: {'✅ Set' if openrouter_key else '❌ Not set'}")
    print(f"Claude API Key: {'✅ Set' if claude_key else '❌ Not set'}")
    print(f"LM Studio URL: {'✅ Set' if lm_studio_url else '❌ Not set'}")
    
    return bool(openrouter_key or claude_key or lm_studio_url)

def check_recent_jobs():
    """Check recent jobs and their status."""
    app = create_test_app()
    with app.app_context():
        jobs = GradingJob.query.order_by(GradingJob.created_at.desc()).limit(5).all()
        
        print(f"\n📋 Recent Jobs ({len(jobs)} found):")
        for job in jobs:
            print(f"  - {job.job_name} (ID: {job.id[:8]}...) - Status: {job.status}")
            print(f"    Submissions: {len(job.submissions)} total, {sum(1 for s in job.submissions if s.status == 'completed')} completed")
            
            for submission in job.submissions:
                print(f"      - {submission.original_filename}: {submission.status}")
                if submission.error_message:
                    print(f"        Error: {submission.error_message}")

if __name__ == "__main__":
    print("🧪 Testing Celery Configuration...")
    
    # Test Celery connection
    test_celery_connection()
    
    # Test task execution
    test_task_execution()
    
    # Check API keys
    check_api_keys()
    
    # Check recent jobs
    check_recent_jobs()
    
    print("\n🎉 Testing completed!")
