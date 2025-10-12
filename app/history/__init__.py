"""
Conversation history management module.

This module provides functionality to save, load, and manage conversation history
for OpenManus agents. Sessions are stored as JSON files in the workspace/history directory.
"""

from app.history.manager import HistoryManager
from app.history.models import SessionMetadata

__all__ = ["HistoryManager", "SessionMetadata", "get_history_manager"]

# Lazy initialization of history manager
_history_manager_instance = None


def get_history_manager() -> HistoryManager:
    """
    Get or create the global history manager instance.

    Returns:
        HistoryManager instance
    """
    global _history_manager_instance
    if _history_manager_instance is None:
        _history_manager_instance = HistoryManager()
    return _history_manager_instance

