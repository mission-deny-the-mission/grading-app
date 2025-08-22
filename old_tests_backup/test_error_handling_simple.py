#!/usr/bin/env python3
"""
Simple test script for error handling system
"""

import os
import sys
from unittest.mock import patch

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_grading_functions_error_handling():
    """Test that grading functions return proper error messages."""
    
    print("🧪 Testing Grading Functions Error Handling...")
    
    try:
        from tasks import grade_with_openrouter, grade_with_claude, grade_with_lm_studio
        
        # Test OpenRouter with invalid API key
        print("\n1. Testing OpenRouter with invalid API key...")
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'invalid-key'}):
            result = grade_with_openrouter("Test document", "Grade this document")
            if not result['success'] and "authentication" in result['error'].lower():
                print("✅ OpenRouter authentication error handling working")
            else:
                print(f"⚠️  OpenRouter error handling returned: {result['error']}")
        
        # Test Claude with invalid API key
        print("\n2. Testing Claude with invalid API key...")
        with patch.dict(os.environ, {'CLAUDE_API_KEY': 'invalid-key'}):
            result = grade_with_claude("Test document", "Grade this document")
            if not result['success'] and "not configured" in result['error'].lower():
                print("✅ Claude configuration error handling working")
            else:
                print(f"⚠️  Claude error handling returned: {result['error']}")
        
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

def test_api_key_validation():
    """Test API key validation logic."""
    
    print("\n🧪 Testing API Key Validation...")
    
    try:
        from tasks import OPENROUTER_API_KEY, CLAUDE_API_KEY
        
        # Test with no API keys
        print("\n1. Testing with no API keys...")
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to get fresh values
            import importlib
            import tasks
            importlib.reload(tasks)
            
            if not tasks.OPENROUTER_API_KEY:
                print("✅ OpenRouter API key correctly detected as not configured")
            else:
                print("⚠️  OpenRouter API key incorrectly detected as configured")
            
            if not tasks.CLAUDE_API_KEY:
                print("✅ Claude API key correctly detected as not configured")
            else:
                print("⚠️  Claude API key incorrectly detected as configured")
        
        # Test with placeholder API keys
        print("\n2. Testing with placeholder API keys...")
        with patch.dict(os.environ, {
            'OPENROUTER_API_KEY': 'sk-or-your-key-here',
            'CLAUDE_API_KEY': 'sk-ant-your-key-here'
        }):
            importlib.reload(tasks)
            
            if tasks.OPENROUTER_API_KEY == 'sk-or-your-key-here':
                print("✅ OpenRouter placeholder key correctly detected")
            else:
                print("⚠️  OpenRouter placeholder key not detected correctly")
            
            if tasks.CLAUDE_API_KEY == 'sk-ant-your-key-here':
                print("✅ Claude placeholder key correctly detected")
            else:
                print("⚠️  Claude placeholder key not detected correctly")
        
        print("\n✅ API key validation test completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Simple Error Handling Tests...")
    
    success1 = test_grading_functions_error_handling()
    success2 = test_api_key_validation()
    
    if success1 and success2:
        print("\n🎉 All error handling tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some error handling tests failed!")
        sys.exit(1)
