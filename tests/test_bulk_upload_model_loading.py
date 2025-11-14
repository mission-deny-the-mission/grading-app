"""
Tests for bulk upload model loading functionality.

This test suite ensures that the bulk upload system properly loads models
and prevents regression of missing DOM element issues.
"""

import re
from unittest.mock import patch

from bs4 import BeautifulSoup


class JavaScriptTestHelper:
    """Helper class for testing JavaScript patterns and DOM elements."""

    @staticmethod
    def extract_script_content(html_content):
        """Extract JavaScript content from HTML."""
        script_match = re.search(r'<script>(.*?)</script>', html_content, re.DOTALL)
        if not script_match:
            raise ValueError("No script content found in HTML")
        return script_match.group(1)

    @staticmethod
    def get_element_references(script_content):
        """Get all getElementById references from JavaScript."""
        return re.findall(r'getElementById\([\'"]([^\'"]+)[\'"]\)', script_content)

    @staticmethod
    def get_function_definitions(script_content):
        """Get all function definitions from JavaScript."""
        return re.findall(r'function\s+(\w+)\s*\(', script_content)

    @staticmethod
    def extract_function_section(script_content, function_name):
        """Extract a function section more robustly to handle nested braces."""
        # Find the function start
        function_start_pattern = rf'function {function_name}\s*\([^)]*\)\s*{{'
        start_match = re.search(function_start_pattern, script_content)

        if not start_match:
            return ""

        start_pos = start_match.end() - 1  # Position of opening brace

        # Count braces to find the matching closing brace
        brace_count = 1
        pos = start_pos + 1

        while pos < len(script_content) and brace_count > 0:
            if script_content[pos] == '{':
                brace_count += 1
            elif script_content[pos] == '}':
                brace_count -= 1
            pos += 1

        # Extract the function content
        if brace_count == 0:
            return script_content[start_pos:pos]
        else:
            # Fallback: return everything from start to next function or end
            remaining_content = script_content[start_pos:]
            next_function_match = re.search(r'\n\s*function\s+\w+\s*\(', remaining_content)
            if next_function_match:
                return remaining_content[:next_function_match.start()]
            return remaining_content

    @staticmethod
    def check_error_handling(script_content):
        """Check for proper error handling patterns."""
        error_patterns = [
            r'try\s*{',
            r'catch\s*\(',
            r'\.catch\s*\(',
            r'finally\s*{',
        ]

        found_patterns = []
        for pattern in error_patterns:
            matches = re.findall(pattern, script_content)
            found_patterns.extend(matches)

        return found_patterns


