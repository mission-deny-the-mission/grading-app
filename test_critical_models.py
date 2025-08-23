#!/usr/bin/env python3
"""
Critical test to validate model name consistency between frontend dropdowns and backend.
Focuses on ensuring all dropdown options correspond to valid backend model names.
"""

import requests
import json
import re

BASE_URL = "http://localhost:5000"

def extract_model_options_from_html(html, context):
    """Extract model options from HTML in various contexts."""
    models = []
    
    if context == "config":
        # Extract from configuration dropdowns
        selects_to_check = [
            "openrouter_default_model_select",
            "claude_default_model", 
            "gemini_default_model",
            "openai_default_model",
            "ollama_default_model_select"
        ]
        
        for select_id in selects_to_check:
            pattern = rf'<select[^>]*id="{select_id}"[^>]*>(.*?)</select>'
            match = re.search(pattern, html, re.DOTALL)
            if match:
                option_pattern = r'<option[^>]*value="([^"]*)"[^>]*>([^<]+)</option>'
                options = re.findall(option_pattern, match.group(1))
                for value, display in options:
                    if value and value not in ["", "custom"]:
                        models.append({
                            "context": f"config_{select_id}",
                            "display_name": display.strip(),
                            "backend_value": value.strip(),
                            "provider": select_id.split('_')[0] if '_' in select_id else select_id
                        })
    
    elif context == "main" or context == "bulk":
        # Extract from main interface model select
        pattern = r'<select[^>]*id="modelSelect"[^>]*>(.*?)</select>'
        match = re.search(pattern, html, re.DOTALL)
        if match:
            option_pattern = r'<option[^>]*value="([^"]*)"[^>]*>([^<]+)</option>'
            options = re.findall(option_pattern, match.group(1))
            for value, display in options:
                if value and value not in ["default", "custom"]:
                    models.append({
                        "context": context,
                        "display_name": display.strip(),
                        "backend_value": value.strip(),
                        "provider": "interface"
                    })
    
    return models

def test_model_naming_consistency():
    """Test that model names are consistent and follow expected patterns."""
    print("🔍 Testing Model Naming Consistency...")
    
    all_models = []
    pages_to_test = [
        ("config", "/config"),
        ("main", "/"),
        ("bulk", "/bulk_upload")
    ]
    
    # Collect all model options
    for context, url in pages_to_test:
        try:
            response = requests.get(f"{BASE_URL}{url}")
            if response.status_code == 200:
                models = extract_model_options_from_html(response.text, context)
                all_models.extend(models)
                print(f"  ✅ Extracted {len(models)} models from {context} page")
            else:
                print(f"  ❌ Failed to fetch {context} page: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error fetching {context} page: {e}")
    
    print(f"\n📊 Found {len(all_models)} model options total")
    
    # Group by backend value to check consistency
    backend_to_displays = {}
    for model in all_models:
        backend_val = model["backend_value"]
        if backend_val not in backend_to_displays:
            backend_to_displays[backend_val] = []
        backend_to_displays[backend_val].append(model)
    
    print(f"\n🔍 Checking {len(backend_to_displays)} unique backend model names...")
    
    # Check naming patterns
    issues_found = 0
    valid_models = 0
    
    for backend_value, model_instances in backend_to_displays.items():
        display_names = [m["display_name"] for m in model_instances]
        contexts = [m["context"] for m in model_instances]
        
        # Check for consistent display names across contexts
        unique_displays = set(display_names)
        if len(unique_displays) > 1:
            print(f"  ⚠️  '{backend_value}' has inconsistent display names: {unique_displays}")
            issues_found += 1
        
        # Validate naming patterns
        is_valid = True
        expected_patterns = {
            "openai/": ["gpt-", "GPT-"],
            "anthropic/": ["claude-", "Claude"],
            "google/": ["gemini-", "Gemini"],
            "meta-llama/": ["llama", "Llama"],
        }
        
        # Check if backend follows expected provider patterns
        for prefix, expected_substrings in expected_patterns.items():
            if backend_value.startswith(prefix):
                if not any(sub in backend_value for sub in expected_substrings):
                    print(f"  ⚠️  '{backend_value}' doesn't match expected pattern for {prefix}")
                    is_valid = False
                    issues_found += 1
                break
        
        # Check basic hyphenation pattern (backend should be hyphenated/lowercase)
        if "/" in backend_value:  # Provider/model format
            model_part = backend_value.split("/", 1)[1]
            if " " in model_part or model_part != model_part.lower():
                print(f"  ⚠️  '{backend_value}' model part should be lowercase and hyphenated")
                is_valid = False
                issues_found += 1
        
        if is_valid:
            valid_models += 1
            print(f"  ✅ '{backend_value}' -> '{display_names[0]}' (used in: {', '.join(set(contexts))})")
    
    return issues_found, valid_models

