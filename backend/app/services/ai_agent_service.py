"""
Servicio del agente IA.
Delega al orquestador de agentes (openai-agents SDK) para priorización
y al Chat Agent para conversación.
Mantiene fallback a OpenAI directo / mocks cuando las keys no están configuradas.
"""
from typing import Any
from datetime import datetime, timezone
import json
import logging

from app.config import get_settings
from app.models.agent import (
    ChatMessage, ChatResponse,
    PrioritiesRequest, PrioritiesResponse, PriorityItem,
    ScheduleRequest, ScheduleResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Historial de conversación en memoria (por sesión de servidor)
_chat_history: list[ChatMessage] = []


# ── Chat (delegado al Chat Agent) ───────────────────────────────────────────

async def chat(message: str, context: dict[str, Any]) -> ChatResponse:
    """Responde a un mensaje del usuario usando el Chat Agent con memoria."""
    if not settings.openai_api_key:
        return _mock_chat(message)

    try:
        from app.agents.chat_agent import run_chat_agent

        # Convertir historial a formato de mensajes para el agente
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in _chat_history[-20:]  # últimos 20 mensajes (10 turnos)
        ]

        reply = await run_chat_agent(message, context, history=history)
    except Exception as exc:
        logger.exception("Error en Chat Agent, fallback a respuesta simple")
        reply = f"Error procesando tu mensaje: {exc}"

    now = datetime.now(timezone.utc)
    _chat_history.append(ChatMessage(role="user",  content=message, timestamp=now))
    _chat_history.append(ChatMessage(role="agent", content=reply,   timestamp=now))

    return ChatResponse(message=reply, timestamp=now)


# ── Prioridades (delegado al Orquestador) ────────────────────────────────────

async def get_priorities(req: PrioritiesRequest) -> PrioritiesResponse:
    """Genera la lista de prioridades del día usando el orquestador de agentes."""
    if not settings.openai_api_key:
        return _mock_priorities(req)

    try:
        from app.agents.orchestrator import run_orchestrator
        result = await run_orchestrator(target_date=req.date)

        # Mapear el output del orquestador al modelo PrioritiesResponse
        priorities = []
        for p in result.get("priorities", []):
            priorities.append(PriorityItem(
                rank=p.get("rank", 0),
                title=p.get("title", ""),
                why=p.get("why", ""),
                time=f"{p.get('estimated_minutes', 30)} min",
                tag=p.get("priority_tag", "media"),
            ))

        return PrioritiesResponse(
            priorities=priorities,
            reasoning=result.get("reasoning", ""),
        )
    except Exception as exc:
        logger.exception("Error en Orquestador, fallback a mock")
        return _mock_priorities(req)


# ── Schedule (delegado al Orquestador) ───────────────────────────────────────

async def get_schedule(req: ScheduleRequest) -> ScheduleResponse:
    """Genera una sugerencia de horario para el día usando el orquestador."""
    if not settings.openai_api_key:
        return ScheduleResponse(reasoning="Configura OPENAI_API_KEY para obtener sugerencias de horario.")

    try:
        from app.agents.orchestrator import run_orchestrator
        result = await run_orchestrator(target_date=req.date)

        return ScheduleResponse(
            schedule=result.get("schedule", []),
            reasoning=result.get("reasoning", ""),
        )
    except Exception as exc:
        logger.exception("Error en Orquestador para schedule, fallback")
        return ScheduleResponse(reasoning=f"Error generando horario: {exc}")


# ── Historial ────────────────────────────────────────────────────────────────

def get_history() -> list[ChatMessage]:
    return list(_chat_history)


def clear_history() -> None:
    _chat_history.clear()


# ── Mocks para desarrollo sin API key ──────────────────────────────────────────

def _mock_chat(message: str) -> ChatResponse:
    reply = (
        "Soy Priorum, tu asistente de productividad. "
        "Para activar el agente IA, configura OPENAI_API_KEY en el archivo .env. "
        f'Recibí tu mensaje: "{message}"'
    )
    now = datetime.utcnow()
    _chat_history.append(ChatMessage(role="user",  content=message, timestamp=now))
    _chat_history.append(ChatMessage(role="agent", content=reply,   timestamp=now))
    return ChatResponse(message=reply, timestamp=now)


def _mock_priorities(req: PrioritiesRequest) -> PrioritiesResponse:
    tasks = req.tasks[:3]
    priorities = [
        PriorityItem(
            rank=i + 1,
            title=t.get("title", f"Tarea {i+1}"),
            why="Prioridad calculada en modo demo (sin API key).",
            time="30 min",
            tag=t.get("priority", "media"),
        )
        for i, t in enumerate(tasks)
    ]
    return PrioritiesResponse(
        priorities=priorities,
        reasoning="Modo demo activo. Configura OPENAI_API_KEY para obtener prioridades reales.",
    )
