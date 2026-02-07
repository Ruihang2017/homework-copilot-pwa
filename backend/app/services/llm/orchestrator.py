"""
LLM Orchestrator

Shared logic for all providers:
- JSON extraction from LLM responses
- Retry with JSON-fix on parse failure
- Parsing raw text into AnalysisResponse

The orchestrator delegates the actual API call to the selected provider,
keeping provider implementations clean and focused on API translation.
"""

import json
import re

from app.services.llm.models import AnalysisResponse
from app.services.llm.registry import get_provider, DEFAULT_MODEL_ID


class LLMOrchestrator:
    """Orchestrates LLM calls with shared parsing and retry logic."""

    async def analyze_homework_image(
        self,
        image_data: bytes,
        system_prompt: str,
        user_prompt: str,
        model_id: str | None = None,
    ) -> AnalysisResponse:
        """
        Analyze a homework image using the specified (or default) model.

        Args:
            image_data: Raw image bytes
            system_prompt: The policy-compiled system prompt
            user_prompt: The analysis instructions
            model_id: Optional model identifier; falls back to DEFAULT_MODEL_ID

        Returns:
            Parsed AnalysisResponse
        """
        model_id = model_id or DEFAULT_MODEL_ID
        provider, api_model = get_provider(model_id)

        # Call the provider
        content = await provider.analyze_image(
            image_data=image_data,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=api_model,
            max_output_tokens=8000,
            temperature=0.3,
        )

        print(f"[LLM] model={model_id} provider={provider.provider_name}")
        print(f"[LLM] Content: {content[:200]}...")

        # Extract and parse JSON
        json_str = self._extract_json(content)

        try:
            data = json.loads(json_str)
            return AnalysisResponse(**data)
        except (json.JSONDecodeError, ValueError) as e:
            # Retry with explicit JSON request
            return await self._retry_with_json_fix(
                provider, api_model, system_prompt, user_prompt, content, str(e)
            )

    def _extract_json(self, content: str) -> str:
        """Extract JSON from response, handling markdown code blocks."""
        # Try to find JSON in code blocks
        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(code_block_pattern, content)
        if matches:
            return matches[0].strip()

        # Try to find raw JSON object
        json_pattern = r"\{[\s\S]*\}"
        matches = re.findall(json_pattern, content)
        if matches:
            # Return the longest match (most likely the full JSON)
            return max(matches, key=len)

        # Return as-is and let JSON parser handle it
        return content.strip()

    async def _retry_with_json_fix(
        self,
        provider,
        api_model: str,
        system_prompt: str,
        user_prompt: str,
        previous_response: str,
        error: str,
    ) -> AnalysisResponse:
        """Retry analysis with a fix prompt when JSON parsing fails."""
        fix_prompt = (
            f"Your previous response was not valid JSON. The error was: {error}\n\n"
            f"Please fix the JSON and respond with ONLY valid JSON, no markdown code blocks or explanation.\n"
            f"Your previous response was:\n{previous_response[:500]}...\n\n"
            f"Respond with the corrected JSON only."
        )

        messages = [
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": previous_response},
            {"role": "user", "content": fix_prompt},
        ]

        content = await provider.chat(
            system_prompt=system_prompt,
            messages=messages,
            model=api_model,
            max_output_tokens=8000,
            temperature=0.1,
        )

        print(f"[LLM] Retry content: {content[:200]}...")
        json_str = self._extract_json(content)
        data = json.loads(json_str)
        return AnalysisResponse(**data)


# ── Singleton ─────────────────────────────────────────────────────────────────

_orchestrator: LLMOrchestrator | None = None


def get_orchestrator() -> LLMOrchestrator:
    """Get or create the LLM orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LLMOrchestrator()
    return _orchestrator
