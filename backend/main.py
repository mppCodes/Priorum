import logging_config  # noqa: F401 – configura logging antes de cualquier otra importación
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import tasks, calendar, agent
from logging_config import setup_logging

# ── App ───────────────────────────────────────────────────────────────────────
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Re-aplicar tras el arranque de uvicorn (que añade sus propios handlers)
    setup_logging()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API backend de Priorum – integración Notion + Outlook + Agente IA",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(tasks.router,    prefix=settings.api_prefix)
app.include_router(calendar.router, prefix=settings.api_prefix)
app.include_router(agent.router,    prefix=settings.api_prefix)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}