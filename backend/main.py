import logging
import logging_config  # noqa: F401 – configura logging antes de cualquier otra importación
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import tasks, calendar, agent
from logging_config import setup_logging
from app.services.mongo import init_db

# Importa los routers como objetos APIRouter
from app.routers.tasks import router as tasks_router
from app.routers.calendar import router as calendar_router
from app.routers.agent import router as agent_router
# Opcional: diagnósticos
from app.routers.diagnostics import router as diagnostics_router

# MCP server (Jira) – montado como sub-aplicación ASGI
from app.services.jira_mcp_server import mcp as jira_mcp

logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
settings = get_settings()

# Build the MCP ASGI app once so we can reference its lifespan
_mcp_app = jira_mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Re-aplicar tras el arranque de uvicorn (que añade sus propios handlers)
    setup_logging()
    logger.info("Jira MCP server mounted at /mcp")
    # Run the MCP app's lifespan so its internal task group is initialized
    async with _mcp_app.lifespan(_mcp_app):
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

# Startup: inicializa MongoDB (índices incluidos)
@app.on_event("startup")
async def startup() -> None:
    await init_db()

# Routers
app.include_router(tasks_router,    prefix=settings.api_prefix)
app.include_router(calendar_router, prefix=settings.api_prefix)
app.include_router(agent_router,    prefix=settings.api_prefix)
app.include_router(diagnostics_router, prefix=settings.api_prefix)  # opcional

# Mount Jira MCP server as an ASGI sub-application at /mcp
# Accessible at http://localhost:8000/mcp/  (same process, same port)
app.mount("/mcp", _mcp_app)

# Health simple
@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
