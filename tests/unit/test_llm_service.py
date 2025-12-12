"""
Unit tests for the LLMService.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from backend.services.llm_service import LLMService, LLMResponse, get_llm_service


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_response_creation(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Generated text",
            model="llama3.2",
            provider="ollama",
            usage={"input_tokens": 10, "output_tokens": 50},
        )

        assert response.content == "Generated text"
        assert response.model == "llama3.2"
        assert response.provider == "ollama"
        assert response.usage["input_tokens"] == 10

    def test_response_default_usage(self):
        """Test response with default empty usage."""
        response = LLMResponse(
            content="Text",
            model="gpt-4",
            provider="openai",
        )

        assert response.usage == {}


class TestLLMServiceInitialization:
    """Tests for LLMService initialization."""

    @patch("backend.services.llm_service.settings")
    def test_init_with_defaults(self, mock_settings):
        """Test initialization with default settings."""
        mock_settings.llm_provider = "ollama"
        mock_settings.ollama_model = "llama3.2"

        service = LLMService()

        assert service.provider == "ollama"
        assert service.model == "llama3.2"
        assert service.temperature == 0.7

    @patch("backend.services.llm_service.settings")
    def test_init_with_custom_provider(self, mock_settings):
        """Test initialization with custom provider."""
        mock_settings.openai_model = "gpt-4"

        service = LLMService(provider="openai", model="gpt-4-turbo")

        assert service.provider == "openai"
        assert service.model == "gpt-4-turbo"

    @patch("backend.services.llm_service.settings")
    def test_init_with_custom_temperature(self, mock_settings):
        """Test initialization with custom temperature."""
        mock_settings.llm_provider = "ollama"
        mock_settings.ollama_model = "llama3.2"

        service = LLMService(temperature=0.3)

        assert service.temperature == 0.3

    @patch("backend.services.llm_service.settings")
    def test_init_openai_provider(self, mock_settings):
        """Test initialization with OpenAI provider."""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4"

        service = LLMService()

        assert service.provider == "openai"
        assert service.model == "gpt-4"

    @patch("backend.services.llm_service.settings")
    def test_init_anthropic_provider(self, mock_settings):
        """Test initialization with Anthropic provider."""
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_model = "claude-3-sonnet"

        service = LLMService()

        assert service.provider == "anthropic"
        assert service.model == "claude-3-sonnet"

    @patch("backend.services.llm_service.settings")
    def test_init_unknown_provider_fallback(self, mock_settings):
        """Test fallback model for unknown provider."""
        mock_settings.llm_provider = "unknown"

        service = LLMService()

        assert service.model == "llama3.2"


class TestGetLLM:
    """Tests for lazy LLM loading."""

    @patch("backend.services.llm_service.settings")
    def test_get_llm_ollama(self, mock_settings):
        """Test loading Ollama LLM."""
        mock_settings.llm_provider = "ollama"
        mock_settings.ollama_model = "llama3.2"
        mock_settings.ollama_base_url = "http://localhost:11434"

        with patch("backend.services.llm_service.ChatOllama") as MockOllama:
            mock_llm = MagicMock()
            MockOllama.return_value = mock_llm

            service = LLMService()

            with patch.dict("sys.modules", {"langchain_ollama": MagicMock(ChatOllama=MockOllama)}):
                from langchain_ollama import ChatOllama
                result = service._get_llm()

    @patch("backend.services.llm_service.settings")
    def test_get_llm_openai_no_api_key(self, mock_settings):
        """Test OpenAI LLM raises error without API key."""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4"
        mock_settings.openai_api_key = None

        service = LLMService()

        with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
            service._get_llm()

    @patch("backend.services.llm_service.settings")
    def test_get_llm_anthropic_no_api_key(self, mock_settings):
        """Test Anthropic LLM raises error without API key."""
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_model = "claude-3"
        mock_settings.anthropic_api_key = None

        service = LLMService()

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
            service._get_llm()

    @patch("backend.services.llm_service.settings")
    def test_get_llm_unknown_provider(self, mock_settings):
        """Test unknown provider raises error."""
        mock_settings.llm_provider = "unknown_provider"

        service = LLMService()

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            service._get_llm()

    @patch("backend.services.llm_service.settings")
    def test_get_llm_caches_instance(self, mock_settings):
        """Test that LLM instance is cached."""
        mock_settings.llm_provider = "ollama"
        mock_settings.ollama_model = "llama3.2"
        mock_settings.ollama_base_url = "http://localhost:11434"

        service = LLMService()
        mock_llm = MagicMock()
        service._llm = mock_llm

        result = service._get_llm()

        assert result == mock_llm


class TestGenerate:
    """Tests for text generation."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked LLM."""
        with patch("backend.services.llm_service.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.ollama_model = "llama3.2"

            service = LLMService()
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Generated text response"
            mock_response.usage_metadata = {
                "input_tokens": 20,
                "output_tokens": 100,
            }
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            service._llm = mock_llm

            return service

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_service):
        """Test successful text generation."""
        result = await mock_service.generate("What is Python?")

        assert isinstance(result, LLMResponse)
        assert result.content == "Generated text response"
        assert result.provider == "ollama"
        mock_service._llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, mock_service):
        """Test generation with system prompt."""
        result = await mock_service.generate(
            prompt="What is Python?",
            system_prompt="You are a helpful assistant."
        )

        assert isinstance(result, LLMResponse)
        call_args = mock_service._llm.ainvoke.call_args[0][0]
        assert len(call_args) == 2  # System + Human message

    @pytest.mark.asyncio
    async def test_generate_extracts_usage(self, mock_service):
        """Test that usage metadata is extracted."""
        result = await mock_service.generate("Test prompt")

        assert result.usage["input_tokens"] == 20
        assert result.usage["output_tokens"] == 100

    @pytest.mark.asyncio
    async def test_generate_handles_no_usage_metadata(self):
        """Test handling responses without usage metadata."""
        with patch("backend.services.llm_service.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.ollama_model = "llama3.2"

            service = LLMService()
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Response"
            mock_response.usage_metadata = None
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            service._llm = mock_llm

            result = await service.generate("Test")

            assert result.usage == {}

    @pytest.mark.asyncio
    async def test_generate_handles_error(self):
        """Test error handling in generation."""
        with patch("backend.services.llm_service.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.ollama_model = "llama3.2"

            service = LLMService()
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM Error"))
            service._llm = mock_llm

            with pytest.raises(Exception, match="LLM Error"):
                await service.generate("Test")


class TestGenerateStructured:
    """Tests for structured (JSON) generation."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked LLM."""
        with patch("backend.services.llm_service.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.ollama_model = "llama3.2"

            service = LLMService()
            return service

    @pytest.mark.asyncio
    async def test_generate_structured_success(self, mock_service):
        """Test successful structured generation."""
        json_response = {"name": "John", "age": 30}

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps(json_response)
        mock_response.usage_metadata = {}
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_service._llm = mock_llm

        result = await mock_service.generate_structured("Get user info")

        assert result == json_response

    @pytest.mark.asyncio
    async def test_generate_structured_with_schema(self, mock_service):
        """Test structured generation with schema hint."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        json_response = {"name": "Alice"}

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps(json_response)
        mock_response.usage_metadata = {}
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_service._llm = mock_llm

        result = await mock_service.generate_structured(
            "Get user",
            output_schema=schema
        )

        assert result == json_response

    @pytest.mark.asyncio
    async def test_generate_structured_handles_markdown_json(self, mock_service):
        """Test handling JSON wrapped in markdown code blocks."""
        json_data = {"key": "value"}
        markdown_response = f"```json\n{json.dumps(json_data)}\n```"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = markdown_response
        mock_response.usage_metadata = {}
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_service._llm = mock_llm

        result = await mock_service.generate_structured("Get data")

        assert result == json_data

    @pytest.mark.asyncio
    async def test_generate_structured_handles_code_block(self, mock_service):
        """Test handling JSON wrapped in generic code blocks."""
        json_data = {"result": 42}
        code_response = f"```\n{json.dumps(json_data)}\n```"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = code_response
        mock_response.usage_metadata = {}
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_service._llm = mock_llm

        result = await mock_service.generate_structured("Calculate")

        assert result == json_data

    @pytest.mark.asyncio
    async def test_generate_structured_invalid_json(self, mock_service):
        """Test handling invalid JSON response."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON"
        mock_response.usage_metadata = {}
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_service._llm = mock_llm

        with pytest.raises(ValueError, match="LLM did not return valid JSON"):
            await mock_service.generate_structured("Get JSON")


class TestIsAvailable:
    """Tests for availability checking."""

    @patch("backend.services.llm_service.settings")
    def test_is_available_true(self, mock_settings):
        """Test availability returns True when LLM loads."""
        mock_settings.llm_provider = "ollama"
        mock_settings.ollama_model = "llama3.2"

        service = LLMService()
        service._llm = MagicMock()  # Pre-set LLM

        assert service.is_available() is True

    @patch("backend.services.llm_service.settings")
    def test_is_available_false(self, mock_settings):
        """Test availability returns False on error."""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4"
        mock_settings.openai_api_key = None

        service = LLMService()

        assert service.is_available() is False


class TestGetLLMServiceSingleton:
    """Tests for singleton service getter."""

    def test_get_llm_service_returns_instance(self):
        """Test that get_llm_service returns an LLMService."""
        import backend.services.llm_service as module

        # Reset singleton
        module._llm_service = None

        with patch("backend.services.llm_service.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.ollama_model = "llama3.2"

            service = get_llm_service()

            assert isinstance(service, LLMService)

    def test_get_llm_service_returns_same_instance(self):
        """Test that get_llm_service returns the same instance."""
        import backend.services.llm_service as module

        # Reset singleton
        module._llm_service = None

        with patch("backend.services.llm_service.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.ollama_model = "llama3.2"

            service1 = get_llm_service()
            service2 = get_llm_service()

            assert service1 is service2
