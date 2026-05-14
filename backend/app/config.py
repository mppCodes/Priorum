from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Raíz del proyecto (dos niveles arriba de este fichero: backend/app/config.py → raíz)
_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────
    app_name: str = "Priorum API"
    debug: bool = False
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

    # ── Base de datos (MongoDB) ────────────────────────────────────
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "priorum"

    # Colecciones principales (operacionales)
    mongo_tasks_collection: str = "tasks"
    mongo_events_collection: str = "events"
    mongo_agent_msgs_collection: str = "agent_messages"

    # Colecciones de caché (fuentes externas)
    mongo_tasks_cache_collection: str = "tasks_cache"     # caché de Notion
    mongo_events_cache_collection: str = "events_cache"   # caché de Outlook/Graph

    # Colección de logs del agente
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
    jira_mcp_url: str = "http://127.0.0.1:8000/mcp/"

    class Config:
        # Busca .env en la raíz del proyecto; si no existe, busca en backend/
        env_file = (str(_ROOT / ".env"), ".env")
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
