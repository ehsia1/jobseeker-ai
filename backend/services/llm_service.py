"""LLM Service - Unified interface for LLM providers (Ollama, OpenAI, Anthropic)."""

import json
import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from backend.config import settings

logger = logging.getLogger(__name__)


def repair_json(text: str) -> str:
    """Attempt to repair common JSON errors from LLM outputs.

    Handles:
    - Missing commas between elements
    - Trailing commas before ] or }
    - Single quotes instead of double quotes
    - Unquoted string values
    - Control characters in strings
    """
    if not text:
        return text

    # Remove any leading/trailing whitespace
    text = text.strip()

    # Remove markdown code blocks
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Replace single quotes with double quotes (but not within strings)
    # This is a simplified approach - convert obvious cases
    text = re.sub(r"'(\w+)':", r'"\1":', text)  # Keys like 'key':

    # Fix missing commas between array elements: "]["  or "}{" or "} {" patterns
    # Add comma between } and { (objects in array)
    text = re.sub(r'\}\s*\{', '}, {', text)

    # Add comma between ] and [ (nested arrays)
    text = re.sub(r'\]\s*\[', '], [', text)

    # Add comma between string and opening brace: "value" {
    text = re.sub(r'"\s*\{', '", {', text)

    # Add comma between } and "
    text = re.sub(r'\}\s*"', '}, "', text)

    # Add comma between ] and "
    text = re.sub(r'\]\s*"', '], "', text)

    # Add comma between number and "
    text = re.sub(r'(\d)\s*\n\s*"', r'\1,\n"', text)

    # Add comma between true/false/null and "
    text = re.sub(r'(true|false|null)\s*\n\s*"', r'\1,\n"', text)

    # Missing comma after string value before next key
    # Pattern: "value"\n    "nextkey":
    text = re.sub(r'"\s*\n(\s*)"([^"]+)":', r'",\n\1"\2":', text)

    # Missing comma after number before next key
    text = re.sub(r'(\d)\s*\n(\s*)"([^"]+)":', r'\1,\n\2"\3":', text)

    # Missing comma after closing bracket before next key
    text = re.sub(r'(\])\s*\n(\s*)"([^"]+)":', r'\1,\n\2"\3":', text)

    # Missing comma after closing brace before next key
    text = re.sub(r'(\})\s*\n(\s*)"([^"]+)":', r'\1,\n\2"\3":', text)

    # Remove trailing commas before ] or }
    text = re.sub(r',\s*\]', ']', text)
    text = re.sub(r',\s*\}', '}', text)

    # Remove control characters that break JSON
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)

    return text


def try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Try multiple strategies to parse JSON from LLM output."""
    if not text:
        return None

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Repair and parse
    repaired = repair_json(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Find JSON object in text (LLM may have added explanation)
    # Look for outermost { } pair
    brace_start = text.find('{')
    brace_end = text.rfind('}')
    if brace_start != -1 and brace_end > brace_start:
        json_candidate = text[brace_start:brace_end + 1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            # Try repairing the extracted JSON
            repaired = repair_json(json_candidate)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    # Strategy 4: Try to extract just the first complete JSON object
    # by counting braces
    if brace_start != -1:
        depth = 0
        in_string = False
        escape = False
        for i, char in enumerate(text[brace_start:], brace_start):
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    json_candidate = text[brace_start:i + 1]
                    repaired = repair_json(json_candidate)
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        break

    return None


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
        # Add JSON instruction to prompt
        json_instruction = "\n\nIMPORTANT: Respond with valid JSON only. No markdown code blocks, no explanation text before or after. Just the raw JSON object."
        if output_schema:
            json_instruction += f"\n\nExpected schema: {json.dumps(output_schema)}"

        full_prompt = prompt + json_instruction

        response = await self.generate(full_prompt, system_prompt)

        # Parse JSON from response using robust parsing
        content = response.content.strip()
        logger.debug(f"Raw LLM response length: {len(content)} chars")

        # Try robust JSON parsing
        result = try_parse_json(content)

        if result is not None:
            logger.info(f"Successfully parsed JSON with {len(result)} top-level keys")
            return result

        # If all parsing strategies failed, log details for debugging
        logger.error(f"Failed to parse LLM JSON response after all repair attempts")
        logger.error(f"Raw response (first 500 chars): {content[:500]}")
        logger.error(f"Raw response (last 300 chars): {content[-300:]}")

        raise ValueError(f"LLM did not return valid JSON after repair attempts")

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
