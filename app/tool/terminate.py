from app.tool.base import BaseTool, ToolResult


_TERMINATE_DESCRIPTION = """Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.
When you have finished all the tasks, call this tool to end the work."""


class Terminate(BaseTool):
    name: str = "terminate"
    description: str = _TERMINATE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "The finish status of the interaction.",
                "enum": ["success", "failure"],
            }
        },
        "required": ["status"],
    }

    async def execute(self, status: str) -> ToolResult:
        """Finish the current execution"""
        message = f"The interaction has been completed with status: {status}"
        return ToolResult(output=message)

    async def cleanup(self) -> None:
        """Clean up resources (no resources to clean for this tool)."""
        pass
