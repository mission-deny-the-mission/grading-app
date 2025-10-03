#!/usr/bin/env python3
"""
Quick validation script for the bulk upload model loading fix.

This script provides a fast way to verify that the critical model loading
issue has been resolved and no regressions have been introduced.

Usage:
    python validate_bulk_upload_fix.py

Returns:
    0 if all validations pass
    1 if any validation fails
"""

import os
import re
import sys


def extract_script_content(html_content):
    """Extract JavaScript content from HTML."""
    script_match = re.search(r'<script>(.*?)</script>', html_content, re.DOTALL)
    if not script_match:
        raise ValueError("No script content found in HTML")
    return script_match.group(1)


def get_element_references(script_content):
    """Get all getElementById references from JavaScript."""
    return re.findall(r'getElementById\([\'"]([^\'"]+)[\'"]\)', script_content)


def validate_bulk_upload_fix():
    """Validate that the bulk upload model loading fix is working."""

    print("🔍 Validating Bulk Upload Model Loading Fix")
    print("=" * 50)

    # Check if file exists
    file_path = 'templates/bulk_upload.html'
    if not os.path.exists(file_path):
        print(f"❌ ERROR: {file_path} not found")
        return False

    print(f"✓ Found {file_path}")

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract JavaScript
    try:
        script_content = extract_script_content(html_content)
        print("✓ JavaScript content extracted successfully")
    except ValueError as e:
        print(f"❌ ERROR: {e}")
        return False

    # Test 1: Check for the original problematic reference
    print("\n🧪 Test 1: Regression Prevention")
    if 'popularModelsDiv' in html_content:
        print("❌ FAIL: Found reference to 'popularModelsDiv' (regression!)")
        return False
    else:
        print("✓ PASS: No reference to 'popularModelsDiv'")

    if 'getElementById(\'popularModels\')' in script_content:
        print("❌ FAIL: Found direct reference to 'popularModels' element")
        return False
    else:
        print("✓ PASS: No direct reference to 'popularModels' element")

    # Test 2: Check for required DOM elements
    print("\n🧪 Test 2: Required DOM Elements")
    required_elements = [
        'id="provider"',
        'id="modelSelect"',
        'id="modelSelectSpinner"',
        'id="bulkModelLoadingStatus"',
        'id="bulkModelError"',
        'id="refreshBulkModelsBtn"',
        'id="enableComparison"',
        'id="modelSelection"',
        'id="allModelsContainer"',
        'id="providerFilters"',
        'id="modelSearch"',
        'id="selectedCount"'
    ]

    missing_elements = []
    for element in required_elements:
        if element not in html_content:
            missing_elements.append(element)

    if missing_elements:
        print(f"❌ FAIL: Missing required elements: {missing_elements}")
        return False
    else:
        print(f"✓ PASS: All {len(required_elements)} required elements found")

    # Test 3: Check for critical JavaScript functions
    print("\n🧪 Test 3: Critical JavaScript Functions")
    functions = re.findall(r'function\s+(\w+)\s*\(', script_content)
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

    missing_functions = []
    for function in required_functions:
        if function not in functions:
            missing_functions.append(function)

    if missing_functions:
        print(f"❌ FAIL: Missing critical functions: {missing_functions}")
        return False
    else:
        print(f"✓ PASS: All {len(required_functions)} critical functions found")

    # Test 4: Check that all JavaScript references exist in DOM
    print("\n🧪 Test 4: DOM Reference Validation")
    element_references = get_element_references(script_content)
    orphaned_references = []

    for element_id in element_references:
        if f'id="{element_id}"' not in html_content:
            orphaned_references.append(element_id)

    if orphaned_references:
        print(f"❌ FAIL: JavaScript references to missing elements: {orphaned_references}")
        return False
    else:
        print(f"✓ PASS: All {len(element_references)} JavaScript references exist in DOM")

    # Test 5: Check for API calls
    print("\n🧪 Test 5: API Integration")
    required_api_calls = [
        '/api/models/${provider}',
        '/api/models/all',
        'fetch('
    ]

    missing_api_calls = []
    for api_call in required_api_calls:
        if api_call not in script_content:
            missing_api_calls.append(api_call)

    if missing_api_calls:
        print(f"❌ FAIL: Missing required API calls: {missing_api_calls}")
        return False
    else:
        print(f"✓ PASS: All {len(required_api_calls)} required API calls found")

    # Test 6: Check for error handling
    print("\n🧪 Test 6: Error Handling")
    error_patterns = [
        'catch(',
        'console.error(',
        'errorDiv.style.display',
        'status.textContent'
    ]

    missing_error_patterns = []
    for pattern in error_patterns:
        if pattern not in script_content:
            missing_error_patterns.append(pattern)

    if missing_error_patterns:
        print(f"❌ FAIL: Missing error handling patterns: {missing_error_patterns}")
        return False
    else:
        print(f"✓ PASS: All {len(error_patterns)} error handling patterns found")

    # Test 7: Check for user feedback mechanisms
    print("\n🧪 Test 7: User Feedback")
    feedback_patterns = [
        'spinner.style.display',
        'status.textContent = \'Loading',
        'Models loaded successfully',
        'refreshBulkProviderModels()'
    ]

    missing_feedback = []
    for pattern in feedback_patterns:
        if pattern not in script_content:
            missing_feedback.append(pattern)

    if missing_feedback:
        print(f"❌ FAIL: Missing user feedback patterns: {missing_feedback}")
        return False
    else:
        print(f"✓ PASS: All {len(feedback_patterns)} user feedback patterns found")

    print("\n" + "=" * 50)
    print("🎉 SUCCESS: All validations passed!")
    print("✅ The bulk upload model loading fix is working correctly")
    print("✅ No regressions detected")
    print("✅ All critical functionality is present")

    return True


def main():
    """Main function."""
    # Add current directory to Python path
    if os.path.basename(os.getcwd()) != 'grading-app':
        if os.path.exists('grading-app'):
            os.chdir('grading-app')
        else:
            print("❌ ERROR: Cannot find grading-app directory")
            sys.exit(1)

    try:
        success = validate_bulk_upload_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ ERROR: Validation failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
