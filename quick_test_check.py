#!/usr/bin/env python3
"""
Quick test status check script
"""

import subprocess
import sys
import os


def run_test_category(test_path, description):
    """Run a specific test category and return results."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {description}")
    print(f"Path: {test_path}")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-x", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/home/harry/grading-app-main",
        )

        if result.returncode == 0:
            print(f"✅ {description}: ALL PASSED")
            return True
        else:
            print(f"❌ {description}: FAILURES DETECTED")
            print(
                "STDOUT:",
                result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
            )
            print(
                "STDERR:",
                result.stderr[-500:] if len(result.stderr) > 500 else result.stderr,
            )
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {description}: TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description}: ERROR - {e}")
        return False


def main():
    """Check status of major test categories."""
    os.chdir("/home/harry/grading-app-main")

    test_categories = [
        ("tests/unit/test_permission_checker.py", "Permission Checker Tests"),
        ("tests/test_encryption.py", "Encryption Tests"),
        ("tests/test_tasks.py", "Task Processing Tests"),
        ("tests/integration/test_document_upload_flow.py", "Document Upload Tests"),
        ("tests/test_desktop/test_credentials.py", "Desktop Credential Tests"),
    ]

    results = {}
    for test_path, description in test_categories:
        results[description] = run_test_category(test_path, description)

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for description, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {description}")

    print(f"\nOverall: {passed}/{total} test categories passing")

    if passed == total:
        print("🎉 All major test categories are passing!")
        return 0
    else:
        print("⚠️  Some test categories still have failures")
        return 1


if __name__ == "__main__":
    sys.exit(main())
