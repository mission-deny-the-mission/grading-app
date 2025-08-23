#!/usr/bin/env python3
"""
Master test runner for all model validation tests.
Runs comprehensive validation of all model options in dropdown menus.
"""

import subprocess
import sys
import os

def run_test_script(script_name, description):
    """Run a test script and return success status."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print('='*60)
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        
        success = result.returncode == 0
        if success:
            print(f"\n✅ {description} - PASSED")
        else:
            print(f"\n❌ {description} - FAILED (exit code: {result.returncode})")
        
        return success
        
    except Exception as e:
        print(f"\n💥 {description} - ERROR: {e}")
        return False

def main():
    """Run all model validation tests in sequence."""
    print("🎯 COMPREHENSIVE MODEL VALIDATION TEST SUITE")
    print("="*60)
    print("This test suite validates all model options in dropdown menus")
    print("and ensures consistency between GUI display names and backend model names.")
    print()
    
    # Define test scripts and descriptions
    test_suite = [
        ("test_critical_models.py", "Critical Model Name Consistency"),
        ("test_model_backend_integration.py", "Backend Integration & Format Validation"),
        ("test_model_validation.py", "Comprehensive Model Options Analysis")
    ]
    
    # Run all tests
    results = []
    for script, description in test_suite:
        success = run_test_script(script, description)
        results.append((description, success))
    
    # Final summary
    print("\n" + "="*60)
    print("📊 FINAL MODEL VALIDATION SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {description}")
    
    print(f"\nOverall Result: {passed_tests}/{total_tests} test suites passed")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL MODEL VALIDATION TESTS PASSED!")
        print("✅ All dropdown model options are valid")
        print("✅ GUI display names match backend model names")
        print("✅ Model naming follows expected patterns")
        print("✅ Configuration save/load works correctly")
        print("✅ Backend integration is properly implemented")
        print("\n🚀 The model selection system is ready for production!")
        
        # Additional validation summary
        print("\n📋 VALIDATION COVERAGE:")
        print("   • Configuration page dropdowns (6 providers)")
        print("   • Main interface model selection")
        print("   • Bulk upload interface model selection")
        print("   • Backend model resolution logic")
        print("   • Model name format compliance")
        print("   • Save/load configuration persistence")
        
        return True
    else:
        failed_count = total_tests - passed_tests
        print(f"\n⚠️  {failed_count} test suite(s) failed.")
        print("Please review the detailed output above and fix any issues.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)