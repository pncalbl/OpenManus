from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.config import config
from app.llm import LLM
from app.schema import AgentState, Memory


def _get_react_max_steps() -> int:
    """Get react max_steps from config or use fallback."""
    return (
        config.agent_config.react_max_steps
        if hasattr(config, "agent_config") and config.agent_config
        else 10
    )


class ReActAgent(BaseAgent, ABC):
    """
    Abstract base class for ReAct (Reasoning + Acting) pattern agents.

    ReActAgent implements the ReAct framework where agents alternate between
    thinking (reasoning about the current state) and acting (taking actions
    based on their reasoning).

    The agent follows this loop:
    1. Think: Analyze current state and decide what to do
    2. Act: Execute the decided action
    3. Observe: Get feedback from the action
    4. Repeat until task is complete

    Attributes:
        name: Agent identifier
        description: Optional agent description
        system_prompt: System-level instructions for the agent
        next_step_prompt: Prompt for the next thinking step
        llm: Language model for reasoning
        memory: Conversation and state memory
        state: Current agent state (IDLE, RUNNING, FINISHED, etc.)
        max_steps: Maximum number of think-act cycles
        current_step: Current step number
    """

    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = Field(default_factory=_get_react_max_steps)
    current_step: int = 0

    @abstractmethod
    async def think(self) -> bool:
        """
        Process current state and decide next action.

        This method should analyze the current state and determine what
        action (if any) should be taken next.

        Returns:
            bool: True if an action should be taken, False otherwise
        """

    @abstractmethod
    async def act(self) -> str:
        """
        Execute decided actions.

        This method should perform the action determined by think().

        Returns:
            str: Result of the action
        """

    async def step(self) -> str:
        """
        Execute a single ReAct step: think and act.

        This method executes one complete cycle of the ReAct pattern:
        - Call think() to decide what to do
        - If thinking determines action is needed, call act()
        - Update progress tracking if enabled

        Returns:
            str: Result of the step execution
        """
        # Update progress if tracking is enabled
        if self.progress_tracker:
            self.progress_tracker.start_step(f"Step {self.current_step}")

        should_act = await self.think()
        if not should_act:
            result = "Thinking complete - no action needed"
            if self.progress_tracker:
                self.progress_tracker.complete_step(
                    f"Step {self.current_step}", result=result
                )
                self.progress_tracker.update(
                    message=result, increment=1
                )
            return result

        result = await self.act()

        # Update progress with result
        if self.progress_tracker:
            self.progress_tracker.complete_step(
                f"Step {self.current_step}", result="Completed"
            )
            self.progress_tracker.update(
                message=f"Step {self.current_step} completed", increment=1
            )

        return result
