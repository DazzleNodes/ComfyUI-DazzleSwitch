#!/usr/bin/env python
"""
DazzleSwitch test runner.

Runs one-off tests for pre-push validation.
Called by the pre-push git hook automatically.

Usage:
    python run_tests.py          # Run all tests
    python run_tests.py -v       # Verbose output
"""

import subprocess
import sys
import os

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(REPO_ROOT, "tests", "one-offs")


def main():
    args = sys.argv[1:]
    test_files = sorted(
        f for f in os.listdir(TEST_DIR)
        if f.startswith("test_") and f.endswith(".py")
    )

    if not test_files:
        print("No test files found in tests/one-offs/")
        return 0

    failed = 0
    for test_file in test_files:
        path = os.path.join(TEST_DIR, test_file)
        result = subprocess.run(
            [sys.executable, path] + args,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            failed += 1

    if failed:
        print(f"\n{failed} test file(s) failed.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
