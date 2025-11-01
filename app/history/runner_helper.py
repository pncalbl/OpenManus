"""
History management helper for command-line runners.

This module provides unified functions to handle history-related CLI operations
across different entry points (main.py, run_mcp.py, run_flow.py).
"""

import argparse
from typing import Optional

from app.agent.base import BaseAgent
from app.config import config
from app.history import get_history_manager
from app.history.cli import (
    format_cleanup_result,
    format_session_deleted,
    format_session_list,
    format_session_not_found,
)
from app.logger import logger


class HistoryRunnerHelper:
    """Helper class for managing conversation history in command-line runners."""

    @staticmethod
    def add_history_arguments(parser: argparse.ArgumentParser) -> None:
        """Add history management arguments to an argument parser.

        Args:
            parser: ArgumentParser to add history arguments to
        """
        history_group = parser.add_argument_group("History Management")
        history_group.add_argument(
            "--enable-history",
            action="store_true",
            help="Enable conversation history saving for this session",
        )
        history_group.add_argument(
            "--resume-session",
            "-r",
            type=str,
            metavar="SESSION_ID",
            help="Resume a previous conversation session",
        )
        history_group.add_argument(
            "--list-sessions",
            "-l",
            action="store_true",
            help="List all saved sessions and exit",
        )
        history_group.add_argument(
            "--delete-session",
            type=str,
            metavar="SESSION_ID",
            help="Delete a specific session and exit",
        )
        history_group.add_argument(
            "--cleanup-sessions",
            action="store_true",
            help="Clean up old sessions and exit",
        )
        history_group.add_argument(
            "--limit",
            type=int,
            metavar="N",
            help="Limit number of sessions to display (default: 50)",
        )

    @staticmethod
    async def handle_history_commands(args: argparse.Namespace) -> bool:
        """Handle history management commands that don't require agent initialization.

        Args:
            args: Parsed command line arguments

        Returns:
            True if a history command was handled (should exit), False otherwise
        """
        history_manager = get_history_manager()

        # List sessions
        if hasattr(args, "list_sessions") and args.list_sessions:
            limit = getattr(args, "limit", None) or 50
            sessions = history_manager.list_sessions(limit=limit)
            print(format_session_list(sessions))
            return True

        # Delete session
        if hasattr(args, "delete_session") and args.delete_session:
            if history_manager.delete_session(args.delete_session):
                print(format_session_deleted(args.delete_session))
            else:
                print(format_session_not_found(args.delete_session))
            return True

        # Cleanup old sessions
        if hasattr(args, "cleanup_sessions") and args.cleanup_sessions:
            deleted_count = history_manager.cleanup_old_sessions()
            print(format_cleanup_result(deleted_count))
            return True

        return False

    @staticmethod
    async def setup_session(
        agent: BaseAgent,
        args: argparse.Namespace,
        agent_type_override: Optional[str] = None,
    ) -> bool:
        """Setup conversation session for an agent based on CLI arguments.

        Args:
            agent: The agent to setup session for
            args: Parsed command line arguments
            agent_type_override: Optional agent type name to override the class name

        Returns:
            True if session setup succeeded, False if should exit (e.g., session not found)
        """
        # Check if history should be enabled
        enable_history = getattr(args, "enable_history", False)
        history_enabled = enable_history or config.history_config.enabled

        # Handle session resumption
        resume_session = getattr(args, "resume_session", None)
        if resume_session:
            return await HistoryRunnerHelper._resume_session(agent, resume_session)

        # Create new session if history is enabled and not resuming
        if history_enabled:
            agent_type = agent_type_override or agent.__class__.__name__
            return await HistoryRunnerHelper._create_new_session(agent, agent_type)

        return True

    @staticmethod
    async def _resume_session(agent: BaseAgent, session_id: str) -> bool:
        """Resume a previous conversation session.

        Args:
            agent: The agent to resume session for
            session_id: ID of the session to resume

        Returns:
            True if session was resumed successfully, False if session not found
        """
        history_manager = get_history_manager()
        loaded_memory = history_manager.load_session(session_id)

        if not loaded_memory:
            logger.warning(f"Session {session_id} not found")
            print(f"\n✗ Session not found: {session_id}")
            return False

        agent.memory = loaded_memory
        agent.session_id = session_id
        logger.info(
            f"📖 Resumed session: {session_id} "
            f"with {len(loaded_memory.messages)} messages"
        )
        print(
            f"\n✓ Resumed session: {session_id} "
            f"({len(loaded_memory.messages)} messages)"
        )
        return True

    @staticmethod
    async def _create_new_session(agent: BaseAgent, agent_type: str) -> bool:
        """Create a new conversation session.

        Args:
            agent: The agent to create session for
            agent_type: Type name of the agent

        Returns:
            True (always succeeds)
        """
        history_manager = get_history_manager()
        agent.session_id = history_manager.create_session(
            agent_name=agent.name,
            agent_type=agent_type,
            workspace_path=str(config.workspace_root),
        )
        logger.info(f"📝 Started new session: {agent.session_id}")
        print(f"\n✓ History enabled. Session ID: {agent.session_id}")
        return True
