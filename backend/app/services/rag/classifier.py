"""
Quick Topic Classifier

A lightweight first-pass that sends the homework image to a cheap, fast model
(gpt-4o-mini) to identify the math topic in a few words.

Why this exists:
- To query ChromaDB, we need a text string describing the topic
  (e.g., "adding fractions with unlike denominators")
- The main LLM analysis is too slow and expensive just for topic detection
- gpt-4o-mini is fast (~2-3s) and cheap (~$0.001 per call)
- The returned topic string becomes the ChromaDB search query
"""

import base64

from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()

# Classification prompt — intentionally minimal for speed
CLASSIFY_PROMPT = (
    "Look at this homework image. "
    "What specific math topic is this question about? "
    "Reply in 5-10 words only. Example: 'adding fractions with unlike denominators'"
)


async def classify_topic(image_data: bytes) -> str:
    """
    Quickly classify the homework image topic using gpt-4o-mini.

    Args:
        image_data: Raw image bytes of the homework question

    Returns:
        A short string describing the topic (e.g., "simplifying algebraic expressions")
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    base64_image = base64.b64encode(image_data).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{base64_image}"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CLASSIFY_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                },
            ],
            max_completion_tokens=50,
            temperature=0.0,
        )

        topic = response.choices[0].message.content
        if topic:
            topic = topic.strip().strip('"').strip("'")
            print(f"[RAG Classifier] Detected topic: {topic}")
            return topic

    except Exception as e:
        print(f"[RAG Classifier] Classification failed: {e}")

    # Fallback — generic query that still returns useful chunks
    return "mathematics homework question"
