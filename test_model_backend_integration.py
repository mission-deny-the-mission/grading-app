#!/usr/bin/env python3
"""
Test backend integration with LLM providers to ensure model names work correctly.
This tests the actual model selection logic in the backend.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Config, db
from app import app

def test_backend_model_resolution():
    """Test that the Config.get_default_model() method works correctly."""
    print("🔍 Testing Backend Model Resolution...")
    
    with app.app_context():
        try:
            # Create test configuration
            config = Config.get_or_create()
            
            # Set test default models
            config.openrouter_default_model = "anthropic/claude-4-sonnet"
            config.claude_default_model = "claude-4-opus"
            config.gemini_default_model = "gemini-2.0-flash-exp"
            config.openai_default_model = "gpt-5-mini"
            config.lm_studio_default_model = "local-model"
            config.ollama_default_model = "llama3"
            
            db.session.commit()
            
            # Test model resolution
            test_cases = [
                ("openrouter", "anthropic/claude-4-sonnet"),
                ("claude", "claude-4-opus"),
                ("gemini", "gemini-2.0-flash-exp"),
                ("openai", "gpt-5-mini"),
                ("lm_studio", "local-model"),
                ("ollama", "llama3"),
                ("unknown_provider", "anthropic/claude-3-5-sonnet-20241022")  # should fallback
            ]
            
            success_count = 0
            for provider, expected_model in test_cases:
                actual_model = config.get_default_model(provider)
                if actual_model == expected_model:
                    print(f"  ✅ {provider}: '{actual_model}' (correct)")
                    success_count += 1
                else:
                    print(f"  ❌ {provider}: expected '{expected_model}' but got '{actual_model}'")
            
            return success_count, len(test_cases)
            
        except Exception as e:
            print(f"  ❌ Backend test failed: {e}")
            return 0, len(test_cases)

def test_upload_route_model_selection():
    """Test that upload route properly handles model selection."""
    print("\n🔍 Testing Upload Route Model Selection Logic...")
    
    # Import here to avoid circular imports
    from routes.upload import DEFAULT_MODELS
    
    try:
        # Test the DEFAULT_MODELS structure
        required_providers = ['openrouter', 'claude', 'gemini', 'openai', 'lm_studio', 'ollama']
        
        success_count = 0
        for provider in required_providers:
            if provider in DEFAULT_MODELS:
                default_model = DEFAULT_MODELS[provider].get('default')
                popular_models = DEFAULT_MODELS[provider].get('popular', [])
                
                if default_model:
                    print(f"  ✅ {provider}: default='{default_model}', {len(popular_models)} popular models")
                    success_count += 1
                else:
                    print(f"  ⚠️  {provider}: no default model specified")
            else:
                print(f"  ❌ {provider}: not found in DEFAULT_MODELS")
        
        return success_count, len(required_providers)
        
    except Exception as e:
        print(f"  ❌ Upload route test failed: {e}")
        return 0, len(required_providers)

def test_model_name_formats():
    """Test that model names follow expected formats for different providers."""
    print("\n🔍 Testing Model Name Format Compliance...")
    
    format_tests = [
        # OpenRouter models (provider/model format)
        ("openai/gpt-5", "openrouter", True),
        ("anthropic/claude-4-sonnet", "openrouter", True),
        ("google/gemini-2.5-pro", "openrouter", True),
        ("invalid-format", "openrouter", False),
        
        # Direct provider models (no prefix)
        ("claude-4-opus", "claude", True),
        ("gpt-5-mini", "openai", True),
        ("gemini-2.0-flash-exp", "gemini", True),
        ("llama3", "ollama", True),
        ("local-model", "lm_studio", True),
        
        # Invalid formats
        ("claude-4-opus", "openrouter", False),  # Should have anthropic/ prefix
        ("anthropic/claude-4-opus", "claude", False),  # Shouldn't have prefix
    ]
    
    success_count = 0
    for model_name, expected_provider, should_be_valid in format_tests:
        is_valid = validate_model_format(model_name, expected_provider)
        
        if is_valid == should_be_valid:
            status = "✅" if should_be_valid else "✅ (correctly invalid)"
            print(f"  {status} '{model_name}' for {expected_provider}: {is_valid}")
            success_count += 1
        else:
            expected_str = "valid" if should_be_valid else "invalid"
            actual_str = "valid" if is_valid else "invalid"
            print(f"  ❌ '{model_name}' for {expected_provider}: expected {expected_str} but was {actual_str}")
    
    return success_count, len(format_tests)

def validate_model_format(model_name, provider):
    """Validate if a model name follows the expected format for a provider."""
    if provider == "openrouter":
        # Should have provider/model format
        return "/" in model_name and len(model_name.split("/")) == 2
    
    elif provider in ["claude", "openai", "gemini", "ollama", "lm_studio"]:
        # Should NOT have provider prefix
        return "/" not in model_name
    
    return False

def main():
    """Run all backend integration tests."""
    print("🚀 Running Model Backend Integration Tests\n")
    
    # Test 1: Backend model resolution
    backend_success, backend_total = test_backend_model_resolution()
    
    # Test 2: Upload route model selection
    upload_success, upload_total = test_upload_route_model_selection()
    
    # Test 3: Model name format compliance
    format_success, format_total = test_model_name_formats()
    
    # Summary
    total_success = backend_success + upload_success + format_success
    total_tests = backend_total + upload_total + format_total
    
    print("\n" + "="*60)
    print("📊 BACKEND INTEGRATION TEST RESULTS")
    print("="*60)
    print(f"🔧 Backend model resolution: {backend_success}/{backend_total}")
    print(f"🛣️  Upload route integration: {upload_success}/{upload_total}")
    print(f"📝 Model name format compliance: {format_success}/{format_total}")
    print(f"📈 Overall success rate: {total_success}/{total_tests} ({100*total_success//total_tests}%)")
    
    if total_success == total_tests:
        print("\n🎉 All backend integration tests passed!")
        print("   Model names are properly integrated throughout the system.")
        return True
    else:
        failed = total_tests - total_success
        print(f"\n⚠️  {failed} backend integration issues found.")
        print("   Some model names may not work correctly in the backend.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)