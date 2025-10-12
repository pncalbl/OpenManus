#!/usr/bin/env python
"""Test script for history CLI functionality."""

import subprocess
import sys


def run_command(cmd: str, description: str):
    """Run a command and print results."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.stdout:
            print("STDOUT:")
            print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"Return code: {result.returncode}")
        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Run all history CLI tests."""
    print("="*60)
    print("History CLI Test Suite")
    print("="*60)

    tests = [
        # Test 1: List sessions (should work even with empty history)
        (f"{sys.executable} main.py --list-sessions", "List all sessions (main.py)"),

        # Test 2: List sessions for MCP
        (f"{sys.executable} run_mcp.py --list-sessions", "List all sessions (run_mcp.py)"),

        # Test 3: List sessions for flow
        (f"{sys.executable} run_flow.py --list-sessions", "List all sessions (run_flow.py)"),

        # Test 4: Cleanup old sessions
        (f"{sys.executable} main.py --cleanup-sessions", "Cleanup old sessions"),

        # Test 5: Show help with history options
        (f"{sys.executable} main.py --help", "Show help with history options"),
    ]

    results = []
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))

    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for description, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {description}")

    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
