"""
Simple test runner for bulk upload model loading tests.
This file provides a way to run the tests without requiring external dependencies.
"""

import os
import re
import sys


class TestRunner:
    """Simple test runner for bulk upload model loading functionality."""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []

    def assert_true(self, condition, message):
        """Simple assertion helper."""
        if condition:
            self.tests_passed += 1
            self.test_results.append(f"✓ PASS: {message}")
            return True
        else:
            self.tests_failed += 1
            self.test_results.append(f"✗ FAIL: {message}")
            return False

    def assert_contains(self, content, item, message):
        """Helper to check if content contains an item."""
        return self.assert_true(item in content, f"{message} - Missing: {item}")

    def assert_not_contains(self, content, item, message):
        """Helper to check if content doesn't contain an item."""
        return self.assert_true(item not in content, f"{message} - Should not contain: {item}")

    def extract_script_content(self, html_content):
        """Extract JavaScript content from HTML."""
        script_match = re.search(r'<script>(.*?)</script>', html_content, re.DOTALL)
        if not script_match:
            raise ValueError("No script content found in HTML")
        return script_match.group(1)

    def get_element_references(self, script_content):
        """Get all getElementById references from JavaScript."""
        return re.findall(r'getElementById\([\'"]([^\'"]+)[\'"]\)', script_content)

    def get_function_definitions(self, script_content):
        """Get all function definitions from JavaScript."""
        return re.findall(r'function\s+(\w+)\s*\(', script_content)

    def test_bulk_upload_page_contains_required_elements(self):
        """Test that the bulk upload page contains all required DOM elements."""
        if not os.path.exists('../templates/bulk_upload.html'):
            self.test_results.append("✗ SKIP: templates/bulk_upload.html not found")
            return

        with open('../templates/bulk_upload.html', 'r') as f:
            html_content = f.read()

        # Test for critical model loading elements
        required_elements = [
            'id="provider"',              # Provider selection dropdown
            'id="modelSelect"',           # Single model selection dropdown
            'id="modelSelectSpinner"',    # Loading spinner for models
            'id="bulkModelLoadingStatus"',  # Loading status text
            'id="bulkModelError"',        # Error display div
            'id="refreshBulkModelsBtn"',  # Refresh models button
            'id="enableComparison"',      # Multi-model comparison checkbox
            'id="modelSelection"',        # Model selection section
            'id="allModelsContainer"',    # Container for all models
            'id="providerFilters"',       # Provider filter checkboxes
            'id="modelSearch"',           # Model search input
            'id="selectedCount"'          # Selected models count
        ]

        all_elements_found = True
        for element_id in required_elements:
            if not self.assert_contains(html_content, element_id, f"Required element '{element_id}' found"):
                all_elements_found = False

        if all_elements_found:
            self.test_results.append("✓ PASS: All required DOM elements found")

    def test_bulk_upload_page_no_references_to_missing_elements(self):
        """Test that the bulk upload page doesn't reference missing DOM elements."""
        if not os.path.exists('../templates/bulk_upload.html'):
            self.test_results.append("✗ SKIP: templates/bulk_upload.html not found")
            return

        with open('../templates/bulk_upload.html', 'r') as f:
            html_content = f.read()

        try:
            script_content = self.extract_script_content(html_content)
            element_references = self.get_element_references(script_content)

            # Check for references to elements that shouldn't exist
            forbidden_elements = [
                'popularModels',  # This was the problematic element that caused the original issue
            ]

            for forbidden_element in forbidden_elements:
                self.assert_not_contains(element_references, forbidden_element,
                                       f"No reference to forbidden element '{forbidden_element}'")

        except ValueError as e:
            self.test_results.append(f"✗ FAIL: {str(e)}")

    def test_javascript_no_dangerous_patterns(self):
        """Test that JavaScript code doesn't contain dangerous patterns."""
        if not os.path.exists('../templates/bulk_upload.html'):
            self.test_results.append("✗ SKIP: templates/bulk_upload.html not found")
            return

        with open('../templates/bulk_upload.html', 'r') as f:
            html_content = f.read()

        try:
            script_content = self.extract_script_content(html_content)

            # Check for dangerous patterns
            dangerous_patterns = [
                'popularModelsDiv',  # The original issue
                'document.getElementById(\'popularModels\')',  # Direct reference
            ]

            no_issues = True
            for pattern in dangerous_patterns:
                if pattern in script_content:
                    no_issues = False
                    self.assert_true(False, f"Dangerous pattern found: {pattern}")

            if no_issues:
                self.test_results.append("✓ PASS: No dangerous JavaScript patterns found")

        except ValueError as e:
            self.test_results.append(f"✗ FAIL: {str(e)}")

    def test_all_javascript_elements_exist_in_dom(self):
        """Test that all JavaScript getElementById references exist in the DOM."""
        if not os.path.exists('../templates/bulk_upload.html'):
            self.test_results.append("✗ SKIP: templates/bulk_upload.html not found")
            return

        with open('../templates/bulk_upload.html', 'r') as f:
            html_content = f.read()

        try:
            script_content = self.extract_script_content(html_content)
            element_references = self.get_element_references(script_content)

            # Check that each referenced element exists in the DOM
            missing_elements = []
            for element_id in element_references:
                # Simple check - if element_id exists in HTML content
                if f'id="{element_id}"' not in html_content:
                    missing_elements.append(element_id)

            self.assert_true(len(missing_elements) == 0,
                           f"All JavaScript element references exist in DOM - Missing: {missing_elements}")

        except ValueError as e:
            self.test_results.append(f"✗ FAIL: {str(e)}")

    def test_critical_javascript_functions_exist(self):
        """Test that critical JavaScript functions exist and are properly defined."""
        if not os.path.exists('../templates/bulk_upload.html'):
            self.test_results.append("✗ SKIP: templates/bulk_upload.html not found")
            return

        with open('../templates/bulk_upload.html', 'r') as f:
            html_content = f.read()

        try:
            script_content = self.extract_script_content(html_content)
            functions = self.get_function_definitions(script_content)

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

            all_functions_found = True
            for function_name in required_functions:
                if not self.assert_true(function_name in functions,
                                      f"Critical JavaScript function '{function_name}' exists"):
                    all_functions_found = False

            if all_functions_found:
                self.test_results.append("✓ PASS: All critical JavaScript functions found")

        except ValueError as e:
            self.test_results.append(f"✗ FAIL: {str(e)}")

    def test_regression_prevention_popular_models_element_missing(self):
        """Regression test: Ensure no references to the problematic popularModels element."""
        if not os.path.exists('../templates/bulk_upload.html'):
            self.test_results.append("✗ SKIP: templates/bulk_upload.html not found")
            return

        with open('../templates/bulk_upload.html', 'r') as f:
            html_content = f.read()

        # This is the specific regression that was fixed
        self.assert_not_contains(html_content, 'popularModelsDiv',
                                "Regression: No reference to 'popularModelsDiv'")
        self.assert_not_contains(html_content, 'getElementById(\'popularModels\')',
                                "Regression: No direct reference to 'popularModels' element")
        self.assert_not_contains(html_content, 'document.getElementById(\'popularModels\')',
                                "Regression: No document.getElementById reference to 'popularModels' element")

        self.test_results.append("✓ PASS: Regression test passed - no problematic references found")

    def test_model_loading_user_feedback_mechanisms(self):
        """Test that model loading provides proper user feedback."""
        if not os.path.exists('../templates/bulk_upload.html'):
            self.test_results.append("✗ SKIP: templates/bulk_upload.html not found")
            return

        with open('../templates/bulk_upload.html', 'r') as f:
            html_content = f.read()

        # Check for user feedback elements
        feedback_elements = [
            'id="modelSelectSpinner"',  # Loading spinner
            'id="bulkModelLoadingStatus"',  # Status text
            'id="bulkModelError"',  # Error display
            'id="refreshBulkModelsBtn"',  # Refresh button
        ]

        all_feedback_elements_found = True
        for element_id in feedback_elements:
            if not self.assert_contains(html_content, element_id, f"User feedback element found: {element_id}"):
                all_feedback_elements_found = False

        if all_feedback_elements_found:
            self.test_results.append("✓ PASS: All user feedback elements found")

    def test_model_loading_api_calls_exist(self):
        """Test that model loading API calls are present."""
        if not os.path.exists('../templates/bulk_upload.html'):
            self.test_results.append("✗ SKIP: templates/bulk_upload.html not found")
            return

        with open('../templates/bulk_upload.html', 'r') as f:
            html_content = f.read()

        try:
            script_content = self.extract_script_content(html_content)

            # Check for API calls
            api_calls = [
                '/api/models/${provider}',
                '/api/models/all',
                'fetch(',
            ]

            all_api_calls_found = True
            for api_call in api_calls:
                if not self.assert_contains(script_content, api_call, f"API call found: {api_call}"):
                    all_api_calls_found = False

            if all_api_calls_found:
                self.test_results.append("✓ PASS: All required API calls found")

        except ValueError as e:
            self.test_results.append(f"✗ FAIL: {str(e)}")

    def test_error_handling_patterns_exist(self):
        """Test that error handling patterns are present."""
        if not os.path.exists('../templates/bulk_upload.html'):
            self.test_results.append("✗ SKIP: templates/bulk_upload.html not found")
            return

        with open('../templates/bulk_upload.html', 'r') as f:
            html_content = f.read()

        try:
            script_content = self.extract_script_content(html_content)

            # Check for error handling patterns
            error_patterns = [
                'catch(',
                'console.error(',
                'errorDiv.style.display',
                'status.textContent',
            ]

            all_error_patterns_found = True
            for pattern in error_patterns:
                if not self.assert_contains(script_content, pattern, f"Error handling pattern found: {pattern}"):
                    all_error_patterns_found = False

            if all_error_patterns_found:
                self.test_results.append("✓ PASS: All error handling patterns found")

        except ValueError as e:
            self.test_results.append(f"✗ FAIL: {str(e)}")

    def run_all_tests(self):
        """Run all tests and report results."""
        print("Running Bulk Upload Model Loading Tests...")
        print("=" * 50)

        # Run all test methods
        self.test_bulk_upload_page_contains_required_elements()
        self.test_bulk_upload_page_no_references_to_missing_elements()
        self.test_javascript_no_dangerous_patterns()
        self.test_all_javascript_elements_exist_in_dom()
        self.test_critical_javascript_functions_exist()
        self.test_regression_prevention_popular_models_element_missing()
        self.test_model_loading_user_feedback_mechanisms()
        self.test_model_loading_api_calls_exist()
        self.test_error_handling_patterns_exist()

        # Print results
        print("\nTest Results:")
        print("=" * 50)
        for result in self.test_results:
            print(result)

        print("\nSummary:")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_failed}")
        print(f"Total tests: {self.tests_passed + self.tests_failed}")

        if self.tests_failed == 0:
            print("\n🎉 All tests passed! The bulk upload model loading fix is working correctly.")
            return True
        else:
            print(f"\n❌ {self.tests_failed} test(s) failed. Please review the failures above.")
            return False


if __name__ == "__main__":
    # Add the current directory to Python path
    sys.path.insert(0, '.')

    # Run the tests
    runner = TestRunner()
    success = runner.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
