"""
Abstract base class for all LLM providers.

Each provider implements the API-specific translation layer.
JSON extraction, parsing, and retry logic are handled by the orchestrator.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    provider_name: str = "base"

    @abstractmethod
    async def analyze_image(
        self,
        image_data: bytes,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_output_tokens: int = 8000,
        temperature: float = 0.3,
    ) -> str:
        """
        Send image + prompts to the LLM and return raw text response.

        Args:
            image_data: Raw image bytes
            system_prompt: The system prompt
            user_prompt: The user prompt
            model: The API model identifier (e.g., "gpt-4o", "gpt-5.2")
            max_output_tokens: Maximum tokens in the response
            temperature: Sampling temperature

        Returns:
            Raw text response from the LLM
        """
        ...

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        max_output_tokens: int = 8000,
        temperature: float = 0.1,
    ) -> str:
        """
        Text-only chat (used for JSON-fix retries).

        Args:
            system_prompt: The system prompt
            messages: List of message dicts with "role" and "content"
            model: The API model identifier
            max_output_tokens: Maximum tokens in the response
            temperature: Sampling temperature

        Returns:
            Raw text response from the LLM
        """
        ...
