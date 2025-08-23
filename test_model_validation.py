#!/usr/bin/env python3
"""
Comprehensive test to validate all model options in dropdown menus.
Tests consistency between GUI display names and backend model names.
"""

import requests
import re
import json
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Base URL for the application
BASE_URL = "http://localhost:5000"

# Expected model mappings from GUI to backend
EXPECTED_MODEL_MAPPINGS = {
    # Configuration dropdowns
    "config_dropdowns": {
        "openrouter": {
            "GPT-5": "openai/gpt-5",
            "Claude 4 Sonnet": "anthropic/claude-4-sonnet", 
            "Claude 4 Opus": "anthropic/claude-4-opus",
            "Gemini 2.5 Pro": "google/gemini-2.5-pro",
            "GPT-4o": "openai/gpt-4o",
            "Gemini Pro": "google/gemini-pro"
        },
        "claude": {
            "Claude 4 Sonnet": "claude-4-sonnet",
            "Claude 4 Opus": "claude-4-opus", 
            "Claude 4 Haiku": "claude-4-haiku",
            "Claude 3.5 Sonnet": "claude-3.5-sonnet-20241022"
        },
        "gemini": {
            "Gemini 2.0 Flash": "gemini-2.0-flash-exp",
            "Gemini Pro": "gemini-pro",
            "Gemini Pro Vision": "gemini-pro-vision"
        },
        "openai": {
            "GPT-5": "gpt-5",
            "GPT-5 Mini": "gpt-5-mini",
            "GPT-4o": "gpt-4o",
            "GPT-4o Mini": "gpt-4o-mini",
            "GPT-4 Turbo": "gpt-4-turbo"
        },
        "ollama": {
            "Llama 2": "llama2",
            "Llama 3": "llama3",
            "Code Llama": "codellama",
            "Mistral": "mistral",
            "Gemma": "gemma",
            "Phi": "phi"
        }
    },
    # Main interface model selection
    "main_interface": {
        "GPT-5": "openai/gpt-5",
        "GPT-5 Mini": "openai/gpt-5-mini", 
        "Claude 4 Sonnet": "anthropic/claude-4-sonnet",
        "Claude 4 Opus": "anthropic/claude-4-opus",
        "Gemini 2.5 Pro": "google/gemini-2.5-pro",
        "GPT-4o": "openai/gpt-4o",
        "Gemini Pro": "google/gemini-pro"
    }
}

# Known backend nameMap for validation
BACKEND_NAME_MAPS = {
    'anthropic/claude-opus-4-1': 'Claude Opus 4.1 (Latest)',
    'openai/gpt-5': 'GPT-5',
    'openai/gpt-4o': 'GPT-4o',
    'openai/gpt-4o-mini': 'GPT-4o Mini',
    'anthropic/claude-3-opus-20240229': 'Claude 3 Opus',
    'meta-llama/llama-3.1-70b-instruct': 'Llama 3.1 70B',
    'google/gemini-2.5-pro': 'Gemini 2.5 Pro (Latest)',
    'google/gemini-pro-1.5': 'Gemini Pro 1.5',
    'mistralai/mistral-7b-instruct': 'Mistral 7B',
    'openai/gpt-4-turbo': 'GPT-4 Turbo',
    'anthropic/claude-3-haiku-20240307': 'Claude 3 Haiku',
    'claude-4-opus-20250805': 'Claude 4 Opus (Latest)',
    'claude-3-5-sonnet-20241022': 'Claude 3.5 Sonnet',
    'claude-3-opus-20240229': 'Claude 3 Opus',
    'claude-3-sonnet-20240229': 'Claude 3 Sonnet',
    'claude-3-haiku-20240307': 'Claude 3 Haiku',
    'local-model': 'Local Model',
    'llama-3.1-70b-instruct': 'Llama 3.1 70B',
    'mistral-7b-instruct': 'Mistral 7B',
    'codellama-34b-instruct': 'Code Llama 34B'
}

class ModelValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        
    def log_error(self, message: str):
        self.errors.append(f"❌ ERROR: {message}")
        print(f"❌ ERROR: {message}")
        
    def log_warning(self, message: str):
        self.warnings.append(f"⚠️  WARNING: {message}")
        print(f"⚠️  WARNING: {message}")
        
    def log_success(self, message: str):
        self.success_count += 1
        print(f"✅ SUCCESS: {message}")

    def extract_dropdown_options(self, html: str, dropdown_id: str) -> List[Tuple[str, str]]:
        """Extract options from a dropdown in HTML. Returns list of (display_text, value) tuples."""
        pattern = rf'<select[^>]*id="{dropdown_id}"[^>]*>(.*?)</select>'
        dropdown_match = re.search(pattern, html, re.DOTALL)
        
        if not dropdown_match:
            self.log_error(f"Could not find dropdown with id '{dropdown_id}'")
            return []
            
        dropdown_html = dropdown_match.group(1)
        option_pattern = r'<option[^>]*value="([^"]*)"[^>]*>([^<]+)</option>'
        options = re.findall(option_pattern, dropdown_html)
        
        return [(display.strip(), value.strip()) for display, value in options if value.strip()]

    def test_config_page_dropdowns(self):
        """Test all dropdown options in the configuration page."""
        print("\n🔍 Testing Configuration Page Dropdowns...")
        
        try:
            response = requests.get(f"{BASE_URL}/config")
            if response.status_code != 200:
                self.log_error(f"Config page returned status {response.status_code}")
                return
                
            html = response.text
            
            # Test each provider's dropdown
            provider_dropdowns = {
                "openrouter_default_model_select": "openrouter",
                "claude_default_model": "claude", 
                "gemini_default_model": "gemini",
                "openai_default_model": "openai",
                "ollama_default_model_select": "ollama"
            }
            
            for dropdown_id, provider in provider_dropdowns.items():
                print(f"\n  Testing {provider} dropdown ({dropdown_id})...")
                options = self.extract_dropdown_options(html, dropdown_id)
                
                if not options:
                    continue
                    
                expected_mappings = EXPECTED_MODEL_MAPPINGS["config_dropdowns"].get(provider, {})
                
                for display_text, backend_value in options:
                    if display_text == "Use System Default" or backend_value == "":
                        continue  # Skip default option
                    if display_text == "Custom Model...":
                        self.log_success(f"{provider}: Custom option found correctly")
                        continue
                        
                    # Check if this mapping is expected
                    if display_text in expected_mappings:
                        expected_backend = expected_mappings[display_text]
                        if backend_value == expected_backend:
                            self.log_success(f"{provider}: '{display_text}' -> '{backend_value}' ✓")
                        else:
                            self.log_error(f"{provider}: '{display_text}' expected '{expected_backend}' but got '{backend_value}'")
                    else:
                        self.log_warning(f"{provider}: Unexpected option '{display_text}' -> '{backend_value}'")
                        
        except Exception as e:
            self.log_error(f"Failed to test config page: {str(e)}")

    def test_main_interface_dropdown(self):
        """Test model dropdown in main interface."""
        print("\n🔍 Testing Main Interface Model Dropdown...")
        
        try:
            response = requests.get(f"{BASE_URL}/")
            if response.status_code != 200:
                self.log_error(f"Main page returned status {response.status_code}")
                return
                
            html = response.text
            options = self.extract_dropdown_options(html, "modelSelect")
            
            if not options:
                return
                
            expected_mappings = EXPECTED_MODEL_MAPPINGS["main_interface"]
            
            for display_text, backend_value in options:
                if display_text == "Use Default Model" or backend_value == "default":
                    continue  # Skip default option
                if display_text == "Custom Model...":
                    self.log_success("Main interface: Custom option found correctly")
                    continue
                    
                if display_text in expected_mappings:
                    expected_backend = expected_mappings[display_text]
                    if backend_value == expected_backend:
                        self.log_success(f"Main interface: '{display_text}' -> '{backend_value}' ✓")
                    else:
                        self.log_error(f"Main interface: '{display_text}' expected '{expected_backend}' but got '{backend_value}'")
                else:
                    self.log_warning(f"Main interface: Unexpected option '{display_text}' -> '{backend_value}'")
                    
        except Exception as e:
            self.log_error(f"Failed to test main interface: {str(e)}")

    def test_bulk_upload_interface(self):
        """Test model dropdown in bulk upload interface."""
        print("\n🔍 Testing Bulk Upload Interface Model Dropdown...")
        
        try:
            response = requests.get(f"{BASE_URL}/bulk_upload")
            if response.status_code != 200:
                self.log_error(f"Bulk upload page returned status {response.status_code}")
                return
                
            html = response.text
            options = self.extract_dropdown_options(html, "modelSelect")
            
            if not options:
                return
                
            expected_mappings = EXPECTED_MODEL_MAPPINGS["main_interface"]  # Should be same as main
            
            for display_text, backend_value in options:
                if display_text == "Use Default Model" or backend_value == "default":
                    continue
                if display_text == "Custom Model...":
                    self.log_success("Bulk upload: Custom option found correctly")
                    continue
                    
                if display_text in expected_mappings:
                    expected_backend = expected_mappings[display_text]
                    if backend_value == expected_backend:
                        self.log_success(f"Bulk upload: '{display_text}' -> '{backend_value}' ✓")
                    else:
                        self.log_error(f"Bulk upload: '{display_text}' expected '{expected_backend}' but got '{backend_value}'")
                else:
                    self.log_warning(f"Bulk upload: Unexpected option '{display_text}' -> '{backend_value}'")
                    
        except Exception as e:
            self.log_error(f"Failed to test bulk upload interface: {str(e)}")

    def test_backend_model_names(self):
        """Test that backend model names are consistent."""
        print("\n🔍 Testing Backend Model Name Consistency...")
        
        try:
            response = requests.get(f"{BASE_URL}/api/models")
            if response.status_code != 200:
                self.log_error(f"Models API returned status {response.status_code}")
                return
                
            models_data = response.json()
            
            for provider, provider_data in models_data.items():
                if 'popular' in provider_data:
                    print(f"\n  Checking {provider} popular models...")
                    for model_name in provider_data['popular']:
                        if model_name in BACKEND_NAME_MAPS:
                            display_name = BACKEND_NAME_MAPS[model_name]
                            self.log_success(f"{provider}: '{model_name}' maps to '{display_name}'")
                        else:
                            self.log_warning(f"{provider}: '{model_name}' not in nameMap (might be valid)")
                            
        except Exception as e:
            self.log_error(f"Failed to test backend model names: {str(e)}")

    def test_config_save_load_consistency(self):
        """Test that saved configuration values work correctly."""
        print("\n🔍 Testing Configuration Save/Load Consistency...")
        
        test_configs = {
            "openrouter_default_model": "anthropic/claude-4-sonnet",
            "claude_default_model": "claude-4-opus",
            "openai_default_model": "gpt-5-mini",
            "ollama_default_model": "llama3"
        }
        
        try:
            # Save test configuration
            response = requests.post(f"{BASE_URL}/save_config", data=test_configs)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_success("Test configuration saved successfully")
                    
                    # Load and verify
                    load_response = requests.get(f"{BASE_URL}/load_config")
                    if load_response.status_code == 200:
                        loaded_config = load_response.json()
                        
                        for key, expected_value in test_configs.items():
                            actual_value = loaded_config.get(key)
                            if actual_value == expected_value:
                                self.log_success(f"Config consistency: {key} = '{actual_value}' ✓")
                            else:
                                self.log_error(f"Config consistency: {key} expected '{expected_value}' but got '{actual_value}'")
                    else:
                        self.log_error("Failed to load configuration for verification")
                else:
                    self.log_error(f"Failed to save configuration: {result.get('message')}")
            else:
                self.log_error(f"Config save returned status {response.status_code}")
                
        except Exception as e:
            self.log_error(f"Failed to test config save/load: {str(e)}")

    def run_all_tests(self):
        """Run all validation tests."""
        print("🚀 Starting Model Validation Tests...\n")
        
        self.test_config_page_dropdowns()
        self.test_main_interface_dropdown()
        self.test_bulk_upload_interface()
        self.test_backend_model_names()
        self.test_config_save_load_consistency()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"✅ Successes: {self.success_count}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        
        if self.errors:
            print("\n🔥 ERRORS FOUND:")
            for error in self.errors:
                print(f"  {error}")
                
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
                
        if not self.errors:
            print("\n🎉 All critical tests passed! Model configuration is valid.")
        else:
            print(f"\n💥 {len(self.errors)} critical errors found. Please review and fix.")
            
        return len(self.errors) == 0

if __name__ == "__main__":
    validator = ModelValidator()
    success = validator.run_all_tests()
    exit(0 if success else 1)