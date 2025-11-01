from app.tool import BaseTool
from app.tool.base import ToolResult


class AskHuman(BaseTool):
    """Add a tool to ask human for help."""

    name: str = "ask_human"
    description: str = "Use this tool to ask human for help."
    parameters: str = {
        "type": "object",
        "properties": {
            "inquire": {
                "type": "string",
                "description": "The question you want to ask human.",
            }
        },
        "required": ["inquire"],
    }

    async def execute(self, inquire: str) -> ToolResult:
        response = input(f"""Bot: {inquire}\n\nYou: """).strip()
        return ToolResult(output=response)

    async def cleanup(self) -> None:
        """Clean up resources (no resources to clean for this tool)."""
        pass
