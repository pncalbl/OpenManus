"""
Test script for conversation history functionality.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.history import HistoryManager
from app.schema import Memory, Message


def test_history_manager():
    """Test the HistoryManager functionality."""
    print("=" * 60)
    print("Testing OpenManus Conversation History System")
    print("=" * 60)

    # Initialize manager
    print("\n1. Initializing HistoryManager...")
    manager = HistoryManager()
    print("   ✓ Manager initialized")

    # Create test memory with messages
    print("\n2. Creating test conversation memory...")
    memory = Memory()
    memory.add_message(Message.user_message("Hello, can you help me?"))
    memory.add_message(
        Message.assistant_message("Of course! I'd be happy to help. What do you need?")
    )
    memory.add_message(
        Message.user_message("I need to analyze some data from a CSV file")
    )
    memory.add_message(
        Message.assistant_message(
            "I can help with that. Please provide the CSV file path."
        )
    )
    print(f"   ✓ Created memory with {len(memory.messages)} messages")

    # Create session
    print("\n3. Creating new session...")
    session_id = manager.create_session(
        agent_name="Manus", agent_type="Manus", workspace_path="/test/workspace"
    )
    print(f"   ✓ Session created: {session_id}")

    # Save session
    print("\n4. Saving session to disk...")
    success = manager.save_session(
        session_id=session_id,
        memory=memory,
        agent_name="Manus",
        agent_type="Manus",
        workspace_path="/test/workspace",
    )
    if success:
        print(f"   ✓ Session saved successfully")
    else:
        print(f"   ✗ Failed to save session")
        return False

    # Verify file exists
    session_path = manager._get_session_path(session_id)
    if session_path.exists():
        size = session_path.stat().st_size
        print(f"   ✓ Session file created: {session_path.name} ({size} bytes)")
    else:
        print(f"   ✗ Session file not found")
        return False

    # Load session
    print("\n5. Loading session from disk...")
    loaded_memory = manager.load_session(session_id)
    if loaded_memory:
        print(f"   ✓ Session loaded successfully")
        print(f"   ✓ Restored {len(loaded_memory.messages)} messages")

        # Verify messages match
        if len(loaded_memory.messages) == len(memory.messages):
            print(f"   ✓ Message count matches")
        else:
            print(
                f"   ✗ Message count mismatch: {len(loaded_memory.messages)} vs {len(memory.messages)}"
            )
            return False

        # Check first message content
        if (
            loaded_memory.messages[0].content == memory.messages[0].content
            and loaded_memory.messages[0].role == memory.messages[0].role
        ):
            print(f"   ✓ Message content verified")
        else:
            print(f"   ✗ Message content mismatch")
            return False
    else:
        print(f"   ✗ Failed to load session")
        return False

    # List sessions
    print("\n6. Listing all sessions...")
    sessions = manager.list_sessions()
    print(f"   ✓ Found {len(sessions)} session(s)")
    if sessions:
        for session in sessions:
            print(f"   - {session.session_id}")
            print(f"     Agent: {session.agent_name} ({session.agent_type})")
            print(f"     Messages: {session.message_count}")
            print(f"     Created: {session.created_at}")
            print(f"     Task: {session.task_summary}")

    # Test session exists
    print("\n7. Testing session existence check...")
    if manager.session_exists(session_id):
        print(f"   ✓ Session exists check passed")
    else:
        print(f"   ✗ Session exists check failed")
        return False

    # Delete session
    print("\n8. Deleting test session...")
    if manager.delete_session(session_id):
        print(f"   ✓ Session deleted successfully")

        # Verify deletion
        if not session_path.exists():
            print(f"   ✓ Session file removed")
        else:
            print(f"   ✗ Session file still exists")
            return False
    else:
        print(f"   ✗ Failed to delete session")
        return False

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_history_manager()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
