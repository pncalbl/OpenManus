from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.llm import LLM
from app.schema import AgentState, Memory


class ReActAgent(BaseAgent, ABC):
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    async def step(self) -> str:
        """Execute a single step: think and act."""
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
