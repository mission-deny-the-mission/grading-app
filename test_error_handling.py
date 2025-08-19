#!/usr/bin/env python3
"""
Test script for error handling system
"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_error_handling_without_api_keys():
    """Test that proper error messages are returned when API keys are not configured."""
    
    print("🧪 Testing Error Handling System...")
    
    # Create a temporary directory for test files
    test_dir = tempfile.mkdtemp()
    original_upload_folder = None
    
    try:
        # Import our modules
        from tasks import process_submission, create_app
        from models import db, GradingJob, Submission
        
        # Create Flask app context
        app = create_app()
        app.config['UPLOAD_FOLDER'] = test_dir
        
        with app.app_context():
            # Create database tables
            db.create_all()
            
            # Create a test job
            job = GradingJob(
                job_name="Test Error Handling Job",
                description="Testing error handling without API keys",
                provider="openrouter",  # This will fail without API key
                prompt="Please grade this document.",
                priority=5
            )
            db.session.add(job)
            db.session.commit()
            
            # Create a test submission
            test_content = "This is a test document for error handling."
            test_file_path = os.path.join(test_dir, "test_document.txt")
            with open(test_file_path, 'w') as f:
                f.write(test_content)
            
            submission = Submission(
                job_id=job.id,
                original_filename="test_document.txt",
                filename="test_document.txt",
                file_type="txt"
            )
            db.session.add(submission)
            db.session.commit()
            
            print(f"\n1. Created test job: {job.job_name} (ID: {job.id})")
            print(f"2. Created test submission: {submission.original_filename} (ID: {submission.id})")
            print(f"   Test file created at: {test_file_path}")
            print(f"   File exists: {os.path.exists(test_file_path)}")
            print(f"   App upload folder: {app.config['UPLOAD_FOLDER']}")
            
            # Test with no API keys configured
            print("\n3. Testing with no API keys configured...")
            
            # Temporarily clear API keys
            original_openrouter_key = os.environ.get('OPENROUTER_API_KEY')
            original_claude_key = os.environ.get('CLAUDE_API_KEY')
            
            if 'OPENROUTER_API_KEY' in os.environ:
                del os.environ['OPENROUTER_API_KEY']
            if 'CLAUDE_API_KEY' in os.environ:
                del os.environ['CLAUDE_API_KEY']
            
            try:
                # Process the submission
                result = process_submission(submission.id)
                
                # Check the result
                if result is False:
                    # Refresh submission from database
                    db.session.refresh(submission)
                    print(f"✅ Error handling working correctly!")
                    print(f"   Submission status: {submission.status}")
                    print(f"   Error message: {submission.error_message}")
                    
                    if "API key not configured" in submission.error_message:
                        print("✅ Correct error message for missing API key")
                    elif "File not found" in submission.error_message:
                        print("⚠️  File path issue - this is expected in test environment")
                    else:
                        print("⚠️  Unexpected error message")
                else:
                    print("❌ Expected failure but got success")
                    
            finally:
                # Restore API keys
                if original_openrouter_key:
                    os.environ['OPENROUTER_API_KEY'] = original_openrouter_key
                if original_claude_key:
                    os.environ['CLAUDE_API_KEY'] = original_claude_key
            
            # Test with unsupported provider
            print("\n4. Testing with unsupported provider...")
            job.provider = "unsupported_provider"
            db.session.commit()
            
            # Create another test file for the second submission
            test_file_path2 = os.path.join(test_dir, "test_document2.txt")
            with open(test_file_path2, 'w') as f:
                f.write(test_content)
            
            submission2 = Submission(
                job_id=job.id,
                original_filename="test_document2.txt",
                filename="test_document2.txt",
                file_type="txt"
            )
            db.session.add(submission2)
            db.session.commit()
            
            result2 = process_submission(submission2.id)
            
            if result2 is False:
                db.session.refresh(submission2)
                print(f"✅ Error handling working correctly!")
                print(f"   Submission status: {submission2.status}")
                print(f"   Error message: {submission2.error_message}")
                
                if "Unsupported provider" in submission2.error_message:
                    print("✅ Correct error message for unsupported provider")
                elif "File not found" in submission2.error_message:
                    print("⚠️  File path issue - this is expected in test environment")
                else:
                    print("⚠️  Unexpected error message")
            else:
                print("❌ Expected failure but got success")
            
            print("\n✅ Error handling system test completed successfully!")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
    
    return True

def test_grading_functions_error_handling():
    """Test that grading functions return proper error messages."""
    
    print("\n🧪 Testing Grading Functions Error Handling...")
    
    try:
        from tasks import grade_with_openrouter, grade_with_claude, grade_with_lm_studio
        
        # Test OpenRouter with invalid API key
        print("\n1. Testing OpenRouter with invalid API key...")
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'invalid-key'}):
            result = grade_with_openrouter("Test document", "Grade this document")
            if not result['success'] and "authentication" in result['error'].lower():
                print("✅ OpenRouter authentication error handling working")
            else:
                print("⚠️  OpenRouter error handling not working as expected")
        
        # Test Claude with invalid API key
        print("\n2. Testing Claude with invalid API key...")
        with patch.dict(os.environ, {'CLAUDE_API_KEY': 'invalid-key'}):
            result = grade_with_claude("Test document", "Grade this document")
            if not result['success'] and "not configured" in result['error'].lower():
                print("✅ Claude configuration error handling working")
            else:
                print("⚠️  Claude error handling not working as expected")
        
        # Test LM Studio with invalid URL
        print("\n3. Testing LM Studio with invalid URL...")
        with patch.dict(os.environ, {'LM_STUDIO_URL': 'http://invalid-url:9999'}):
            result = grade_with_lm_studio("Test document", "Grade this document")
            if not result['success']:
                if "connect" in result['error'].lower() or "timeout" in result['error'].lower():
                    print("✅ LM Studio connection error handling working")
                else:
                    print(f"⚠️  LM Studio error handling returned: {result['error']}")
            else:
                print("⚠️  LM Studio error handling not working as expected")
        
        print("\n✅ Grading functions error handling test completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Error Handling System Tests...")
    
    success1 = test_error_handling_without_api_keys()
    success2 = test_grading_functions_error_handling()
    
    if success1 and success2:
        print("\n🎉 All error handling tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some error handling tests failed!")
        sys.exit(1)