class TestBulkUploadModelLoading:
    """Test suite for bulk upload model loading functionality."""

    def test_bulk_upload_page_contains_required_elements(self, client):
        """Test that the bulk upload page contains all required DOM elements."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        soup = BeautifulSoup(html_content, 'html.parser')

        # Test for critical model loading elements
        required_elements = [
            'provider',              # Provider selection dropdown
            'modelSelect',           # Single model selection dropdown
            'modelSelectSpinner',    # Loading spinner for models
            'bulkModelLoadingStatus',  # Loading status text
            'bulkModelError',        # Error display div
            'refreshBulkModelsBtn',  # Refresh models button
            'enableComparison',      # Multi-model comparison checkbox
            'modelSelection',        # Model selection section
            'allModelsContainer',    # Container for all models
            'providerFilters',       # Provider filter checkboxes
            'modelSearch',           # Model search input
            'selectedCount'          # Selected models count
        ]

        for element_id in required_elements:
            element = soup.find(id=element_id)
            assert element is not None, f"Required element '{element_id}' not found in bulk upload page"

    def test_bulk_upload_page_no_references_to_missing_elements(self, client):
        """Test that the bulk upload page doesn't reference missing DOM elements."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Get all element references
        element_references = JavaScriptTestHelper.get_element_references(script_content)

        # Check for references to elements that shouldn't exist
        forbidden_elements = [
            'popularModels',  # This was the problematic element that caused the original issue
        ]

        for forbidden_element in forbidden_elements:
            assert forbidden_element not in element_references, \
                f"Found reference to forbidden element '{forbidden_element}' in JavaScript"

    def test_javascript_basic_error_handling(self, client):
        """Test that JavaScript has basic error handling for critical operations."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Check for basic error handling patterns in critical functions
        critical_functions = ['loadAvailableModels', 'loadAllProvidersModels']

        for function_name in critical_functions:
            # Check if function exists
            function_pattern = rf'function {function_name}\('
            assert re.search(function_pattern, script_content), f"Function {function_name} not found"

            # Check for some form of error handling (try/catch or .catch)
            error_handling_patterns = [
                rf'function {function_name}.*?try',
                rf'function {function_name}.*?\.catch',
                rf'{function_name}.*?try',
                rf'{function_name}.*?\.catch'
            ]

            has_error_handling = any(re.search(pattern, script_content, re.DOTALL)
                                    for pattern in error_handling_patterns)

            # Note: We don't require strict error handling for all functions as this can be
            # overly restrictive for simple UI functions, but critical data loading functions
            # should have some form of error handling
            if 'load' in function_name:  # Critical data loading functions
                assert has_error_handling, f"Critical function {function_name} should have error handling"

    def test_javascript_has_proper_error_handling(self, client):
        """Test that JavaScript code has proper error handling."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Check for error handling patterns
        error_handling_patterns = JavaScriptTestHelper.check_error_handling(script_content)

        # Assert that some error handling patterns are present
        assert len(error_handling_patterns) > 0, "No error handling patterns found in JavaScript"

        # Check for at least one of the key error handling patterns
        has_try_catch = any('try' in pattern for pattern in error_handling_patterns)
        has_catch = any('catch' in pattern for pattern in error_handling_patterns)
        has_console_error = any('console.error' in script_content for _ in [0])  # Check directly in script

        assert has_try_catch or has_catch, "Missing basic error handling (try/catch) in JavaScript"
        assert 'console.error' in script_content, "Missing console.error logging in JavaScript"

    def test_all_javascript_elements_exist_in_dom(self, client):
        """Test that all JavaScript getElementById references exist in the DOM."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        soup = BeautifulSoup(html_content, 'html.parser')
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Get all element references from JavaScript
        element_references = JavaScriptTestHelper.get_element_references(script_content)

        # Check that each referenced element exists in the DOM
        missing_elements = []
        for element_id in element_references:
            element = soup.find(id=element_id)
            if element is None:
                missing_elements.append(element_id)

        assert len(missing_elements) == 0, \
            f"JavaScript references elements that don't exist in DOM: {missing_elements}"

    def test_critical_javascript_functions_exist(self, client):
        """Test that critical JavaScript functions exist and are properly defined."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Get all function definitions
        functions = JavaScriptTestHelper.get_function_definitions(script_content)

        # Check for critical functions
        required_functions = [
            'loadAvailableModels',
            'loadAllProvidersModels',
            'refreshBulkProviderModels',
            'toggleModelSelection',
            'updateSelectedModelCount',
            'getModelDisplayName',
            'getBulkFallbackModels',
            'toggleCustomModelBulk',
            'resetForm',
            'loadJobTemplate'
        ]

        for function_name in required_functions:
            assert function_name in functions, \
                f"Missing critical JavaScript function: {function_name}"

    def test_api_models_provider_endpoint_works(self, client):
        """Test that the /api/models/<provider> endpoint works correctly."""
        providers = ['openrouter', 'claude', 'gemini', 'openai', 'lm_studio', 'ollama']

        for provider in providers:
            response = client.get(f'/api/models/{provider}')
            assert response.status_code == 200

            data = response.get_json()
            assert isinstance(data, dict), f"Expected dict response for {provider}, got {type(data)}"

            # Check for required structure
            if data:  # Only check if data is not empty (some providers might not be configured)
                assert 'popular' in data, f"Missing 'popular' key in response for {provider}"
                assert isinstance(data['popular'], list), f"'popular' should be a list for {provider}"

    def test_api_models_all_endpoint_works(self, client):
        """Test that the /api/models/all endpoint works correctly."""
        response = client.get('/api/models/all')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, dict), "Expected dict response from /api/models/all"

        # Check that we get data for multiple providers
        assert len(data) > 0, "Expected at least one provider in /api/models/all response"

        # Verify structure of provider data
        for provider, provider_data in data.items():
            assert isinstance(provider_data, dict), f"Provider data for {provider} should be a dict"
            assert 'popular' in provider_data, f"Missing 'popular' key for provider {provider}"
            assert isinstance(provider_data['popular'], list), f"'popular' should be a list for {provider}"

    def test_javascript_load_available_models_function_structure(self, client):
        """Test that the loadAvailableModels function has correct structure."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Check that loadAvailableModels function exists
        assert 'function loadAvailableModels(' in script_content, "loadAvailableModels function not found"

        # Check that function references correct elements (more flexible approach)
        function_section = JavaScriptTestHelper.extract_function_section(script_content, 'loadAvailableModels')

        # Check that function references correct elements
        required_references = [
            'getElementById(\'provider\')',
            'getElementById(\'modelSelect\')',
            'getElementById(\'modelSelectSpinner\')',
            'getElementById(\'bulkModelLoadingStatus\')',
            'getElementById(\'bulkModelError\')'
        ]

        for reference in required_references:
            assert reference in function_section, \
                f"Missing required reference '{reference}' in loadAvailableModels function"

        # Check that function makes API call
        assert '/api/models/' in function_section, "Missing API call in loadAvailableModels function"

        # Check that function handles success and error cases (more flexible)
        assert 'then(' in function_section, "Missing success handling in loadAvailableModels function"
        assert ('catch(' in function_section or 'try' in function_section), \
            "Missing error handling in loadAvailableModels function"

    def test_javascript_load_all_providers_models_function_structure(self, client):
        """Test that the loadAllProvidersModels function has correct structure."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Check that loadAllProvidersModels function exists
        assert 'function loadAllProvidersModels(' in script_content, "loadAllProvidersModels function not found"

        # Extract function section using improved method
        function_section = JavaScriptTestHelper.extract_function_section(script_content, 'loadAllProvidersModels')

        # Check that function references correct elements
        required_references = [
            'getElementById(\'allModelsContainer\')',
            'getElementById(\'providerFilters\')'
        ]

        for reference in required_references:
            assert reference in function_section, \
                f"Missing required reference '{reference}' in loadAllProvidersModels function"

        # Check that function makes API call
        assert '/api/models/all' in function_section, "Missing API call in loadAllProvidersModels function"

        # Check that function creates provider filters
        assert 'provider-filter' in function_section, "Missing provider filter creation in loadAllProvidersModels function"

        # Check that function creates model checkboxes
        assert 'unified-model-checkbox' in function_section, "Missing model checkbox creation in loadAllProvidersModels function"

    def test_javascript_event_listeners_are_properly_bound(self, client):
        """Test that JavaScript event listeners are properly bound."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)

        # Check for key event listeners
        required_event_listeners = [
            'addEventListener(\'change\', function()',
            'addEventListener(\'DOMContentLoaded\', function()',
            'addEventListener(\'change\', toggleModelSelection)',
            'addEventListener(\'submit\', async function(e)',
        ]

        for listener in required_event_listeners:
            assert listener in html_content, f"Missing event listener: {listener}"

        # Check that model loading is triggered on provider change
        assert 'addEventListener(\'change\', function()' in html_content, \
            "Missing provider change event listener"
        assert 'loadAvailableModels()' in html_content, \
            "Missing loadAvailableModels() call in event listeners"

    def test_javascript_error_handling_is_robust(self, client):
        """Test that JavaScript error handling is robust."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)

        # Extract JavaScript content
        script_match = re.search(r'<script>(.*?)</script>', html_content, re.DOTALL)
        assert script_match, "No script content found"

        script_content = script_match.group(1)

        # Check for proper error handling patterns
        error_handling_patterns = [
            'catch(',
            'console.error(',
            'errorDiv.style.display',
            'status.textContent',
            'finally('
        ]

        for pattern in error_handling_patterns:
            assert pattern in script_content, f"Missing error handling pattern: {pattern}"

    def test_fallback_models_function_exists(self, client):
        """Test that fallback models function exists and works."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)

        # Check for fallback models function
        assert 'getBulkFallbackModels(' in html_content, \
            "Missing getBulkFallbackModels function"

        # Check that fallback models are defined for common providers
        providers = ['openrouter', 'claude', 'gemini', 'openai']
        for provider in providers:
            assert f"'{provider}': [" in html_content, \
                f"Missing fallback models for provider {provider}"

    def test_model_comparison_functionality_structure(self, client):
        """Test that model comparison functionality has correct structure."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)

        # Check for model comparison functions
        comparison_functions = [
            'toggleModelSelection()',
            'loadAllProvidersModels()',
            'updateSelectedModelCount()',
            'clearAllModelSelections()',
            'addProviderFilterListeners()',
            'addProviderSelectAllListeners()',
            'addModelSearchListener()'
        ]

        for func in comparison_functions:
            assert func in html_content, f"Missing model comparison function: {func}"

    def test_no_hardcoded_model_references_that_could_break(self, client):
        """Test that there are no hardcoded references that could break."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)

        # Extract JavaScript content
        script_match = re.search(r'<script>(.*?)</script>', html_content, re.DOTALL)
        assert script_match, "No script content found"

        script_content = script_match.group(1)

        # Check for problematic patterns
        problematic_patterns = [
            'popularModelsDiv',  # The original issue
            'document.getElementById(\'popularModels\')',  # Direct reference
        ]

        for pattern in problematic_patterns:
            assert pattern not in script_content, \
                f"Found problematic pattern that could cause regression: {pattern}"

    def test_refresh_models_functionality(self, client):
        """Test that refresh models functionality works."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)

        # Check for refresh functionality
        assert 'refreshBulkProviderModels()' in html_content, \
            "Missing refreshBulkProviderModels function"

        assert 'refreshBulkModelsBtn' in html_content, \
            "Missing refresh button element"

        # Check that refresh function includes cache busting
        assert '?t=${Date.now()}' in html_content, \
            "Missing cache busting in refresh function"

    def test_model_display_name_function_exists(self, client):
        """Test that model display name function exists."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)

        # Check for getModelDisplayName function
        assert 'getModelDisplayName(' in html_content, \
            "Missing getModelDisplayName function"

        # Check for common model name mappings
        model_mappings = [
            'anthropic/claude-opus-4-1',
            'openai/gpt-4o',
            'anthropic/claude-3-5-sonnet-20241022'
        ]

        for model in model_mappings:
            assert model in html_content, \
                f"Missing model display name mapping for {model}"

    @patch('routes.api.get_cached_models')
    def test_api_models_handles_provider_errors(self, mock_get_cached_models, client):
        """Test that API models endpoint handles provider errors gracefully."""
        # Mock get_cached_models to return None for unknown provider
        mock_get_cached_models.return_value = None

        response = client.get('/api/models/unknown_provider')
        assert response.status_code == 400

        data = response.get_json()
        assert 'error' in data
        assert 'Unknown provider' in data['error']

    def test_bulk_upload_form_structure_is_complete(self, client):
        """Test that the bulk upload form has complete structure."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        soup = BeautifulSoup(html_content, 'html.parser')

        # Check for form elements
        job_form = soup.find(id='jobForm')
        assert job_form is not None, "Missing job form"

        upload_form = soup.find(id='uploadForm')
        assert upload_form is not None, "Missing upload form"

        # Check for step indicators
        upload_section = soup.find(id='uploadSection')
        assert upload_section is not None, "Missing upload section"

        job_status = soup.find(id='jobStatus')
        assert job_status is not None, "Missing job status section"

    def test_regression_prevention_popular_models_element_missing(self, client):
        """Regression test: Ensure no references to the problematic popularModels element."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # This is the specific regression that was fixed
        assert 'popularModelsDiv' not in script_content, \
            "Regression: Found reference to 'popularModelsDiv' which should not exist"

        assert 'getElementById(\'popularModels\')' not in script_content, \
            "Regression: Found direct reference to 'popularModels' element"

        assert 'document.getElementById(\'popularModels\')' not in script_content, \
            "Regression: Found document.getElementById reference to 'popularModels' element"

    def test_model_loading_event_listeners_properly_bound(self, client):
        """Test that model loading event listeners are properly bound."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Check for key event listeners related to model loading
        required_listeners = [
            "getElementById('provider').addEventListener('change',",
            "getElementById('enableComparison').addEventListener('change',",
            "addEventListener('DOMContentLoaded', function()",
        ]

        for listener in required_listeners:
            assert listener in script_content, \
                f"Missing required event listener: {listener}"

        # Check that model loading is triggered at the right times
        model_loading_triggers = [
            'loadAvailableModels()',
            'loadAllProvidersModels()',
        ]

        for trigger in model_loading_triggers:
            assert trigger in script_content, \
                f"Missing model loading trigger: {trigger}"

    def test_model_loading_api_endpoints_integration(self, client):
        """Test integration between frontend and backend model loading endpoints."""
        # Test that frontend can successfully call backend endpoints
        providers_to_test = ['openrouter', 'claude', 'gemini']

        for provider in providers_to_test:
            # Test provider-specific endpoint
            response = client.get(f'/api/models/{provider}')
            assert response.status_code == 200

            data = response.get_json()
            assert isinstance(data, dict), f"Expected dict for {provider}"

            if data:  # If provider is configured
                assert 'popular' in data, f"Missing popular models for {provider}"

        # Test all models endpoint
        response = client.get('/api/models/all')
        assert response.status_code == 200

        all_data = response.get_json()
        assert isinstance(all_data, dict), "Expected dict from /api/models/all"

        # Should have data for at least one provider
        assert len(all_data) > 0, "Expected data for at least one provider"

    def test_model_loading_error_recovery(self, client):
        """Test that model loading gracefully handles errors."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Check for error recovery patterns - more flexible approach
        # Look for any form of error handling in the script
        has_try_catch = 'try' in script_content and 'catch' in script_content
        has_promise_catch = '.catch(' in script_content
        has_console_error = 'console.error' in script_content
        has_error_status_update = 'status.textContent' in script_content or 'errorDiv.style.display' in script_content

        # At least one form of error handling should be present
        assert has_try_catch or has_promise_catch, \
            "No error handling found in JavaScript code"

        # For critical model loading functions, we expect more comprehensive error handling
        load_models_section = JavaScriptTestHelper.extract_function_section(script_content, 'loadAvailableModels')
        if load_models_section:
            has_error_handling_in_load = (
                ('try' in load_models_section and 'catch' in load_models_section) or
                '.catch(' in load_models_section
            )
            assert has_error_handling_in_load, \
                "loadAvailableModels function should have error handling"

            # Check for some form of user feedback on errors
            has_user_feedback = (
                'status.textContent' in load_models_section or
                'errorDiv' in load_models_section or
                'console.error' in load_models_section
            )
            assert has_user_feedback, \
                "loadAvailableModels should provide user feedback on errors"

    def test_model_loading_user_feedback_mechanisms(self, client):
        """Test that model loading provides proper user feedback."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        soup = BeautifulSoup(html_content, 'html.parser')

        # Check for user feedback elements
        feedback_elements = [
            ('modelSelectSpinner', 'Loading spinner'),
            ('bulkModelLoadingStatus', 'Status text'),
            ('bulkModelError', 'Error display'),
            ('refreshBulkModelsBtn', 'Refresh button'),
        ]

        for element_id, description in feedback_elements:
            element = soup.find(id=element_id)
            assert element is not None, f"Missing {description}: {element_id}"

        # Check JavaScript for user feedback mechanisms
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        feedback_patterns = [
            'spinner.style.display = \'block\'',
            'status.textContent = \'Loading models',
            'errorDiv.style.display = \'block\'',
            'status.textContent = \'Models loaded successfully',
        ]

        for pattern in feedback_patterns:
            assert pattern in script_content, \
                f"Missing user feedback pattern: {pattern}"

    def test_model_loading_performance_optimizations(self, client):
        """Test that model loading includes performance optimizations."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Check for performance optimizations
        performance_patterns = [
            r'\?t=\${Date\.now\(\)}',  # Cache busting
            r'setTimeout.*status\.textContent.*Ready',  # Reset status after delay
            r'spinner\.style\.display = \'none\'',  # Hide spinner when done
        ]

        for pattern in performance_patterns:
            matches = re.findall(pattern, script_content)
            assert len(matches) > 0, \
                f"Missing performance optimization pattern: {pattern}"

    @patch('routes.api.get_cached_models')
    def test_model_loading_with_mocked_api_failure(self, mock_get_cached_models, client):
        """Test model loading behavior when API fails."""
        # Mock API to raise an exception
        mock_get_cached_models.side_effect = Exception("API connection failed")

        response = client.get('/api/models/openrouter')
        # The endpoint should handle the error gracefully
        assert response.status_code in [200, 400, 500], f"Unexpected status code: {response.status_code}"

        # Check that we get some kind of response (error handling is working)
        if response.status_code == 200:
            data = response.get_json()
            # Should still get a response, possibly with fallback data
            assert isinstance(data, dict), "Response should be JSON"
        elif response.status_code in [400, 500]:
            data = response.get_json()
            # Should get an error message
            assert 'error' in data or 'message' in data or 'models' in data, \
                f"Expected error message in response: {data}"

    def test_bulk_upload_page_semantic_structure(self, client):
        """Test that bulk upload page has proper semantic structure."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        soup = BeautifulSoup(html_content, 'html.parser')

        # Check for proper semantic structure
        semantic_elements = [
            ('h1', 'Main heading'),
            ('h5', 'Section headings'),
            ('form', 'Forms'),
            ('label', 'Form labels'),
            ('select', 'Select dropdowns'),
            ('button', 'Buttons'),
        ]

        for tag_name, description in semantic_elements:
            elements = soup.find_all(tag_name)
            assert len(elements) > 0, f"Missing {description}: {tag_name}"

        # Check for accessibility attributes
        accessibility_checks = [
            ('aria-label', 'ARIA labels'),
            ('for', 'Label for attributes'),
        ]

        for attr_name, description in accessibility_checks:
            elements_with_attr = soup.find_all(attrs={attr_name: True})
            # At least some elements should have these attributes
            if attr_name == 'for':
                assert len(elements_with_attr) > 0, f"Missing {description}: {attr_name}"

    def test_model_loading_cross_browser_compatibility(self, client):
        """Test that model loading code is cross-browser compatible."""
        response = client.get('/bulk_upload')
        assert response.status_code == 200

        html_content = response.get_data(as_text=True)
        script_content = JavaScriptTestHelper.extract_script_content(html_content)

        # Check for cross-browser compatible patterns
        compatible_patterns = [
            'addEventListener(',  # Modern event handling
            'fetch(',  # Modern API calls
            'querySelector(',  # Modern DOM querying
        ]

        # Check that we're using modern, compatible patterns
        for pattern in compatible_patterns:
            assert pattern in script_content, \
                f"Missing cross-browser compatible pattern: {pattern}"

        # Avoid older browser-specific patterns
        incompatible_patterns = [
            'attachEvent(',  # IE-specific
            'document.all',  # IE-specific
            'window.ActiveXObject',  # IE-specific
        ]

        for pattern in incompatible_patterns:
            assert pattern not in script_content, \
                f"Found incompatible browser pattern: {pattern}"
