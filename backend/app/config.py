# app/config.py
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    # App
    app_name: str = "Priorum"
    api_prefix: str = "/api"

    # ── Notion ─────────────────────────────────────────────────────
    notion_api_key: str = ""
    notion_tasks_database_id: str = ""

    # ── Microsoft Graph (Outlook / Teams) ──────────────────────────
    ms_tenant_id: str = ""
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_user_email: str = ""          # UPN del usuario cuyo calendario se lee

    # ── OpenAI / LLM ───────────────────────────────────────────────
    openai_api_key: str = ""
    openai_base_url: str = ""  # URL base personalizada (proxy/gateway)
    openai_model: str = ""
    openai_temperature: float = 0.3
    # Embeddings para RAG (usado por Qdrant)
    openai_embedding_model: str = "text-embedding-3-small"

    # ── CORS ───────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    debug: bool = False

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "priorum"

    mongo_tasks_collection: str = "tasks"
    mongo_events_collection: str = "events"
    mongo_tasks_cache_collection: str = "tasks_cache"
    mongo_events_cache_collection: str = "events_cache"
    mongo_agent_logs_collection: str = "agent_logs"

    # TTL opcional en segundos (0 = desactivado)
    mongo_cache_ttl_seconds: int = 0          # p.ej., 21600 (6 horas)
    mongo_agent_logs_ttl_seconds: int = 0     # p.ej., 2592000 (30 días)

    # ── Vector store (Qdrant / RAG) ────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "priorum_rag"

    # ── Jira ────────────────────────────────────────────────────────────────────
    jira_email: str = ""
    jira_api_token: str = ""

    class Config:
        # Busca .env en la raíz del proyecto; si no existe, busca en backend/
        env_file = (str(_ROOT / ".env"), ".env")
        env_file_encoding = "utf-8"


@lru_cache
    mongo_agent_msgs_collection: str = "agent_msgs"

    mongo_cache_ttl_seconds: int = 0
    mongo_agent_logs_ttl_seconds: int = 0

    # Notion (opcional)
    notion_api_key: Optional[str] = None
    notion_tasks_database_id: Optional[str] = None

    # Microsoft Graph (opcional)
    ms_tenant_id: Optional[str] = None
    ms_client_id: Optional[str] = None
    ms_client_secret: Optional[str] = None
    ms_user_email: Optional[str] = None

    # OpenAI (opcional)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5-chat-nextai"
    openai_temperature: float = 0.2

    # CORS
    cors_origins: List[str] = []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        """
        Admite:
        - JSON: ["http://localhost:3000","http://localhost:5173"]
        - Coma-separado: http://localhost:3000,http://localhost:5173
        - Vacío -> []
        """
        if v is None:
            return []
        if isinstance(v, list):
            # Ya es lista
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("[") and s.endswith("]"):
                # Intentar JSON
                try:
                    data = json.loads(s)
                    if isinstance(data, list):
                        # Normaliza elementos a str
                        return [str(item).strip() for item in data if str(item).strip()]
                except Exception:
                    # Fallback a coma-separado si el JSON no es válido
                    pass
            # Coma-separado
            return [item.strip() for item in s.split(",") if item.strip()]
        # Cualquier otra cosa, devolver tal cual y que Pydantic valide
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
