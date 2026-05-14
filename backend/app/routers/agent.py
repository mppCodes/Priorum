import json
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.models.agent import (
    ChatRequest, ChatResponse,
    PrioritiesRequest, PrioritiesResponse,
    ScheduleRequest, ScheduleResponse,
    HistoryResponse,
)
from app.services import ai_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Envía un mensaje al agente IA y obtiene una respuesta."""
    return await ai_agent_service.chat(req.message, req.context)


@router.post("/priorities", response_model=PrioritiesResponse)
async def get_priorities(req: PrioritiesRequest):
    """Genera la lista de prioridades del día usando el agente IA."""
    return await ai_agent_service.get_priorities(req)


@router.post("/schedule", response_model=ScheduleResponse)
async def get_schedule(req: ScheduleRequest):
    """Genera una sugerencia de distribución del horario del día."""
    return await ai_agent_service.get_schedule(req)


@router.get("/history", response_model=HistoryResponse)
async def get_history():
    """Devuelve el historial de conversación con el agente."""
    return HistoryResponse(messages=ai_agent_service.get_history())


@router.delete("/history", status_code=204)
async def clear_history():
    """Limpia el historial de conversación."""
    ai_agent_service.clear_history()


# ── Tasks Agent (openai-agents SDK) ──────────────────────────────────────────

class TasksAgentRequest(BaseModel):
    message: str = "Analiza todas mis tareas pendientes de hoy y esta semana."


class TasksAgentResponse(BaseModel):
    result: dict | str
    error: str | None = None


@router.post("/tasks-analysis", response_model=TasksAgentResponse)
async def run_tasks_agent(req: TasksAgentRequest):
    """Ejecuta el Tasks Agent y devuelve el análisis estructurado de tareas."""
    try:
        from agents import Runner
        from app.agents.tasks_agent import tasks_agent

        run_result = await Runner.run(tasks_agent, req.message)

        # Intentar parsear la salida como JSON
        try:
            parsed = json.loads(run_result.final_output)
            return TasksAgentResponse(result=parsed)
        except (json.JSONDecodeError, TypeError):
            return TasksAgentResponse(result=run_result.final_output)

    except Exception as e:
        logger.exception("Error ejecutando Tasks Agent")
        return TasksAgentResponse(result={}, error=f"{type(e).__name__}: {e}")
