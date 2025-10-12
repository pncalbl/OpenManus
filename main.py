import argparse
import asyncio

from app.agent.manus import Manus
from app.config import config
from app.history import get_history_manager
from app.history.cli import (
    format_cleanup_result,
    format_session_deleted,
    format_session_list,
    format_session_not_found,
)
from app.logger import logger


async def handle_history_commands(args):
    """Handle history management commands that don't need agent initialization."""
    history_manager = get_history_manager()

    # List sessions
    if args.list_sessions:
        sessions = history_manager.list_sessions(limit=args.limit or 50)
        print(format_session_list(sessions))
        return True

    # Delete session
    if args.delete_session:
        if history_manager.delete_session(args.delete_session):
            print(format_session_deleted(args.delete_session))
        else:
            print(format_session_not_found(args.delete_session))
        return True

    # Cleanup old sessions
    if args.cleanup_sessions:
        deleted_count = history_manager.cleanup_old_sessions()
        print(format_cleanup_result(deleted_count))
        return True

    return False


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Manus agent with a prompt")
    parser.add_argument(
        "--prompt", type=str, required=False, help="Input prompt for the agent"
    )

    # History management arguments
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

    args = parser.parse_args()

    # Handle history commands that don't need agent
    if await handle_history_commands(args):
        return

    # Create and initialize Manus agent
    agent = await Manus.create()

    try:
        # Check if history should be enabled
        history_enabled = args.enable_history or config.history_config.enabled

        # Handle session resumption
        if args.resume_session:
            history_manager = get_history_manager()
            loaded_memory = history_manager.load_session(args.resume_session)

            if loaded_memory:
                agent.memory = loaded_memory
                agent.session_id = args.resume_session
                logger.info(
                    f"📖 Resumed session: {args.resume_session} with {len(loaded_memory.messages)} messages"
                )
                print(
                    f"\n✓ Resumed session: {args.resume_session} ({len(loaded_memory.messages)} messages)"
                )
            else:
                logger.warning(f"Session {args.resume_session} not found")
                print(f"\n✗ Session not found: {args.resume_session}")
                return

        # Create new session if history is enabled and not resuming
        elif history_enabled:
            history_manager = get_history_manager()
            agent.session_id = history_manager.create_session(
                agent_name=agent.name,
                agent_type=agent.__class__.__name__,
                workspace_path=str(config.workspace_root),
            )
            logger.info(f"📝 Started new session: {agent.session_id}")
            print(f"\n✓ History enabled. Session ID: {agent.session_id}")

        # Use command line prompt if provided, otherwise ask for input
        prompt = args.prompt if args.prompt else input("\nEnter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")

    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    finally:
        # Ensure agent resources are cleaned up before exiting
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
