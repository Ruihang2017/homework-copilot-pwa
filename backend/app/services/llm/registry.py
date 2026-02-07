"""
Model Registry

Maps model IDs to their metadata and provider types.
Used by the orchestrator to select the correct provider per request.
"""

from app.services.llm.base import LLMProvider


# ── Model Registry ────────────────────────────────────────────────────────────
# Each entry maps a user-facing model_id to:
#   - display_name: Human-readable name for the frontend
#   - provider:     Which LLMProvider class to use
#   - api_model:    The actual model string sent to the provider API
#   - supports_vision: Whether the model supports image analysis
#   - tier:         Pricing tier for frontend display

MODEL_REGISTRY: dict[str, dict] = {
    # ── OpenAI Responses API (GPT-5.x) ──
    "gpt-5.2": {
        "display_name": "GPT-5.2 (Premium)",
        "provider": "openai_responses",
        "api_model": "gpt-5.2",
        "supports_vision": True,
        "tier": "premium",
        "description": "Most capable model. Best reasoning but slowest (~30s). Use for complex or multi-step problems.",
    },
    "gpt-5-mini": {
        "display_name": "GPT-5 Mini",
        "provider": "openai_responses",
        "api_model": "gpt-5-mini",
        "supports_vision": True,
        "tier": "standard",
        "description": "Good balance of quality and speed (~15-20s). Suitable for most homework questions.",
    },
    # ── OpenAI Chat Completions API (GPT-4o) ──
    "gpt-4o": {
        "display_name": "GPT-4o",
        "provider": "openai_chat",
        "api_model": "gpt-4o",
        "supports_vision": True,
        "tier": "standard",
        "description": "Fast and reliable (~15-25s). Strong vision support. Recommended default.",
    },
    "gpt-4o-mini": {
        "display_name": "GPT-4o Mini (Budget)",
        "provider": "openai_chat",
        "api_model": "gpt-4o-mini",
        "supports_vision": True,
        "tier": "budget",
        "description": "Fastest and cheapest (~5-10s). Good for simple questions. May struggle with complex problems.",
    },
}

# Default model when nothing else is specified
DEFAULT_MODEL_ID = "gpt-4o"


# ── Provider Factory ──────────────────────────────────────────────────────────

# Provider class registry (lazy-loaded singletons)
_provider_instances: dict[str, LLMProvider] = {}


def _create_provider(provider_type: str) -> LLMProvider:
    """Create a provider instance by type string."""
    if provider_type == "openai_responses":
        from app.services.llm.openai_responses import OpenAIResponsesProvider
        return OpenAIResponsesProvider()
    elif provider_type == "openai_chat":
        from app.services.llm.openai_chat import OpenAIChatProvider
        return OpenAIChatProvider()
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


def get_provider(model_id: str) -> tuple[LLMProvider, str]:
    """
    Get the provider instance and API model name for a given model_id.

    Args:
        model_id: The user-facing model identifier (e.g., "gpt-4o")

    Returns:
        Tuple of (provider_instance, api_model_name)

    Raises:
        ValueError: If the model_id is not in the registry
    """
    if model_id not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model: {model_id}. "
            f"Available models: {', '.join(MODEL_REGISTRY.keys())}"
        )

    model_info = MODEL_REGISTRY[model_id]
    provider_type = model_info["provider"]

    # Lazy singleton creation
    if provider_type not in _provider_instances:
        _provider_instances[provider_type] = _create_provider(provider_type)

    return _provider_instances[provider_type], model_info["api_model"]


def list_models() -> list[dict]:
    """
    Return the list of available models for the frontend.

    Returns:
        List of dicts with id, display_name, tier, supports_vision, description
    """
    return [
        {
            "id": model_id,
            "display_name": info["display_name"],
            "tier": info["tier"],
            "supports_vision": info["supports_vision"],
            "description": info.get("description", ""),
        }
        for model_id, info in MODEL_REGISTRY.items()
    ]
