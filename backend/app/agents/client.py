"""Shared OpenAI client for all agents."""
from __future__ import annotations

from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

openai_client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url if settings.openai_base_url else None,
    default_headers={
        "provider": "AzureOpenAI",
        "origin": "Priorum",
        "origin-detail": "Priorum-Agents",
    },
)

MODEL_NAME = settings.openai_model or "gpt-4o-nextai"