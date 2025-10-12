"""
Simplified test script for conversation history functionality.
Tests history manager without full config dependencies.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.schema import Memory, Message


def test_serialization():
    """Test message serialization and deserialization."""
    print("=" * 60)
    print("Testing Conversation History - Serialization")
    print("=" * 60)

    # Import serializer
    from app.history.serializer import Serializer

    print("\n1. Creating test memory...")
    memory = Memory()
    memory.add_message(Message.user_message("Hello, can you help me?"))
    memory.add_message(
        Message.assistant_message("Of course! I'd be happy to help. What do you need?")
    )
    memory.add_message(
        Message.user_message("I need to analyze some data from a CSV file")
    )
    print(f"   ✓ Created memory with {len(memory.messages)} messages")

    print("\n2. Serializing memory...")
    serializer = Serializer()
    messages_data = serializer.serialize_memory(memory)
    print(f"   ✓ Serialized {len(messages_data)} messages")
    print(f"   Sample message: {messages_data[0]}")

    print("\n3. Deserializing memory...")
    restored_memory = serializer.deserialize_memory(messages_data)
    print(f"   ✓ Deserialized {len(restored_memory.messages)} messages")

    print("\n4. Verifying data integrity...")
    if len(restored_memory.messages) == len(memory.messages):
        print(f"   ✓ Message count matches")
    else:
        print(f"   ✗ Message count mismatch")
        return False

    for i, (original, restored) in enumerate(
        zip(memory.messages, restored_memory.messages)
    ):
        if original.role == restored.role and original.content == restored.content:
            print(f"   ✓ Message {i+1} verified")
        else:
            print(f"   ✗ Message {i+1} mismatch")
            return False

    print("\n5. Testing full session serialization...")
    session_data = {
        "metadata": {
            "session_id": f"session_test_{uuid4().hex[:8]}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "agent_name": "TestAgent",
            "agent_type": "Manus",
            "message_count": len(messages_data),
            "task_summary": "Test conversation",
            "workspace_path": "/test/workspace",
        },
        "messages": messages_data,
    }

    json_str = serializer.serialize_session(session_data)
    print(f"   ✓ Session serialized to JSON ({len(json_str)} chars)")

    restored_session = serializer.deserialize_session(json_str)
    print(f"   ✓ Session deserialized successfully")

    if restored_session["metadata"]["agent_name"] == "TestAgent":
        print(f"   ✓ Metadata verified")
    else:
        print(f"   ✗ Metadata mismatch")
        return False

    print("\n" + "=" * 60)
    print("✓ All serialization tests passed!")
    print("=" * 60)
    return True


def test_session_metadata():
    """Test SessionMetadata model."""
    print("\n" + "=" * 60)
    print("Testing Conversation History - Models")
    print("=" * 60)

    from app.history.models import SessionData, SessionMetadata

    print("\n1. Creating SessionMetadata...")
    metadata = SessionMetadata(
        session_id="session_20250112_test123",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        agent_name="Manus",
        agent_type="Manus",
        message_count=5,
        task_summary="Test task summary",
        workspace_path="/test/workspace",
    )
    print(f"   ✓ Created metadata: {metadata.session_id}")

    print("\n2. Testing metadata serialization...")
    metadata_dict = metadata.model_dump()
    print(f"   ✓ Converted to dict: {list(metadata_dict.keys())}")

    print("\n3. Creating SessionData...")
    session_data = SessionData(
        metadata=metadata, messages=[{"role": "user", "content": "test"}]
    )
    print(f"   ✓ Created session data with {len(session_data.messages)} message(s)")

    print("\n" + "=" * 60)
    print("✓ All model tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        # Test serialization
        if not test_serialization():
            sys.exit(1)

        # Test models
        if not test_session_metadata():
            sys.exit(1)

        print("\n" + "=" * 60)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("=" * 60)
        print("\nCore history functionality is working correctly.")
        print("Next steps:")
        print("  1. Create/copy config.toml from config.example.toml")
        print("  2. Enable history in config: [history] enabled = true")
        print("  3. Run full integration tests")

        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
