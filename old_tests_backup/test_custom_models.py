#!/usr/bin/env python3
"""
Test script for custom model functionality
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000"
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

def test_available_models():
    """Test the new API endpoints for getting available models."""
    print("Testing available models API...")
    
    # Test getting all models
    response = requests.get(f"{BASE_URL}/api/models")
    if response.status_code == 200:
        models = response.json()
        print("✓ Available models API working")
        print(f"  OpenRouter models: {len(models.get('openrouter', {}).get('popular', []))}")
        print(f"  Claude models: {len(models.get('claude', {}).get('popular', []))}")
        print(f"  LM Studio models: {len(models.get('lm_studio', {}).get('popular', []))}")
    else:
        print(f"✗ Available models API failed: {response.status_code}")
        return False
    
    # Test getting models for specific provider
    response = requests.get(f"{BASE_URL}/api/models/openrouter")
    if response.status_code == 200:
        openrouter_models = response.json()
        print(f"✓ OpenRouter models API working: {len(openrouter_models.get('popular', []))} models")
    else:
        print(f"✗ OpenRouter models API failed: {response.status_code}")
        return False
    
    return True

def test_custom_model_upload():
    """Test uploading a file with a custom model."""
    print("\nTesting custom model upload...")
    
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == 'sk-or-your-key-here':
        print("⚠ Skipping custom model upload test - OpenRouter API key not configured")
        return True
    
    # Create a simple test file
    test_content = "This is a test document for grading. It contains some sample text to evaluate."
    with open("test_document.txt", "w") as f:
        f.write(test_content)
    
    try:
        # Test with custom model
        with open("test_document.txt", "rb") as f:
            files = {'file': ('test_document.txt', f, 'text/plain')}
            data = {
                'provider': 'openrouter',
                'customModel': 'openai/gpt-4o-mini',  # Use a different model
                'prompt': 'Please grade this document and provide feedback.'
            }
            
            response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✓ Custom model upload successful")
                    print(f"  Model used: {result.get('model')}")
                    print(f"  Provider: {result.get('provider')}")
                else:
                    print(f"✗ Custom model upload failed: {result.get('error')}")
                    return False
            else:
                print(f"✗ Custom model upload failed: {response.status_code}")
                return False
                
    finally:
        # Clean up test file
        if os.path.exists("test_document.txt"):
            os.remove("test_document.txt")
    
    return True

def test_multi_model_comparison():
    """Test multi-model comparison with custom models."""
    print("\nTesting multi-model comparison...")
    
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == 'sk-or-your-key-here':
        print("⚠ Skipping multi-model comparison test - OpenRouter API key not configured")
        return True
    
    # Create a simple test file
    test_content = "This is a test document for multi-model comparison grading."
    with open("test_comparison.txt", "w") as f:
        f.write(test_content)
    
    try:
        # Test with multiple models including custom ones
        with open("test_comparison.txt", "rb") as f:
            files = {'file': ('test_comparison.txt', f, 'text/plain')}
            data = {
                'provider': 'openrouter',
                'models_to_compare[]': ['anthropic/claude-3-5-sonnet-20241022', 'openai/gpt-4o'],
                'customModels[]': ['openai/gpt-4o-mini'],
                'prompt': 'Please grade this document and provide feedback.'
            }
            
            response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success') and result.get('comparison'):
                    print("✓ Multi-model comparison successful")
                    print(f"  Total models: {result.get('total_models')}")
                    print(f"  Successful models: {result.get('successful_models')}")
                    print(f"  Results: {len(result.get('results', []))}")
                else:
                    print(f"✗ Multi-model comparison failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"✗ Multi-model comparison failed: {response.status_code}")
                return False
                
    finally:
        # Clean up test file
        if os.path.exists("test_comparison.txt"):
            os.remove("test_comparison.txt")
    
    return True

def main():
    """Run all tests."""
    print("Testing Custom Model Functionality")
    print("=" * 40)
    
    tests = [
        test_available_models,
        test_custom_model_upload,
        test_multi_model_comparison
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Custom model functionality is working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()
