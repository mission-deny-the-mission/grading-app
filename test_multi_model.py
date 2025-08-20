#!/usr/bin/env python3
"""
Test script for multi-model comparison feature.
"""

import requests
import json
import os

def test_multi_model_comparison():
    """Test the multi-model comparison feature."""
    
    # Test data
    test_data = {
        'prompt': 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement',
        'provider': 'openrouter',
        'models_to_compare[]': ['anthropic/claude-3.5-sonnet', 'openai/gpt-4o']
    }
    
    # Create a simple test document
    test_content = """
    This is a test document for the multi-model comparison feature.
    
    The purpose of this document is to test how different AI models grade the same content.
    This will help us understand the differences in grading approaches and feedback styles.
    
    The document contains various elements that should be evaluated:
    - Content quality and relevance
    - Structure and organization  
    - Writing style and clarity
    - Grammar and mechanics
    
    We expect different models to provide different perspectives on this document.
    """
    
    # Save test content to a file
    with open('test_document.txt', 'w') as f:
        f.write(test_content)
    
    try:
        # Test the upload endpoint with multi-model comparison
        print("Testing multi-model comparison feature...")
        
        # Prepare the request
        files = {'file': ('test_document.txt', open('test_document.txt', 'rb'), 'text/plain')}
        data = {
            'prompt': test_data['prompt'],
            'provider': test_data['provider']
        }
        
        # Add models to compare - use a list for the form data
        data['models_to_compare[]'] = test_data['models_to_compare[]']
        
        # Make the request - send multiple values for models_to_compare[]
        response = requests.post('http://localhost:5000/upload', files=files, data=data)
        
        # Debug: print the actual data being sent
        print(f"Data being sent: {data}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Upload request successful")
            print(f"Response keys: {list(result.keys())}")
            
            if result.get('comparison'):
                print("✓ Multi-model comparison detected")
                print(f"✓ Total models: {result.get('total_models')}")
                print(f"✓ Successful models: {result.get('successful_models')}")
                
                for i, model_result in enumerate(result.get('results', [])):
                    print(f"\nModel {i+1}: {model_result.get('provider')} - {model_result.get('model')}")
                    print(f"Status: {'✓ Success' if model_result.get('success') else '✗ Failed'}")
                    if model_result.get('success'):
                        print(f"Grade preview: {model_result.get('grade', '')[:100]}...")
                    else:
                        print(f"Error: {model_result.get('error', 'Unknown error')}")
                
                return True
            else:
                print("✗ Multi-model comparison not detected")
                print(f"Response: {json.dumps(result, indent=2)}")
                return False
        else:
            print(f"✗ Upload request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False
    finally:
        # Clean up test file
        if os.path.exists('test_document.txt'):
            os.remove('test_document.txt')

def test_single_model_backward_compatibility():
    """Test that single model uploads still work (backward compatibility)."""
    
    test_content = "This is a simple test document for backward compatibility testing."
    
    with open('test_single.txt', 'w') as f:
        f.write(test_content)
    
    try:
        print("\nTesting single model backward compatibility...")
        
        files = {'file': ('test_single.txt', open('test_single.txt', 'rb'), 'text/plain')}
        data = {
            'prompt': 'Please grade this document.',
            'provider': 'openrouter',
            'model': 'anthropic/claude-3.5-sonnet'  # Explicitly specify a model
        }
        
        response = requests.post('http://localhost:5000/upload', files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Single model upload successful")
            
            if not result.get('comparison'):
                print("✓ Backward compatibility confirmed")
                print(f"✓ Provider: {result.get('provider')}")
                print(f"✓ Model: {result.get('model')}")
                return True
            else:
                print("✗ Unexpected comparison format for single model")
                return False
        else:
            print(f"✗ Single model upload failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Backward compatibility test failed: {e}")
        return False
    finally:
        if os.path.exists('test_single.txt'):
            os.remove('test_single.txt')

if __name__ == "__main__":
    print("Multi-Model Comparison Feature Test")
    print("=" * 40)
    
    # Test multi-model comparison
    multi_model_success = test_multi_model_comparison()
    
    # Test backward compatibility
    single_model_success = test_single_model_backward_compatibility()
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Multi-model comparison: {'✓ PASS' if multi_model_success else '✗ FAIL'}")
    print(f"Backward compatibility: {'✓ PASS' if single_model_success else '✗ FAIL'}")
    
    if multi_model_success and single_model_success:
        print("\n🎉 All tests passed! Multi-model comparison feature is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
