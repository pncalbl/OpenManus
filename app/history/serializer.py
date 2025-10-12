"""
Serialization utilities for conversation history.
"""

import json
from typing import Dict, List

from app.schema import Memory, Message


class Serializer:
    """Handles serialization and deserialization of conversation sessions."""

    @staticmethod
    def serialize_memory(memory: Memory) -> List[Dict]:
        """
        Convert Memory object to JSON-serializable format.

        Args:
            memory: Memory object containing conversation messages

        Returns:
            List of message dictionaries
        """
        return [msg.to_dict() for msg in memory.messages]

    @staticmethod
    def deserialize_memory(messages_data: List[Dict]) -> Memory:
        """
        Convert JSON data back to Memory object.

        Args:
            messages_data: List of message dictionaries

        Returns:
            Memory object with restored messages
        """
        messages = []
        for msg_dict in messages_data:
            # Reconstruct Message from dict
            message = Message(**msg_dict)
            messages.append(message)

        return Memory(messages=messages)

    @staticmethod
    def serialize_session(session_data: Dict) -> str:
        """
        Serialize complete session data to JSON string.

        Args:
            session_data: Dictionary containing metadata and messages

        Returns:
            JSON string
        """
        return json.dumps(session_data, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def deserialize_session(json_str: str) -> Dict:
        """
        Deserialize JSON string to session data.

        Args:
            json_str: JSON string containing session data

        Returns:
            Dictionary with session data

        Raises:
            json.JSONDecodeError: If JSON is invalid
        """
        return json.loads(json_str)
