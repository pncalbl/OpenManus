#!/usr/bin/env python
import argparse
import asyncio
import sys

from app.agent.mcp import MCPAgent
from app.config import config
from app.history import get_history_manager
from app.history.cli import (
    format_cleanup_result,
    format_session_deleted,
    format_session_list,
    format_session_not_found,
)
from app.logger import logger


class MCPRunner:
    """Runner class for MCP Agent with proper path handling and configuration."""

    def __init__(self):
        self.root_path = config.root_path
        self.server_reference = config.mcp_config.server_reference
        self.agent = MCPAgent()

    async def initialize(
        self,
        connection_type: str,
        server_url: str | None = None,
    ) -> None:
        """Initialize the MCP agent with the appropriate connection."""
        logger.info(f"Initializing MCPAgent with {connection_type} connection...")

        if connection_type == "stdio":
            await self.agent.initialize(
                connection_type="stdio",
                command=sys.executable,
                args=["-m", self.server_reference],
            )
        else:  # sse
            await self.agent.initialize(connection_type="sse", server_url=server_url)

        logger.info(f"Connected to MCP server via {connection_type}")

    async def run_interactive(self) -> None:
        """Run the agent in interactive mode."""
        print("\nMCP Agent Interactive Mode (type 'exit' to quit)\n")
        while True:
            user_input = input("\nEnter your request: ")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            response = await self.agent.run(user_input)
            print(f"\nAgent: {response}")

    async def run_single_prompt(self, prompt: str) -> None:
        """Run the agent with a single prompt."""
        await self.agent.run(prompt)

    async def run_default(self) -> None:
        """Run the agent in default mode."""
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        await self.agent.run(prompt)
        logger.info("Request processing completed.")

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        await self.agent.cleanup()
        logger.info("Session ended")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the MCP Agent")
    parser.add_argument(
        "--connection",
        "-c",
        choices=["stdio", "sse"],
        default="stdio",
        help="Connection type: stdio or sse",
    )
    parser.add_argument(
        "--server-url",
        default="http://127.0.0.1:8000/sse",
        help="URL for SSE connection",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument("--prompt", "-p", help="Single prompt to execute and exit")

    # History management arguments
    history_group = parser.add_argument_group("History Management")
    history_group.add_argument(
        "--enable-history",
        action="store_true",
        help="Enable conversation history saving",
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

    return parser.parse_args()


async def run_mcp() -> None:
    """Main entry point for the MCP runner."""
    args = parse_args()

    # Handle history commands first
    if args.list_sessions:
        history_manager = get_history_manager()
        sessions = history_manager.list_sessions()
        print(format_session_list(sessions))
        return

    if args.delete_session:
        history_manager = get_history_manager()
        if history_manager.delete_session(args.delete_session):
            print(format_session_deleted(args.delete_session))
        else:
            print(format_session_not_found(args.delete_session))
        return

    if args.cleanup_sessions:
        history_manager = get_history_manager()
        deleted_count = history_manager.cleanup_old_sessions()
        print(format_cleanup_result(deleted_count))
        return

    runner = MCPRunner()

    try:
        await runner.initialize(args.connection, args.server_url)

        # Check if history should be enabled
        history_enabled = args.enable_history or config.history_config.enabled

        # Handle session resumption
        if args.resume_session:
            history_manager = get_history_manager()
            loaded_memory = history_manager.load_session(args.resume_session)

            if loaded_memory:
                runner.agent.memory = loaded_memory
                runner.agent.session_id = args.resume_session
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
            runner.agent.session_id = history_manager.create_session(
                agent_name=runner.agent.name,
                agent_type=runner.agent.__class__.__name__,
                workspace_path=str(config.workspace_root),
            )
            logger.info(f"📝 Started new session: {runner.agent.session_id}")
            print(f"\n✓ History enabled. Session ID: {runner.agent.session_id}")

        if args.prompt:
            await runner.run_single_prompt(args.prompt)
        elif args.interactive:
            await runner.run_interactive()
        else:
            await runner.run_default()

    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Error running MCPAgent: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run_mcp())
