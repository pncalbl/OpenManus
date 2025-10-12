import argparse
import asyncio
import time

from app.agent.data_analysis import DataAnalysis
from app.agent.manus import Manus
from app.config import config
from app.flow.flow_factory import FlowFactory, FlowType
from app.history import get_history_manager
from app.history.cli import (
    format_cleanup_result,
    format_session_deleted,
    format_session_list,
    format_session_not_found,
)
from app.logger import logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run multi-agent flow execution")
    parser.add_argument(
        "--prompt", type=str, required=False, help="Input prompt for the flow"
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

    return parser.parse_args()


async def run_flow():
    args = parse_args()

    # Handle history commands first (these don't need agent initialization)
    if args.list_sessions:
        history_manager = get_history_manager()
        sessions = history_manager.list_sessions(limit=args.limit or 50)
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

    # Create agents
    agents = {
        "manus": Manus(),
    }
    if config.run_flow_config.use_data_analysis_agent:
        agents["data_analysis"] = DataAnalysis()

    try:
        # Get the primary agent (manus) for history management
        primary_agent = agents["manus"]

        # Check if history should be enabled
        history_enabled = args.enable_history or config.history_config.enabled

        # Handle session resumption
        if args.resume_session:
            history_manager = get_history_manager()
            loaded_memory = history_manager.load_session(args.resume_session)

            if loaded_memory:
                primary_agent.memory = loaded_memory
                primary_agent.session_id = args.resume_session
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
            primary_agent.session_id = history_manager.create_session(
                agent_name=primary_agent.name,
                agent_type="FlowExecution",
                workspace_path=str(config.workspace_root),
            )
            logger.info(f"📝 Started new session: {primary_agent.session_id}")
            print(f"\n✓ History enabled. Session ID: {primary_agent.session_id}")

        # Use command line prompt if provided, otherwise ask for input
        prompt = args.prompt if args.prompt else input("Enter your prompt: ")

        if prompt.strip().isspace() or not prompt:
            logger.warning("Empty prompt provided.")
            return

        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents,
        )
        logger.warning("Processing your request...")

        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                flow.execute(prompt),
                timeout=3600,  # 60 minute timeout for the entire execution
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
            logger.info(result)
        except asyncio.TimeoutError:
            logger.error("Request processing timed out after 1 hour")
            logger.info(
                "Operation terminated due to timeout. Please try a simpler request."
            )

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        # Ensure cleanup for all agents
        for agent in agents.values():
            if hasattr(agent, "cleanup"):
                await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(run_flow())
