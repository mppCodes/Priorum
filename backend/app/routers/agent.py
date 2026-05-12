from fastapi import APIRouter

from app.models.agent import (
    ChatRequest, ChatResponse,
    PrioritiesRequest, PrioritiesResponse,
    ScheduleRequest, ScheduleResponse,
    HistoryResponse,
)
from app.services import ai_agent_service

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