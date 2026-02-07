"""
OpenAI Chat Completions API Provider

Handles GPT-4o, GPT-4o-mini, and other Chat Completions API models:
- client.chat.completions.create()
- messages (not input)
- text / image_url content types
- response.choices[0].message.content
"""

import base64

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.services.llm.base import LLMProvider

settings = get_settings()


class OpenAIChatProvider(LLMProvider):
    """Provider for OpenAI Chat Completions API (GPT-4o, GPT-4o-mini, etc.)."""

    provider_name = "openai_chat"

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

        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                            },
                        },
                    ],
                },
            ],
            max_completion_tokens=max_output_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI Chat Completions API")
        return content

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        max_output_tokens: int = 8000,
        temperature: float = 0.1,
    ) -> str:
        chat_messages = [{"role": "system", "content": system_prompt}] + messages

        response = await self.client.chat.completions.create(
            model=model,
            messages=chat_messages,
            max_completion_tokens=max_output_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI Chat Completions API on retry")
        return content
