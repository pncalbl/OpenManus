"""
CLI utilities for history management.
"""

from typing import List

from app.history.models import SessionMetadata


def format_session_list(sessions: List[SessionMetadata]) -> str:
    """
    Format a list of sessions for display in the terminal.

    Args:
        sessions: List of SessionMetadata objects

    Returns:
        Formatted string ready for printing
    """
    if not sessions:
        return "No saved sessions found."

    # Build table
    lines = []
    lines.append("=" * 100)
    lines.append("Available Conversation Sessions")
    lines.append("=" * 100)

    # Header
    header = (
        f"{'Session ID':<35} {'Agent':<12} {'Messages':<10} {'Created':<20} {'Task'}"
    )
    lines.append(header)
    lines.append("-" * 100)

    # Rows
    for session in sessions:
        created = session.created_at.strftime("%Y-%m-%d %H:%M:%S")
        task = session.task_summary or "(No task summary)"
        if len(task) > 30:
            task = task[:27] + "..."

        row = f"{session.session_id:<35} {session.agent_name:<12} {session.message_count:<10} {created:<20} {task}"
        lines.append(row)

    lines.append("=" * 100)
    lines.append(f"Total: {len(sessions)} session(s)")

    return "\n".join(lines)


def format_session_deleted(session_id: str) -> str:
    """Format a session deletion confirmation message."""
    return f"[OK] Session deleted: {session_id}"


def format_session_not_found(session_id: str) -> str:
    """Format a session not found error message."""
    return f"[ERROR] Session not found: {session_id}"


def format_cleanup_result(deleted_count: int) -> str:
    """Format cleanup operation result."""
    if deleted_count == 0:
        return "No old sessions to clean up."
    elif deleted_count == 1:
        return "[OK] Cleaned up 1 old session."
    else:
        return f"[OK] Cleaned up {deleted_count} old sessions."
