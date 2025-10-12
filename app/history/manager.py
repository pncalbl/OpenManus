"""
Core history management functionality.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from app.config import config
from app.history.models import SessionData, SessionMetadata
from app.history.serializer import Serializer
from app.logger import logger
from app.schema import Memory


class HistoryManager:
    """
    Manages conversation history persistence and retrieval.

    Handles saving, loading, listing, and deleting conversation sessions.
    Sessions are stored as JSON files in workspace/history directory.
    """

    def __init__(self):
        """Initialize the history manager."""
        self._serializer = Serializer()
        self._ensure_history_directory()

    def _ensure_history_directory(self) -> None:
        """Create history directory if it doesn't exist."""
        history_dir = self._get_history_directory()
        history_dir.mkdir(parents=True, exist_ok=True)

    def _get_history_directory(self) -> Path:
        """Get the history storage directory path."""
        return config.workspace_root / "history"

    def _generate_session_id(self) -> str:
        """
        Generate a unique session ID.

        Format: session_YYYYMMDD_HHMMSS_<short-uuid>
        Example: session_20250111_143022_a7b3c5d1
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{short_uuid}"

    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session ID."""
        return self._get_history_directory() / f"{session_id}.json"

    def _extract_task_summary(self, memory: Memory) -> Optional[str]:
        """
        Extract a brief task summary from the conversation.

        Uses the first user message as the task summary.

        Args:
            memory: Memory object containing conversation messages

        Returns:
            First 100 characters of initial user message, or None
        """
        for msg in memory.messages:
            if msg.role == "user" and msg.content:
                summary = msg.content.strip()
                return summary[:100] + "..." if len(summary) > 100 else summary
        return None

    def create_session(
        self, agent_name: str, agent_type: str, workspace_path: Optional[str] = None
    ) -> str:
        """
        Create a new session and return its ID.

        Args:
            agent_name: Name of the agent
            agent_type: Type of agent (e.g., "Manus", "MCPAgent")
            workspace_path: Optional workspace path

        Returns:
            Generated session ID
        """
        session_id = self._generate_session_id()
        logger.info(f"Created new session: {session_id}")
        return session_id

    def save_session(
        self,
        session_id: str,
        memory: Memory,
        agent_name: str,
        agent_type: str,
        workspace_path: Optional[str] = None,
    ) -> bool:
        """
        Save a conversation session to disk.

        Args:
            session_id: Unique session identifier
            memory: Memory object containing conversation messages
            agent_name: Name of the agent
            agent_type: Type of agent
            workspace_path: Optional workspace path

        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Check if history is enabled
            if hasattr(config, "history_config") and not config.history_config.enabled:
                logger.debug("History is disabled, skipping save")
                return False

            # Create metadata
            now = datetime.now()
            metadata = SessionMetadata(
                session_id=session_id,
                created_at=now,
                updated_at=now,
                agent_name=agent_name,
                agent_type=agent_type,
                message_count=len(memory.messages),
                task_summary=self._extract_task_summary(memory),
                workspace_path=workspace_path or str(config.workspace_root),
            )

            # Serialize messages
            messages_data = self._serializer.serialize_memory(memory)

            # Create session data
            session_data = SessionData(metadata=metadata, messages=messages_data)

            # Serialize to JSON
            json_str = self._serializer.serialize_session(session_data.dict())

            # Write to file (atomic write via temp file)
            file_path = self._get_session_path(session_id)
            temp_path = file_path.with_suffix(".tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(json_str)

            # Atomic rename
            temp_path.replace(file_path)

            logger.info(
                f"Saved session {session_id} with {len(memory.messages)} messages"
            )

            # Auto-cleanup if enabled
            if hasattr(config, "history_config") and config.history_config.auto_cleanup:
                self.cleanup_old_sessions()

            return True

        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            return False

    def load_session(self, session_id: str) -> Optional[Memory]:
        """
        Load a conversation session from disk.

        Args:
            session_id: Session identifier to load

        Returns:
            Memory object with restored messages, or None if not found

        Raises:
            ValueError: If session file is corrupted
        """
        try:
            file_path = self._get_session_path(session_id)

            if not file_path.exists():
                logger.warning(f"Session {session_id} not found")
                return None

            # Read session file
            with open(file_path, "r", encoding="utf-8") as f:
                json_str = f.read()

            # Deserialize
            session_data = self._serializer.deserialize_session(json_str)

            # Restore memory
            memory = self._serializer.deserialize_memory(session_data["messages"])

            logger.info(
                f"Loaded session {session_id} with {len(memory.messages)} messages"
            )
            return memory

        except json.JSONDecodeError as e:
            logger.error(f"Corrupted session file {session_id}: {e}")
            raise ValueError(f"Session file is corrupted: {session_id}")
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def list_sessions(self, limit: int = 50) -> List[SessionMetadata]:
        """
        List all available sessions.

        Args:
            limit: Maximum number of sessions to return (default: 50)

        Returns:
            List of SessionMetadata objects, sorted by creation time (newest first)
        """
        sessions = []
        history_dir = self._get_history_directory()

        try:
            for file_path in history_dir.glob("session_*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Parse metadata
                    metadata_dict = data.get("metadata", {})
                    metadata_dict["created_at"] = datetime.fromisoformat(
                        metadata_dict["created_at"]
                    )
                    metadata_dict["updated_at"] = datetime.fromisoformat(
                        metadata_dict["updated_at"]
                    )

                    metadata = SessionMetadata(**metadata_dict)
                    sessions.append(metadata)

                except Exception as e:
                    logger.warning(f"Failed to read session {file_path.name}: {e}")
                    continue

            # Sort by creation time (newest first)
            sessions.sort(key=lambda s: s.created_at, reverse=True)

            return sessions[:limit]

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session.

        Args:
            session_id: Session identifier to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            file_path = self._get_session_path(session_id)

            if not file_path.exists():
                logger.warning(f"Session {session_id} not found for deletion")
                return False

            file_path.unlink()
            logger.info(f"Deleted session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def cleanup_old_sessions(self, retention_days: Optional[int] = None) -> int:
        """
        Remove sessions older than retention period.

        Args:
            retention_days: Days to keep (uses config if not specified)

        Returns:
            Number of sessions deleted
        """
        try:
            # Get retention period from config
            if retention_days is None:
                if hasattr(config, "history_config"):
                    retention_days = config.history_config.retention_days
                else:
                    retention_days = 30  # Default

            if retention_days <= 0:
                logger.debug("Retention days is 0, skipping cleanup")
                return 0

            cutoff_date = datetime.now() - timedelta(days=retention_days)
            deleted_count = 0

            # List and check each session
            sessions = self.list_sessions(limit=1000)  # Check all sessions
            for session in sessions:
                if session.created_at < cutoff_date:
                    if self.delete_session(session.session_id):
                        deleted_count += 1

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} sessions older than {retention_days} days"
                )

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0

    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: Session identifier to check

        Returns:
            True if session exists, False otherwise
        """
        return self._get_session_path(session_id).exists()
