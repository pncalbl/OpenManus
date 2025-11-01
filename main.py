import argparse
import asyncio

from app.agent.manus import Manus
from app.history.runner_helper import HistoryRunnerHelper
from app.logger import logger


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Manus agent with a prompt")
    parser.add_argument(
        "--prompt", type=str, required=False, help="Input prompt for the agent"
    )

    # Add history management arguments
    HistoryRunnerHelper.add_history_arguments(parser)

    args = parser.parse_args()

    # Handle history commands that don't need agent
    if await HistoryRunnerHelper.handle_history_commands(args):
        return

    # Create and initialize Manus agent
    agent = await Manus.create()

    try:
        # Setup conversation session
        if not await HistoryRunnerHelper.setup_session(agent, args):
            return

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
