"""
OpenAI Responses API Provider

Handles GPT-5.x models using the newer Responses API format:
- client.responses.create()
- input (not messages)
- input_text / input_image content types
- response.output_text
"""

import base64

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.services.llm.base import LLMProvider

settings = get_settings()


class OpenAIResponsesProvider(LLMProvider):
    """Provider for OpenAI Responses API (GPT-5.x models)."""

    provider_name = "openai_responses"

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze_image(
        self,
        image_data: bytes,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_output_tokens: int = 8000,
        temperature: float = 0.3,
    ) -> str:
        base64_image = base64.b64encode(image_data).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{base64_image}"

        response = await self.client.responses.create(
            model=model,
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
            max_output_tokens=max_output_tokens,
        )

        content = response.output_text
        if not content:
            raise ValueError("Empty response from OpenAI Responses API")
        return content

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        max_output_tokens: int = 8000,
        temperature: float = 0.1,
    ) -> str:
        input_messages = [{"role": "system", "content": system_prompt}] + messages

        response = await self.client.responses.create(
            model=model,
            input=input_messages,
            max_output_tokens=max_output_tokens,
        )

        content = response.output_text
        if not content:
            raise ValueError("Empty response from OpenAI Responses API on retry")
        return content
