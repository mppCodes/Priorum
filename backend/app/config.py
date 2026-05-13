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
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.3

    # ── CORS ───────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        # Busca .env en la raíz del proyecto; si no existe, busca en backend/
        env_file = (str(_ROOT / ".env"), ".env")
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()