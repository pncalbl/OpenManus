"""
Tests for ToolCallAgent

Unit tests for the tool call agent functionality including tool execution,
state management, and error handling.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.toolcall import ToolCallAgent
from app.schema import AgentState, Message, ToolCall, ToolChoice
from app.tool import Terminate, ToolCollection, ToolResult


class MockTool:
    """Mock tool for testing purposes"""

    name = "mock_tool"
    description = "A mock tool for testing"

    async def __call__(self, **kwargs):
        return ToolResult.success_response(f"Mock result: {kwargs}")

    async def cleanup(self):
        """Cleanup method for testing"""
        pass


class FailingMockTool:
    """Mock tool that always fails"""

    name = "failing_tool"
    description = "A mock tool that fails"

    async def __call__(self, **kwargs):
        raise ValueError("Mock tool failure")


def create_mock_tool_call(name: str, arguments: dict) -> ToolCall:
    """Helper function to create a mock ToolCall"""
    return ToolCall(
        id="test_call_id",
        type="function",
        function={
            "name": name,
            "arguments": json.dumps(arguments),
        },
    )


class TestToolCallAgent:
    """Test ToolCallAgent functionality"""

    @pytest.fixture
    def agent(self):
        """Create a test agent with basic tools"""
        tool_collection = ToolCollection(Terminate(), MockTool())
        agent = ToolCallAgent(
            available_tools=tool_collection,
            max_steps=5,
        )
        return agent

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test basic agent initialization"""
        assert agent.name == "toolcall"
        assert agent.max_steps == 5
        assert agent.state == AgentState.IDLE
        assert len(agent.available_tools.tool_map) == 2
        assert "terminate" in agent.available_tools.tool_map
        assert "mock_tool" in agent.available_tools.tool_map

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, agent):
        """Test successful tool execution"""
        tool_call = create_mock_tool_call("mock_tool", {"param": "value"})

        result = await agent.execute_tool(tool_call)

        assert "Mock result" in result
        assert "param" in result

    @pytest.mark.asyncio
    async def test_execute_tool_terminate(self, agent):
        """Test terminate tool execution"""
        tool_call = create_mock_tool_call("terminate", {})

        result = await agent.execute_tool(tool_call)

        # Terminate tool should change state to FINISHED
        assert agent.state == AgentState.FINISHED
        assert "terminated" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, agent):
        """Test execution of unknown tool"""
        tool_call = create_mock_tool_call("unknown_tool", {})

        result = await agent.execute_tool(tool_call)

        assert "Error" in result
        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_json(self, agent):
        """Test tool execution with invalid JSON arguments"""
        tool_call = ToolCall(
            id="test_call_id",
            type="function",
            function={
                "name": "mock_tool",
                "arguments": "{invalid json}",
            },
        )

        result = await agent.execute_tool(tool_call)

        assert "Error" in result
        assert "JSON" in result or "parsing" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_with_exception(self):
        """Test tool execution when tool raises exception"""
        tool_collection = ToolCollection(FailingMockTool())
        agent = ToolCallAgent(available_tools=tool_collection)

        tool_call = create_mock_tool_call("failing_tool", {})
        result = await agent.execute_tool(tool_call)

        assert "Error" in result
        assert "Mock tool failure" in result

    @pytest.mark.asyncio
    async def test_special_tool_detection(self, agent):
        """Test special tool detection"""
        assert agent._is_special_tool("terminate")
        assert agent._is_special_tool("Terminate")  # Case insensitive
        assert not agent._is_special_tool("mock_tool")

    @pytest.mark.asyncio
    async def test_handle_special_tool(self, agent):
        """Test special tool handling changes agent state"""
        initial_state = agent.state

        await agent._handle_special_tool("terminate", "success")

        assert agent.state == AgentState.FINISHED
        assert agent.state != initial_state

    @pytest.mark.asyncio
    async def test_handle_non_special_tool(self, agent):
        """Test non-special tool doesn't change state"""
        initial_state = agent.state

        await agent._handle_special_tool("mock_tool", "success")

        assert agent.state == initial_state

    @pytest.mark.asyncio
    async def test_act_with_no_tool_calls(self, agent):
        """Test act() when no tool calls are present"""
        agent.tool_calls = []
        agent.memory.add_message(Message.assistant_message("Test content"))

        result = await agent.act()

        assert "Test content" in result or "No content" in result

    @pytest.mark.asyncio
    async def test_act_with_tool_calls(self, agent):
        """Test act() with tool calls"""
        agent.tool_calls = [create_mock_tool_call("mock_tool", {"test": "data"})]

        result = await agent.act()

        assert "Mock result" in result

    @pytest.mark.asyncio
    async def test_act_required_mode_no_calls(self):
        """Test act() in REQUIRED mode without tool calls raises error"""
        agent = ToolCallAgent(
            available_tools=ToolCollection(MockTool()),
            tool_choices=ToolChoice.REQUIRED,
        )
        agent.tool_calls = []

        with pytest.raises(ValueError, match="Tool calls required"):
            await agent.act()

    @pytest.mark.asyncio
    async def test_cleanup(self, agent):
        """Test cleanup calls cleanup on tools"""
        # Track if cleanup was called
        cleanup_called = {"mock_tool": False}

        async def mock_cleanup():
            cleanup_called["mock_tool"] = True

        agent.available_tools.tool_map["mock_tool"].cleanup = mock_cleanup

        await agent.cleanup()

        assert cleanup_called["mock_tool"]

    @pytest.mark.asyncio
    async def test_cleanup_with_error(self, agent):
        """Test cleanup handles errors gracefully"""

        async def failing_cleanup():
            raise Exception("Cleanup failed")

        agent.available_tools.tool_map["mock_tool"].cleanup = failing_cleanup

        # Should not raise exception
        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_saves_history_when_session_id_set(self, agent):
        """Test cleanup saves conversation history when session_id is set"""
        agent.session_id = "test_session_123"
        agent.memory.add_message(Message.user_message("Test message"))

        with patch("app.agent.toolcall.get_history_manager") as mock_manager:
            mock_history = MagicMock()
            mock_history.save_session.return_value = True
            mock_manager.return_value = mock_history

            await agent.cleanup()

            # Verify save_session was called
            mock_history.save_session.assert_called_once()
            call_args = mock_history.save_session.call_args
            assert call_args[1]["session_id"] == "test_session_123"
            assert call_args[1]["agent_name"] == agent.name

    @pytest.mark.asyncio
    async def test_max_observe_truncates_result(self, agent):
        """Test max_observe truncates long results"""
        agent.max_observe = 10
        agent.tool_calls = [create_mock_tool_call("mock_tool", {"test": "data"})]

        result = await agent.act()

        # Result should be truncated to max_observe characters
        lines = result.split("\n\n")
        for line in lines:
            assert len(line) <= 10

    @pytest.mark.asyncio
    async def test_execute_tool_with_invalid_command(self, agent):
        """Test execute_tool with invalid/empty command"""
        # Test with None command
        result = await agent.execute_tool(None)
        assert "Error" in result
        assert "Invalid command" in result

        # Test with command missing function
        invalid_call = ToolCall(id="test", type="function", function=None)
        result = await agent.execute_tool(invalid_call)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_tool_choice_none_mode(self):
        """Test agent behavior in NONE tool choice mode"""
        agent = ToolCallAgent(
            available_tools=ToolCollection(MockTool()),
            tool_choices=ToolChoice.NONE,
        )

        # Mock the LLM response
        with patch.object(agent.llm, "ask_tool") as mock_ask:
            mock_response = MagicMock()
            mock_response.content = "Test response"
            mock_response.tool_calls = None
            mock_ask.return_value = mock_response

            result = await agent.think()

            # In NONE mode, should accept content without tools
            assert result is True
            assert len(agent.memory.messages) > 0

    @pytest.mark.asyncio
    async def test_tool_choice_auto_mode(self):
        """Test agent behavior in AUTO tool choice mode"""
        agent = ToolCallAgent(
            available_tools=ToolCollection(MockTool()),
            tool_choices=ToolChoice.AUTO,
        )

        # Mock the LLM response with content but no tool calls
        with patch.object(agent.llm, "ask_tool") as mock_ask:
            mock_response = MagicMock()
            mock_response.content = "Test response"
            mock_response.tool_calls = None
            mock_ask.return_value = mock_response

            result = await agent.think()

            # In AUTO mode with content, should return True
            assert result is True

    @pytest.mark.asyncio
    async def test_tool_choice_required_mode(self):
        """Test agent behavior in REQUIRED tool choice mode"""
        agent = ToolCallAgent(
            available_tools=ToolCollection(MockTool()),
            tool_choices=ToolChoice.REQUIRED,
        )

        # Mock the LLM response with no tool calls
        with patch.object(agent.llm, "ask_tool") as mock_ask:
            mock_response = MagicMock()
            mock_response.content = "Test response"
            mock_response.tool_calls = None
            mock_ask.return_value = mock_response

            result = await agent.think()

            # In REQUIRED mode without tool calls, should still return True
            # (will be handled in act())
            assert result is True

    @pytest.mark.asyncio
    async def test_progress_tracking_during_execution(self, agent):
        """Test progress tracking is updated during tool execution"""
        mock_tracker = MagicMock()
        agent.progress_tracker = mock_tracker
        agent.progress_enabled = True

        tool_call = create_mock_tool_call("mock_tool", {"test": "data"})

        await agent.execute_tool(tool_call)

        # Verify progress tracker was called
        mock_tracker.message.assert_called()
        call_args = [call[0][0] for call in mock_tracker.message.call_args_list]
        assert any("mock_tool" in arg for arg in call_args)

    @pytest.mark.asyncio
    async def test_base64_image_handling(self, agent):
        """Test base64 image is properly captured from tool result"""

        class ImageTool:
            name = "image_tool"
            description = "Tool that returns image"

            async def __call__(self, **kwargs):
                return ToolResult.success_response(
                    "Image generated", base64_image="base64encodedimage"
                )

        agent.available_tools.add_tool(ImageTool())
        agent.tool_calls = [create_mock_tool_call("image_tool", {})]

        await agent.act()

        # Check that base64_image was stored
        assert agent._current_base64_image == "base64encodedimage"

        # Check that tool message includes the base64_image
        tool_messages = [m for m in agent.memory.messages if m.role == "tool"]
        assert len(tool_messages) > 0
        assert tool_messages[-1].base64_image == "base64encodedimage"
