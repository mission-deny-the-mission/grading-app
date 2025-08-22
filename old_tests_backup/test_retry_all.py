#!/usr/bin/env python3
"""
Test script to verify the retry all functionality for failed submissions.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, GradingJob, Submission
from datetime import datetime

def test_retry_all_functionality():
    """Test the retry all functionality."""
    with app.app_context():
        # Create a test job
        job = GradingJob(
            job_name="Test Retry Job",
            description="Testing retry all functionality",
            provider="openrouter",
            prompt="Please grade this document.",
            status="completed_with_errors"
        )
        db.session.add(job)
        db.session.commit()
        
        # Create some test submissions
        submissions = []
        for i in range(3):
            submission = Submission(
                filename=f"test_file_{i}.pdf",
                original_filename=f"test_file_{i}.pdf",
                file_size=1024,
                file_type="pdf",
                job_id=job.id,
                status="failed" if i < 2 else "completed",  # 2 failed, 1 completed
                error_message=f"Test error {i}" if i < 2 else None,
                retry_count=1 if i < 2 else 0
            )
            submissions.append(submission)
            db.session.add(submission)
        
        db.session.commit()
        
        # Update job progress
        job.update_progress()
        
        print(f"Created test job: {job.job_name}")
        print(f"Job status: {job.status}")
        print(f"Total submissions: {job.total_submissions}")
        print(f"Completed: {job.processed_submissions}")
        print(f"Failed: {job.failed_submissions}")
        print(f"Can retry: {job.can_retry}")
        print(f"Can retry (method): {job.can_retry_failed_submissions()}")
        
        # Test retry all functionality
        if job.can_retry_failed_submissions():
            print("\nRetrying failed submissions...")
            retried_count = job.retry_failed_submissions()
            print(f"Retried {retried_count} submissions")
            
            # Check status after retry
            print(f"Job status after retry: {job.status}")
            print(f"Can retry after retry: {job.can_retry_failed_submissions()}")
            
            # Show submission statuses
            for i, submission in enumerate(submissions):
                print(f"Submission {i}: {submission.status} (retry_count: {submission.retry_count})")
        else:
            print("No submissions can be retried")
        
        # Clean up
        db.session.delete(job)
        db.session.commit()
        print("\nTest completed and cleaned up.")

if __name__ == "__main__":
    test_retry_all_functionality()
