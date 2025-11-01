import argparse
import asyncio
import time

from app.agent.data_analysis import DataAnalysis
from app.agent.manus import Manus
from app.config import config
from app.flow.flow_factory import FlowFactory, FlowType
from app.history.runner_helper import HistoryRunnerHelper
from app.logger import logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run multi-agent flow execution")
    parser.add_argument(
        "--prompt", type=str, required=False, help="Input prompt for the flow"
    )

    # Add history management arguments
    HistoryRunnerHelper.add_history_arguments(parser)

    return parser.parse_args()


async def run_flow():
    args = parse_args()

    # Handle history commands first (these don't need agent initialization)
    if await HistoryRunnerHelper.handle_history_commands(args):
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

        # Setup conversation session (use FlowExecution as agent type)
        if not await HistoryRunnerHelper.setup_session(
            primary_agent, args, agent_type_override="FlowExecution"
        ):
            return

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
