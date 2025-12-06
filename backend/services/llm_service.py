"""LLM Service - Unified interface for LLM providers (Ollama, OpenAI, Anthropic)."""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)


class LLMService:
    """Unified LLM service supporting multiple providers."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """Initialize LLM service.

        Args:
            provider: LLM provider (ollama, openai, anthropic). Defaults to settings.
            model: Model name. Defaults to settings based on provider.
            temperature: Sampling temperature. Defaults to 0.7.
        """
        self.provider = provider or settings.llm_provider
        self.temperature = temperature
        self._llm = None

        # Set model based on provider
        if model:
            self.model = model
        elif self.provider == "ollama":
            self.model = settings.ollama_model
        elif self.provider == "openai":
            self.model = settings.openai_model
        elif self.provider == "anthropic":
            self.model = settings.anthropic_model
        else:
            self.model = "llama3.2"

        logger.info(f"LLM Service initialized: provider={self.provider}, model={self.model}")

    def _get_llm(self):
        """Lazy-load the LLM based on provider."""
        if self._llm is not None:
            return self._llm

        if self.provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
                self._llm = ChatOllama(
                    model=self.model,
                    base_url=settings.ollama_base_url,
                    temperature=self.temperature,
                )
                logger.info(f"Initialized Ollama LLM: {self.model}")
            except ImportError:
                logger.error("langchain-ollama not installed. Run: pip install langchain-ollama")
                raise

        elif self.provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            try:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.model,
                    api_key=settings.openai_api_key,
                    temperature=self.temperature,
                )
                logger.info(f"Initialized OpenAI LLM: {self.model}")
            except ImportError:
                logger.error("langchain-openai not installed. Run: pip install langchain-openai")
                raise

        elif self.provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            try:
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=self.model,
                    api_key=settings.anthropic_api_key,
                    temperature=self.temperature,
                )
                logger.info(f"Initialized Anthropic LLM: {self.model}")
            except ImportError:
                logger.error("langchain-anthropic not installed. Run: pip install langchain-anthropic")
                raise

        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

        return self._llm

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generate text from the LLM.

        Args:
            prompt: User prompt/message.
            system_prompt: Optional system message for context.
            max_tokens: Maximum tokens to generate.

        Returns:
            LLMResponse with generated content.
        """
        llm = self._get_llm()

        messages = []
        if system_prompt:
            from langchain_core.messages import SystemMessage
            messages.append(SystemMessage(content=system_prompt))

        from langchain_core.messages import HumanMessage
        messages.append(HumanMessage(content=prompt))

        try:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # Extract usage info if available
            usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "input_tokens": response.usage_metadata.get("input_tokens", 0),
                    "output_tokens": response.usage_metadata.get("output_tokens", 0),
                }

            logger.debug(f"LLM generated {len(content)} chars")
            return LLMResponse(
                content=content,
                model=self.model,
                provider=self.provider,
                usage=usage,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate structured output (JSON) from the LLM.

        Args:
            prompt: User prompt with instructions for JSON output.
            system_prompt: Optional system message.
            output_schema: Optional JSON schema hint (for documentation).

        Returns:
            Parsed JSON as dictionary.
        """
        import json

        # Add JSON instruction to prompt
        json_instruction = "\n\nRespond with valid JSON only. No markdown, no explanation."
        if output_schema:
            json_instruction += f"\n\nExpected schema: {json.dumps(output_schema)}"

        full_prompt = prompt + json_instruction

        response = await self.generate(full_prompt, system_prompt)

        # Parse JSON from response
        try:
            # Try to extract JSON from the response
            content = response.content.strip()

            # Handle markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Raw response: {response.content}")
            raise ValueError(f"LLM did not return valid JSON: {e}")

    def is_available(self) -> bool:
        """Check if the LLM service is available."""
        try:
            self._get_llm()
            return True
        except Exception as e:
            logger.warning(f"LLM not available: {e}")
            return False


# Singleton instance for easy import
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
