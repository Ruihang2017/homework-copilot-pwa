"""
OpenAI Client Service

Handles communication with OpenAI API for image analysis.
"""

import base64
import json
import re
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()


class Hint(BaseModel):
    stage: int
    text: str


class ParentContext(BaseModel):
    what_it_tests: list[str]
    key_idea: str


class AnalysisResponse(BaseModel):
    subject: str
    topic: str
    parent_context: ParentContext
    hints: list[Hint]
    common_mistakes: list[str]


class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def analyze_homework_image(
        self,
        image_data: bytes,
        system_prompt: str,
        user_prompt: str,
    ) -> AnalysisResponse:
        """
        Analyze a homework image using OpenAI vision model.

        Args:
            image_data: Raw image bytes
            system_prompt: The policy-compiled system prompt
            user_prompt: The analysis instructions

        Returns:
            Parsed AnalysisResponse
        """
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Determine image type (assume JPEG for now)
        image_url = f"data:image/jpeg;base64,{base64_image}"

        # Call the API
        response = await self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": user_prompt,
                        },
                        {
                            "type": "input_image",
                            "image_url": image_url,
                        },
                    ],
                },
            ],
            max_output_tokens=8000,
            temperature=0.3,  # Lower temperature for more consistent outputs
        )

        # Parse the response
        content = response.output_text
        if not content:
            raise ValueError("Empty response from OpenAI")
        print(f"Content: {content}")
        # Extract JSON from response (handle potential markdown code blocks)
        json_str = self._extract_json(content)

        # Parse and validate
        try:
            data = json.loads(json_str)
            return AnalysisResponse(**data)
        except (json.JSONDecodeError, ValueError) as e:
            # Retry with explicit JSON request
            return await self._retry_with_json_fix(
                system_prompt, user_prompt, content, str(e)
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
        system_prompt: str,
        user_prompt: str,
        previous_response: str,
        error: str,
    ) -> AnalysisResponse:
        """Retry analysis with a fix prompt when JSON parsing fails."""
        fix_prompt = f"""Your previous response was not valid JSON. The error was: {error}

Please fix the JSON and respond with ONLY valid JSON, no markdown code blocks or explanation.
Your previous response was:
{previous_response[:500]}...

Respond with the corrected JSON only."""

        response = await self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": previous_response},
                {"role": "user", "content": fix_prompt},
            ],
            max_output_tokens=8000,
            temperature=0.1,
        )

        content = response.output_text
        if not content:
            raise ValueError("Empty response from OpenAI on retry")
        print(f"Content: {content}")
        json_str = self._extract_json(content)
        data = json.loads(json_str)
        return AnalysisResponse(**data)


# Singleton instance
_client: OpenAIClient | None = None


def get_openai_client() -> OpenAIClient:
    """Get or create the OpenAI client singleton."""
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client
