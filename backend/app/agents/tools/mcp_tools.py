"""
MCP Tools – wraps tools exposed by external MCP servers as openai-agents function_tools.

At startup, connects to the configured Jira MCP server, discovers available tools
and generates async wrappers compatible with the openai-agents SDK.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agents import function_tool
from fastmcp import Client

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


async def _call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Generic helper: opens a short-lived MCP client session, calls a tool and returns JSON."""
    try:
        async with Client(settings.jira_mcp_url) as client:
            result = await client.call_tool(tool_name, arguments)
            # result.data can be a dict, list or primitive
            return json.dumps(result.data, default=str, ensure_ascii=False)
    except Exception as exc:
        logger.error("Error calling MCP tool '%s': %s", tool_name, exc)
        return json.dumps({"error": str(exc)})


# ── Jira tools ────────────────────────────────────────────────────────────────

@function_tool(strict_mode=False)
async def crear_tarjeta_jira(
    titulo: str,
    prioridad: str = "media",
    proyecto: str = "",
    fecha_limite: str = "",
    etiquetas: list[str] | None = None,
) -> str:
    """Crea una tarjeta (issue) en Jira a través del servidor MCP.

    Args:
        titulo: Título de la tarea o issue a crear en Jira.
        prioridad: Nivel de prioridad ('alta', 'media', 'baja').
        proyecto: Nombre del proyecto al que pertenece la tarea.
        fecha_limite: Fecha límite en formato 'YYYY-MM-DD'.
        etiquetas: Lista de etiquetas para clasificar la tarea.

    Returns:
        JSON con el resultado de la creación en Jira.
    """
    return await _call_mcp_tool(
        "crear_tarjeta_jira",
        {
            "titulo": titulo,
            "prioridad": prioridad,
            "proyecto": proyecto,
            "fecha_limite": fecha_limite,
            "etiquetas": etiquetas or [],
        },
    )


# ── Registry: all MCP-backed tools exported for agents ───────────────────────

MCP_TOOLS = [crear_tarjeta_jira]