"""
Tests for HistoryManager

Unit tests for conversation history management including session creation,
saving, loading, and cleanup.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.history.manager import HistoryManager
from app.history.models import SessionMetadata
from app.schema import Memory, Message


class TestHistoryManager:
    """Test HistoryManager functionality"""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_workspace):
        """Create a HistoryManager with temporary workspace"""
        with patch("app.history.manager.config") as mock_config:
            mock_config.workspace_root = temp_workspace
            mock_config.history_config.enabled = True
            mock_config.history_config.auto_cleanup = False
            mock_config.history_config.retention_days = 30
            manager = HistoryManager()
            return manager

    @pytest.fixture
    def sample_memory(self):
        """Create sample memory with messages"""
        memory = Memory()
        memory.add_message(Message.user_message("Hello, can you help me?"))
        memory.add_message(Message.assistant_message("Of course! How can I help?"))
        memory.add_message(Message.user_message("I need to write some code"))
        return memory

    def test_initialization(self, manager):
        """Test manager initialization creates history directory"""
        history_dir = manager._get_history_directory()
        assert history_dir.exists()
        assert history_dir.is_dir()

    def test_generate_session_id(self, manager):
        """Test session ID generation format"""
        session_id = manager._generate_session_id()

        # Should match format: session_YYYYMMDD_HHMMSS_<uuid>
        assert session_id.startswith("session_")
        parts = session_id.split("_")
        assert len(parts) == 4
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 8  # short UUID

    def test_generate_unique_session_ids(self, manager):
        """Test that generated session IDs are unique"""
        ids = [manager._generate_session_id() for _ in range(10)]
        assert len(ids) == len(set(ids))  # All should be unique

    def test_create_session(self, manager):
        """Test session creation"""
        session_id = manager.create_session(
            agent_name="test_agent", agent_type="TestAgent"
        )

        assert session_id.startswith("session_")

    def test_save_session(self, manager, sample_memory):
        """Test saving a session to disk"""
        session_id = manager.create_session(
            agent_name="test_agent", agent_type="TestAgent"
        )

        success = manager.save_session(
            session_id=session_id,
            memory=sample_memory,
            agent_name="test_agent",
            agent_type="TestAgent",
        )

        assert success is True

        # Verify file was created
        session_path = manager._get_session_path(session_id)
        assert session_path.exists()

    def test_save_session_creates_valid_json(self, manager, sample_memory):
        """Test that saved session is valid JSON"""
        session_id = manager.create_session(
            agent_name="test_agent", agent_type="TestAgent"
        )

        manager.save_session(
            session_id=session_id,
            memory=sample_memory,
            agent_name="test_agent",
            agent_type="TestAgent",
        )

        # Load and verify JSON structure
        session_path = manager._get_session_path(session_id)
        with open(session_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "messages" in data
        assert data["metadata"]["session_id"] == session_id
        assert data["metadata"]["agent_name"] == "test_agent"
        assert data["metadata"]["message_count"] == 3

    def test_load_session(self, manager, sample_memory):
        """Test loading a session from disk"""
        # Create and save session
        session_id = manager.create_session(
            agent_name="test_agent", agent_type="TestAgent"
        )
        manager.save_session(
            session_id=session_id,
            memory=sample_memory,
            agent_name="test_agent",
            agent_type="TestAgent",
        )

        # Load session
        loaded_memory = manager.load_session(session_id)

        assert loaded_memory is not None
        assert len(loaded_memory.messages) == len(sample_memory.messages)
        assert loaded_memory.messages[0].content == sample_memory.messages[0].content

    def test_load_nonexistent_session(self, manager):
        """Test loading a session that doesn't exist"""
        loaded_memory = manager.load_session("nonexistent_session_id")
        assert loaded_memory is None

    def test_load_corrupted_session(self, manager):
        """Test loading a corrupted session file"""
        session_id = "session_corrupted_123"
        session_path = manager._get_session_path(session_id)

        # Create corrupted JSON file
        with open(session_path, "w", encoding="utf-8") as f:
            f.write("{invalid json}")

        with pytest.raises(ValueError, match="corrupted"):
            manager.load_session(session_id)

    def test_list_sessions_empty(self, manager):
        """Test listing sessions when none exist"""
        sessions = manager.list_sessions()
        assert sessions == []

    def test_list_sessions(self, manager, sample_memory):
        """Test listing multiple sessions"""
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session_id = manager.create_session(
                agent_name=f"agent_{i}", agent_type="TestAgent"
            )
            manager.save_session(
                session_id=session_id,
                memory=sample_memory,
                agent_name=f"agent_{i}",
                agent_type="TestAgent",
            )
            session_ids.append(session_id)

        # List sessions
        sessions = manager.list_sessions()

        assert len(sessions) == 3
        assert all(isinstance(s, SessionMetadata) for s in sessions)

        # Should be sorted by creation time (newest first)
        created_times = [s.created_at for s in sessions]
        assert created_times == sorted(created_times, reverse=True)

    def test_list_sessions_with_limit(self, manager, sample_memory):
        """Test listing sessions with limit"""
        # Create 5 sessions
        for i in range(5):
            session_id = manager.create_session(
                agent_name=f"agent_{i}", agent_type="TestAgent"
            )
            manager.save_session(
                session_id=session_id,
                memory=sample_memory,
                agent_name=f"agent_{i}",
                agent_type="TestAgent",
            )

        # List with limit
        sessions = manager.list_sessions(limit=3)
        assert len(sessions) == 3

    def test_delete_session(self, manager, sample_memory):
        """Test deleting a session"""
        # Create session
        session_id = manager.create_session(
            agent_name="test_agent", agent_type="TestAgent"
        )
        manager.save_session(
            session_id=session_id,
            memory=sample_memory,
            agent_name="test_agent",
            agent_type="TestAgent",
        )

        # Verify it exists
        assert manager.session_exists(session_id)

        # Delete it
        success = manager.delete_session(session_id)
        assert success is True

        # Verify it's gone
        assert not manager.session_exists(session_id)

    def test_delete_nonexistent_session(self, manager):
        """Test deleting a session that doesn't exist"""
        success = manager.delete_session("nonexistent_session")
        assert success is False

    def test_session_exists(self, manager, sample_memory):
        """Test checking session existence"""
        session_id = manager.create_session(
            agent_name="test_agent", agent_type="TestAgent"
        )

        # Should not exist before saving
        assert not manager.session_exists(session_id)

        # Save it
        manager.save_session(
            session_id=session_id,
            memory=sample_memory,
            agent_name="test_agent",
            agent_type="TestAgent",
        )

        # Should exist now
        assert manager.session_exists(session_id)

    def test_cleanup_old_sessions(self, manager, sample_memory):
        """Test cleanup of old sessions"""
        # Create an old session by modifying its timestamp
        old_session_id = manager.create_session(
            agent_name="old_agent", agent_type="TestAgent"
        )
        manager.save_session(
            session_id=old_session_id,
            memory=sample_memory,
            agent_name="old_agent",
            agent_type="TestAgent",
        )

        # Manually modify the file timestamp to make it old
        old_date = datetime.now() - timedelta(days=40)
        session_path = manager._get_session_path(old_session_id)

        # Reload and modify the session to have old timestamp
        with open(session_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["metadata"]["created_at"] = old_date.isoformat()
        data["metadata"]["updated_at"] = old_date.isoformat()

        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Create a recent session
        recent_session_id = manager.create_session(
            agent_name="recent_agent", agent_type="TestAgent"
        )
        manager.save_session(
            session_id=recent_session_id,
            memory=sample_memory,
            agent_name="recent_agent",
            agent_type="TestAgent",
        )

        # Cleanup sessions older than 30 days
        deleted_count = manager.cleanup_old_sessions(retention_days=30)

        assert deleted_count == 1
        assert not manager.session_exists(old_session_id)
        assert manager.session_exists(recent_session_id)

    def test_cleanup_with_zero_retention(self, manager):
        """Test cleanup with zero retention days (should skip)"""
        deleted_count = manager.cleanup_old_sessions(retention_days=0)
        assert deleted_count == 0

    def test_extract_task_summary(self, manager):
        """Test extracting task summary from memory"""
        memory = Memory()
        memory.add_message(Message.user_message("This is a test task"))

        summary = manager._extract_task_summary(memory)
        assert summary == "This is a test task"

    def test_extract_task_summary_long_message(self, manager):
        """Test task summary truncation for long messages"""
        memory = Memory()
        long_message = "A" * 150  # More than 100 characters
        memory.add_message(Message.user_message(long_message))

        summary = manager._extract_task_summary(memory)
        assert len(summary) <= 103  # 100 + "..."
        assert summary.endswith("...")

    def test_extract_task_summary_no_user_message(self, manager):
        """Test task summary when no user message exists"""
        memory = Memory()
        memory.add_message(Message.assistant_message("Only assistant message"))

        summary = manager._extract_task_summary(memory)
        assert summary is None

    def test_save_with_disabled_history(self, manager, sample_memory):
        """Test saving when history is disabled"""
        with patch("app.history.manager.config") as mock_config:
            mock_config.history_config.enabled = False

            session_id = manager.create_session(
                agent_name="test_agent", agent_type="TestAgent"
            )
            success = manager.save_session(
                session_id=session_id,
                memory=sample_memory,
                agent_name="test_agent",
                agent_type="TestAgent",
            )

            assert success is False

    def test_save_with_workspace_path(self, manager, sample_memory):
        """Test saving session with custom workspace path"""
        session_id = manager.create_session(
            agent_name="test_agent",
            agent_type="TestAgent",
            workspace_path="/custom/path",
        )

        manager.save_session(
            session_id=session_id,
            memory=sample_memory,
            agent_name="test_agent",
            agent_type="TestAgent",
            workspace_path="/custom/path",
        )

        # Load and verify workspace path
        session_path = manager._get_session_path(session_id)
        with open(session_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"]["workspace_path"] == "/custom/path"

    def test_atomic_write(self, manager, sample_memory):
        """Test that save uses atomic write (temp file + rename)"""
        session_id = manager.create_session(
            agent_name="test_agent", agent_type="TestAgent"
        )

        session_path = manager._get_session_path(session_id)
        temp_path = session_path.with_suffix(".tmp")

        # Ensure temp file doesn't exist before save
        if temp_path.exists():
            temp_path.unlink()

        manager.save_session(
            session_id=session_id,
            memory=sample_memory,
            agent_name="test_agent",
            agent_type="TestAgent",
        )

        # After successful save, temp file should not exist
        assert not temp_path.exists()
        # But final file should exist
        assert session_path.exists()

    def test_concurrent_session_creation(self, manager):
        """Test that concurrent session creations produce unique IDs"""
        import concurrent.futures

        def create_session():
            return manager.create_session(
                agent_name="test_agent", agent_type="TestAgent"
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_session) for _ in range(10)]
            session_ids = [f.result() for f in futures]

        # All session IDs should be unique
        assert len(session_ids) == len(set(session_ids))
