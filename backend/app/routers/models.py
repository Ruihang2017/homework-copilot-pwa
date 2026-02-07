"""
Models Router

Exposes the available AI models to the frontend.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.llm.registry import list_models


router = APIRouter()


class ModelInfo(BaseModel):
    id: str
    display_name: str
    tier: str
    supports_vision: bool
    description: str


@router.get("", response_model=list[ModelInfo])
async def get_available_models():
    """Return the list of available AI models."""
    return list_models()
