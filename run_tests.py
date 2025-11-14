#!/usr/bin/env python3
"""
Test runner script for the grading app.
"""

import argparse
import os
import subprocess
import sys


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {description}:")
        print(f"Return code: {e.returncode}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def run_unit_tests():
    """Run unit tests."""
    return run_command(
        [sys.executable, "-m", "pytest", "tests/", "-m", "unit", "-v"], "Unit Tests"
    )


def run_integration_tests():
    """Run integration tests."""
    return run_command(
        [sys.executable, "-m", "pytest", "tests/", "-m", "integration", "-v"],
        "Integration Tests",
    )


def run_api_tests():
    """Run API tests."""
    return run_command(
        [sys.executable, "-m", "pytest", "tests/", "-m", "api", "-v"], "API Tests"
    )


def run_database_tests():
    """Run database tests."""
    return run_command(
        [sys.executable, "-m", "pytest", "tests/", "-m", "database", "-v"],
        "Database Tests",
    )


def run_celery_tests():
    """Run Celery task tests."""
    return run_command(
        [sys.executable, "-m", "pytest", "tests/", "-m", "celery", "-v"],
        "Celery Task Tests",
    )


def run_all_tests():
    """Run all tests."""
    return run_command([sys.executable, "-m", "pytest", "tests/", "-v"], "All Tests")


def run_tests_with_coverage():
    """Run tests with coverage report."""
    return run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=app",
            "--cov=models",
            "--cov=tasks",
            "--cov-report=html",
            "--cov-report=term-missing",
        ],
        "Tests with Coverage",
    )


def run_specific_test_file(test_file):
    """Run a specific test file."""
    if not os.path.exists(test_file):
        print(f"Test file {test_file} not found!")
        return False

    return run_command(
        [sys.executable, "-m", "pytest", test_file, "-v"],
        f"Specific Test File: {test_file}",
    )


def run_specific_test_class(test_class):
    """Run a specific test class."""
    return run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            f"tests/test_{test_class}.py::Test{test_class}",
            "-v",
        ],
        f"Specific Test Class: {test_class}",
    )


def run_fast_tests():
    """Run only fast tests (exclude slow tests)."""
    return run_command(
        [sys.executable, "-m", "pytest", "tests/", "-m", "not slow", "-v"],
        "Fast Tests (excluding slow tests)",
    )


def run_linting():
    """Run code linting."""
    return run_command(
        [sys.executable, "-m", "flake8", "app.py", "models.py", "tasks.py", "tests/"],
        "Code Linting",
    )


def run_type_checking():
    """Run type checking (if mypy is available)."""
    try:
        pass

        return run_command(
            [sys.executable, "-m", "mypy", "app.py", "models.py", "tasks.py"],
            "Type Checking",
        )
    except ImportError:
        print("mypy not installed. Skipping type checking.")
        return True


def main():
    """Main function to run tests based on command line arguments."""
    parser = argparse.ArgumentParser(description="Run tests for the grading app")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "api", "database", "celery", "all", "fast"],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage report"
    )
    parser.add_argument("--file", type=str, help="Run a specific test file")
    parser.add_argument(
        "--class", type=str, dest="test_class", help="Run a specific test class"
    )
    parser.add_argument("--lint", action="store_true", help="Run code linting")
    parser.add_argument("--type-check", action="store_true", help="Run type checking")
    parser.add_argument(
        "--all-checks",
        action="store_true",
        help="Run all checks (tests, linting, type checking)",
    )

    args = parser.parse_args()

    # Ensure we're in the right directory
    if not os.path.exists("app.py"):
        print(
            "Error: app.py not found. Please run this script from the project root directory."
        )
        sys.exit(1)

    # Create tests directory if it doesn't exist
    if not os.path.exists("tests"):
        os.makedirs("tests")
        print("Created tests directory.")

    success = True

    if args.all_checks:
        print("Running all checks...")
        success &= run_linting()
        success &= run_type_checking()
        success &= run_tests_with_coverage()
    elif args.lint:
        success &= run_linting()
    elif args.type_check:
        success &= run_type_checking()
    elif args.coverage:
        success &= run_tests_with_coverage()
    elif args.file:
        success &= run_specific_test_file(args.file)
    elif args.test_class:
        success &= run_specific_test_class(args.test_class)
    else:
        if args.type == "unit":
            success &= run_unit_tests()
        elif args.type == "integration":
            success &= run_integration_tests()
        elif args.type == "api":
            success &= run_api_tests()
        elif args.type == "database":
            success &= run_database_tests()
        elif args.type == "celery":
            success &= run_celery_tests()
        elif args.type == "fast":
            success &= run_fast_tests()
        else:  # all
            success &= run_all_tests()

    print(f"\n{'=' * 60}")
    if success:
        print("✅ All tests passed successfully!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
