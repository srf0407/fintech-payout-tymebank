#!/usr/bin/env python3
"""
Test runner script for the fintech payout system.
Provides easy commands to run different test categories.
"""

import subprocess
import sys
import os


def run_command(cmd):
    """Run a command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode == 0


def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py <test_type>")
        print("Available test types:")
        print("  all          - Run all tests")
        print("  unit         - Run unit tests only")
        print("  integration  - Run integration tests only")
        print("  security     - Run security tests only")
        print("  api          - Run API tests only")
        print("  minimal      - Run only the required minimal tests")
        print("  coverage     - Run all tests with coverage")
        sys.exit(1)
    
    test_type = sys.argv[1].lower()
    
    # Change to the backend directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if test_type == "all":
        success = run_command("python -m pytest app/tests/ -v")
    elif test_type == "unit":
        success = run_command("python -m pytest app/tests/unit/ -v")
    elif test_type == "integration":
        success = run_command("python -m pytest app/tests/integration/ -v")
    elif test_type == "security":
        success = run_command("python -m pytest app/tests/security/ -v")
    elif test_type == "api":
        success = run_command("python -m pytest app/tests/api/ -v")
    elif test_type == "minimal":
        # Run only the required minimal tests
        success = run_command("python -m pytest app/tests/security/test_webhook_security.py::TestWebhookSecurity::test_verify_webhook_signature_hmac_valid -v")
        success &= run_command("python -m pytest app/tests/security/test_webhook_security.py::TestWebhookSecurity::test_verify_webhook_timestamp_too_old -v")
        success &= run_command("python -m pytest app/tests/unit/test_payout_service.py::TestPayoutService::test_create_payout_idempotency -v")
    elif test_type == "coverage":
        success = run_command("python -m pytest app/tests/ --cov=app --cov-report=html --cov-report=term")
    else:
        print(f"Unknown test type: {test_type}")
        sys.exit(1)
    
    if success:
        print(f"\n✅ {test_type.title()} tests passed!")
    else:
        print(f"\n❌ {test_type.title()} tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