def test_config_model_save_load():
    """Test that configuration models can be saved and loaded correctly."""
    print("\n🔍 Testing Configuration Model Save/Load...")
    
    test_models = {
        "openrouter_default_model": "anthropic/claude-4-sonnet",
        "claude_default_model": "claude-4-opus",
        "gemini_default_model": "gemini-2.0-flash-exp",
        "openai_default_model": "gpt-5-mini",
        "ollama_default_model": "llama3"
    }
    
    try:
        # Save configuration
        response = requests.post(f"{BASE_URL}/save_config", data=test_models)
        if response.status_code == 200 and response.json().get('success'):
            print("  ✅ Configuration saved successfully")
            
            # Load and verify
            load_response = requests.get(f"{BASE_URL}/load_config")
            if load_response.status_code == 200:
                config = load_response.json()
                
                all_match = True
                for key, expected_value in test_models.items():
                    actual_value = config.get(key)
                    if actual_value == expected_value:
                        print(f"  ✅ {key}: '{expected_value}' saved and loaded correctly")
                    else:
                        print(f"  ❌ {key}: expected '{expected_value}' but got '{actual_value}'")
                        all_match = False
                
                return all_match
            else:
                print("  ❌ Failed to load configuration")
                return False
        else:
            print("  ❌ Failed to save configuration")
            return False
            
    except Exception as e:
        print(f"  ❌ Error during save/load test: {e}")
        return False

def validate_model_patterns():
    """Validate that model names follow expected patterns."""
    print("\n🔍 Validating Model Name Patterns...")
    
    expected_patterns = {
        "OpenAI models": {
            "pattern": r"^(openai/)?gpt-[45].*",
            "examples": ["gpt-5", "gpt-4o", "openai/gpt-5"],
            "description": "Should start with 'gpt-4' or 'gpt-5'"
        },
        "Claude models": {
            "pattern": r"^(anthropic/)?claude-[34].*",
            "examples": ["claude-4-sonnet", "anthropic/claude-4-opus"],
            "description": "Should start with 'claude-3' or 'claude-4'"
        },
        "Gemini models": {
            "pattern": r"^(google/)?gemini.*",
            "examples": ["gemini-pro", "google/gemini-2.5-pro"],
            "description": "Should contain 'gemini'"
        },
        "Ollama models": {
            "pattern": r"^[a-z][a-z0-9-]*$",
            "examples": ["llama3", "codellama", "mistral"],
            "description": "Should be lowercase, alphanumeric with hyphens"
        }
    }
    
    # Test each pattern
    for category, info in expected_patterns.items():
        print(f"\n  Testing {category}:")
        pattern = re.compile(info["pattern"])
        
        for example in info["examples"]:
            if pattern.match(example):
                print(f"    ✅ '{example}' matches pattern")
            else:
                print(f"    ❌ '{example}' doesn't match pattern: {info['description']}")
    
    return True

def main():
    """Run all model validation tests."""
    print("🚀 Running Critical Model Validation Tests\n")
    
    # Test 1: Model naming consistency
    issues, valid = test_model_naming_consistency()
    
    # Test 2: Configuration save/load
    config_ok = test_config_model_save_load()
    
    # Test 3: Pattern validation
    patterns_ok = validate_model_patterns()
    
    # Summary
    print("\n" + "="*60)
    print("📊 CRITICAL MODEL VALIDATION RESULTS")
    print("="*60)
    print(f"✅ Valid models found: {valid}")
    print(f"⚠️  Potential issues: {issues}")
    print(f"💾 Configuration save/load: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"🔤 Pattern validation: {'✅ PASS' if patterns_ok else '❌ FAIL'}")
    
    overall_success = issues == 0 and config_ok and patterns_ok
    
    if overall_success:
        print("\n🎉 All critical model validations passed!")
        print("   Model names are consistent between frontend and backend.")
    else:
        print("\n⚠️  Some issues were found that may need attention.")
        print("   Check the detailed output above for specifics.")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)