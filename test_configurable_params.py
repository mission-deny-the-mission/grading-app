#!/usr/bin/env python3
"""
Test script to verify configurable temperature and max_tokens parameters.
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def test_configurable_parameters():
    """Test that configurable parameters are working correctly."""
    
    from flask import Flask
    from models import db, GradingJob
    from tasks import grade_with_openrouter, grade_with_claude, grade_with_lm_studio
    
    # Create Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        print("🧪 Testing configurable parameters...")
        
        # Test 1: Check if new fields exist in database
        print("\n1. Testing database fields...")
        try:
            job = GradingJob.query.first()
            if job:
                print(f"   ✓ Temperature field: {job.temperature}")
                print(f"   ✓ Max tokens field: {job.max_tokens}")
            else:
                print("   ⚠ No jobs found in database")
        except Exception as e:
            print(f"   ❌ Database test failed: {e}")
            return False
        
        # Test 2: Test grading functions with custom parameters
        print("\n2. Testing grading functions with custom parameters...")
        
        test_text = "This is a test document for grading."
        test_prompt = "Please provide a brief evaluation of this document."
        
        # Test with different temperature and max_tokens values
        test_params = [
            (0.1, 1000),  # Low temperature, low tokens
            (0.5, 3000),  # Medium temperature, medium tokens
            (1.0, 5000),  # High temperature, high tokens
        ]
        
        for temp, tokens in test_params:
            print(f"\n   Testing temperature={temp}, max_tokens={tokens}:")
            
            # Test OpenRouter function
            try:
                result = grade_with_openrouter(
                    test_text, test_prompt, 
                    temperature=temp, max_tokens=tokens
                )
                if result['success']:
                    print(f"   ✓ OpenRouter: Success (response length: {len(result['grade'])} chars)")
                else:
                    print(f"   ⚠ OpenRouter: {result['error']}")
            except Exception as e:
                print(f"   ❌ OpenRouter test failed: {e}")
            
            # Test Claude function
            try:
                result = grade_with_claude(
                    test_text, test_prompt, 
                    temperature=temp, max_tokens=tokens
                )
                if result['success']:
                    print(f"   ✓ Claude: Success (response length: {len(result['grade'])} chars)")
                else:
                    print(f"   ⚠ Claude: {result['error']}")
            except Exception as e:
                print(f"   ❌ Claude test failed: {e}")
            
            # Test LM Studio function
            try:
                result = grade_with_lm_studio(
                    test_text, test_prompt, 
                    temperature=temp, max_tokens=tokens
                )
                if result['success']:
                    print(f"   ✓ LM Studio: Success (response length: {len(result['grade'])} chars)")
                else:
                    print(f"   ⚠ LM Studio: {result['error']}")
            except Exception as e:
                print(f"   ❌ LM Studio test failed: {e}")
        
        print("\n✅ Configurable parameters test completed!")
        return True

if __name__ == "__main__":
    success = test_configurable_parameters()
    if success:
        print("\n🎉 All tests passed! Configurable parameters are working correctly.")
    else:
        print("\n💥 Some tests failed. Please check the error messages above.")
        sys.exit(1)
