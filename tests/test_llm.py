"""
Tests for LLM module

Unit tests for LLM functionality including TokenCounter, message handling,
and API interactions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm import LLM, TokenCounter
from app.schema import Message, ToolChoice


class TestTokenCounter:
    """Test TokenCounter functionality"""

    @pytest.fixture
    def tokenizer(self):
        """Create a mock tokenizer"""
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
        return mock_tokenizer

    @pytest.fixture
    def counter(self, tokenizer):
        """Create a TokenCounter instance"""
        return TokenCounter(tokenizer)

    def test_count_text(self, counter):
        """Test text token counting"""
        result = counter.count_text("test text")
        assert result == 5  # Mock tokenizer returns 5 tokens

    def test_count_text_empty(self, counter):
        """Test empty text returns 0 tokens"""
        result = counter.count_text("")
        assert result == 0

    def test_count_text_none(self, counter):
        """Test None text returns 0 tokens"""
        result = counter.count_text(None)
        assert result == 0

    def test_count_image_low_detail(self, counter):
        """Test low detail image token count"""
        image_item = {"detail": "low"}
        result = counter.count_image(image_item)
        assert result == TokenCounter.LOW_DETAIL_IMAGE_TOKENS  # 85 tokens

    def test_count_image_high_detail_with_dimensions(self, counter):
        """Test high detail image with dimensions"""
        image_item = {"detail": "high", "dimensions": (1024, 1024)}
        result = counter.count_image(image_item)
        # Should calculate based on dimensions
        assert result > 0

    def test_count_image_medium_detail(self, counter):
        """Test medium detail image (default)"""
        image_item = {"detail": "medium"}
        result = counter.count_image(image_item)
        # Medium detail uses high detail calculation
        assert result > 0

    def test_calculate_high_detail_tokens_small_image(self, counter):
        """Test high detail token calculation for small image"""
        # Image smaller than MAX_SIZE
        result = counter._calculate_high_detail_tokens(512, 512)
        assert result > 0

    def test_calculate_high_detail_tokens_large_image(self, counter):
        """Test high detail token calculation for large image"""
        # Image larger than MAX_SIZE (2048)
        result = counter._calculate_high_detail_tokens(4096, 4096)
        assert result > 0

    def test_calculate_high_detail_tokens_rectangular(self, counter):
        """Test high detail token calculation for rectangular image"""
        result = counter._calculate_high_detail_tokens(1920, 1080)
        assert result > 0


class TestLLM:
    """Test LLM functionality"""

    @pytest.fixture
    def llm_config(self):
        """Create mock LLM configuration"""
        from app.config import LLMSettings

        return LLMSettings(
            api_key="test_key",
            base_url="https://api.openai.com/v1",
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
        )

    @pytest.fixture
    def llm(self, llm_config):
        """Create LLM instance"""
        with patch("app.llm.LLM._init_client"):
            llm = LLM(llm_config)
            llm.client = AsyncMock()
            return llm

    def test_llm_initialization(self, llm_config):
        """Test LLM initialization"""
        with patch("app.llm.LLM._init_client") as mock_init:
            llm = LLM(llm_config)
            mock_init.assert_called_once()
            assert llm.model == "gpt-4"
            assert llm.temperature == 0.7

    def test_prepare_messages_basic(self, llm):
        """Test basic message preparation"""
        messages = [
            Message.user_message("Hello"),
            Message.assistant_message("Hi there"),
        ]

        prepared = llm._prepare_messages(messages)

        assert len(prepared) == 2
        assert prepared[0]["role"] == "user"
        assert prepared[0]["content"] == "Hello"
        assert prepared[1]["role"] == "assistant"
        assert prepared[1]["content"] == "Hi there"

    def test_prepare_messages_with_system(self, llm):
        """Test message preparation with system messages"""
        messages = [Message.user_message("Hello")]
        system_msgs = [Message.system_message("You are a helpful assistant")]

        prepared = llm._prepare_messages(messages, system_msgs=system_msgs)

        assert len(prepared) == 2
        assert prepared[0]["role"] == "system"
        assert prepared[1]["role"] == "user"

    def test_prepare_messages_with_tool_calls(self, llm):
        """Test message preparation with tool calls"""
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "test_tool", "arguments": '{"arg": "value"}'},
            }
        ]

        message = Message.from_tool_calls(content="Using tool", tool_calls=tool_calls)
        prepared = llm._prepare_messages([message])

        assert len(prepared) == 1
        assert prepared[0]["role"] == "assistant"
        assert "tool_calls" in prepared[0]

    @pytest.mark.asyncio
    async def test_ask_basic(self, llm):
        """Test basic ask functionality"""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Test response", tool_calls=None))
        ]
        llm.client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message.user_message("Test question")]
        response = await llm.ask(messages)

        assert response.content == "Test response"
        assert response.tool_calls is None

    @pytest.mark.asyncio
    async def test_ask_with_system_prompt(self, llm):
        """Test ask with system prompt"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Response", tool_calls=None))
        ]
        llm.client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message.user_message("Question")]
        system_msgs = [Message.system_message("System prompt")]

        response = await llm.ask(messages, system_msgs=system_msgs)

        # Verify system message was included
        call_args = llm.client.chat.completions.create.call_args
        prepared_messages = call_args[1]["messages"]
        assert prepared_messages[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_ask_tool_with_tools(self, llm):
        """Test ask_tool with tool definitions"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Using tool",
                    tool_calls=[
                        MagicMock(
                            id="call_1",
                            type="function",
                            function=MagicMock(
                                name="test_tool", arguments='{"arg": "value"}'
                            ),
                        )
                    ],
                )
            )
        ]
        llm.client.chat.completions.create = AsyncMock(return_value=mock_response)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {},
                },
            }
        ]

        messages = [Message.user_message("Use the tool")]
        response = await llm.ask_tool(
            messages, tools=tools, tool_choice=ToolChoice.AUTO
        )

        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].function.name == "test_tool"

    @pytest.mark.asyncio
    async def test_ask_tool_choice_none(self, llm):
        """Test ask_tool with tool_choice=NONE"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Response", tool_calls=None))
        ]
        llm.client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message.user_message("Question")]
        response = await llm.ask_tool(messages, tool_choice=ToolChoice.NONE)

        # Verify tool_choice="none" was passed
        call_args = llm.client.chat.completions.create.call_args
        assert call_args[1]["tool_choice"] == "none"

    @pytest.mark.asyncio
    async def test_ask_tool_choice_required(self, llm):
        """Test ask_tool with tool_choice=REQUIRED"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="",
                    tool_calls=[
                        MagicMock(
                            id="call_1",
                            type="function",
                            function=MagicMock(name="tool", arguments="{}"),
                        )
                    ],
                )
            )
        ]
        llm.client.chat.completions.create = AsyncMock(return_value=mock_response)

        tools = [{"type": "function", "function": {"name": "tool", "parameters": {}}}]
        messages = [Message.user_message("Question")]

        response = await llm.ask_tool(
            messages, tools=tools, tool_choice=ToolChoice.REQUIRED
        )

        # Verify tool_choice="required" was passed
        call_args = llm.client.chat.completions.create.call_args
        assert call_args[1]["tool_choice"] == "required"

    @pytest.mark.asyncio
    async def test_token_limit_exceeded(self, llm):
        """Test TokenLimitExceeded exception handling"""
        from app.exceptions import TokenLimitExceeded

        # Mock to raise TokenLimitExceeded
        llm.client.chat.completions.create = AsyncMock(
            side_effect=TokenLimitExceeded("Token limit exceeded", 1000, 8000)
        )

        messages = [Message.user_message("Test")]

        with pytest.raises(TokenLimitExceeded):
            await llm.ask(messages)

    @pytest.mark.asyncio
    async def test_is_reasoning_model(self, llm_config):
        """Test reasoning model detection"""
        llm_config.model = "o1"
        with patch("app.llm.LLM._init_client"):
            llm = LLM(llm_config)
            assert llm.is_reasoning_model is True

        llm_config.model = "gpt-4"
        with patch("app.llm.LLM._init_client"):
            llm = LLM(llm_config)
            assert llm.is_reasoning_model is False

    @pytest.mark.asyncio
    async def test_is_multimodal_model(self, llm_config):
        """Test multimodal model detection"""
        llm_config.model = "gpt-4o"
        with patch("app.llm.LLM._init_client"):
            llm = LLM(llm_config)
            assert llm.is_multimodal is True

        llm_config.model = "gpt-3.5-turbo"
        with patch("app.llm.LLM._init_client"):
            llm = LLM(llm_config)
            assert llm.is_multimodal is False

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, llm):
        """Test retry behavior on rate limit error"""
        from openai import RateLimitError

        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Success", tool_calls=None))
        ]

        llm.client.chat.completions.create = AsyncMock(
            side_effect=[
                RateLimitError(
                    "Rate limit",
                    response=MagicMock(status_code=429),
                    body={"error": {"message": "Rate limit"}},
                ),
                mock_response,
            ]
        )

        messages = [Message.user_message("Test")]

        # Should retry and succeed
        response = await llm.ask(messages)
        assert response.content == "Success"

    def test_count_message_tokens_basic(self, llm):
        """Test basic message token counting"""
        messages = [
            Message.user_message("Hello world"),
            Message.assistant_message("Hi there"),
        ]

        with patch.object(llm.counter, "count_text", return_value=10):
            total = llm.count_message_tokens(messages)
            # Should include base tokens + text tokens
            assert total > 0

    def test_count_message_tokens_with_tools(self, llm):
        """Test token counting for messages with tools"""
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "test_tool", "arguments": '{"arg": "value"}'},
            }
        ]

        message = Message.from_tool_calls(content="Using tool", tool_calls=tool_calls)

        with patch.object(llm.counter, "count_text", return_value=10):
            total = llm.count_message_tokens([message])
            assert total > 0

    def test_singleton_pattern(self):
        """Test LLM singleton pattern"""
        from app.llm import LLM

        with patch("app.llm.LLM._init_client"):
            llm1 = LLM.get_instance()
            llm2 = LLM.get_instance()

            # Should return the same instance
            assert llm1 is llm2

    @pytest.mark.asyncio
    async def test_bedrock_client_initialization(self):
        """Test Bedrock client initialization"""
        from app.config import LLMSettings

        config = LLMSettings(
            api_key="test_key",
            model="claude-3-opus",
            bedrock_region="us-east-1",
        )

        with patch("app.llm.BedrockClient") as mock_bedrock:
            llm = LLM(config)
            # Should initialize Bedrock client for Claude models
            if "claude" in config.model.lower():
                mock_bedrock.assert_called()
