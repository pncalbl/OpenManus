#!/usr/bin/env python
"""Basic test for history module functionality."""

import sys
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all history modules can be imported."""
    print("Testing imports...")

    try:
        from app.history import get_history_manager, SessionMetadata
        print("[OK] app.history imports successful")

        from app.history.models import SessionData
        print("[OK] app.history.models imports successful")

        from app.history.serializer import Serializer
        print("[OK] app.history.serializer imports successful")

        from app.history.manager import HistoryManager
        print("[OK] app.history.manager imports successful")

        from app.history.cli import (
            format_session_list,
            format_session_deleted,
            format_session_not_found,
            format_cleanup_result
        )
        print("[OK] app.history.cli imports successful")

        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_history_manager():
    """Test basic HistoryManager functionality."""
    print("\nTesting HistoryManager...")

    try:
        from app.history import get_history_manager

        # Get manager instance
        manager = get_history_manager()
        print(f"[OK] Created HistoryManager: {manager}")

        # Test session listing (should work even if empty)
        sessions = manager.list_sessions()
        print(f"[OK] Listed sessions: {len(sessions)} found")

        # Test cleanup (should work even if empty)
        deleted = manager.cleanup_old_sessions()
        print(f"[OK] Cleanup old sessions: {deleted} deleted")

        return True
    except Exception as e:
        print(f"[FAIL] HistoryManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_formatters():
    """Test CLI formatting functions."""
    print("\nTesting CLI formatters...")

    try:
        from app.history.cli import (
            format_session_list,
            format_session_deleted,
            format_session_not_found,
            format_cleanup_result
        )
        from app.history.models import SessionMetadata
        from datetime import datetime

        # Test empty session list
        result = format_session_list([])
        print(f"[OK] Empty session list: {result.splitlines()[0]}")

        # Test session list with data
        test_session = SessionMetadata(
            session_id="test_session_123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            agent_name="TestAgent",
            agent_type="TestType",
            message_count=5,
            task_summary="Test task"
        )
        result = format_session_list([test_session])
        print(f"[OK] Session list with data: {len(result.splitlines())} lines")

        # Test other formatters
        print(f"[OK] Session deleted: {format_session_deleted('test_123')}")
        print(f"[OK] Session not found: {format_session_not_found('test_123')}")
        print(f"[OK] Cleanup result (0): {format_cleanup_result(0)}")
        print(f"[OK] Cleanup result (5): {format_cleanup_result(5)}")

        return True
    except Exception as e:
        print(f"[FAIL] CLI formatter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all basic tests."""
    print("="*60)
    print("History Module Basic Tests")
    print("="*60)

    results = []

    # Run tests
    results.append(("Import test", test_imports()))
    results.append(("HistoryManager test", test_history_manager()))
    results.append(("CLI formatter test", test_cli_formatters()))

    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
