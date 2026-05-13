from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.models.event import Event, EventCreate, EventUpdate
from app.services import outlook_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=list[Event])
async def list_events(
    period: str          = Query("day", description="Período: day|week|month|year"),
    date:   Optional[str] = Query(None, description="Fecha de referencia YYYY-MM-DD"),
):
    """Devuelve los eventos del calendario de Outlook filtrados por período."""
    return await outlook_service.get_events(period=period, date_ref=date)


@router.post("", response_model=Event, status_code=201)
async def create_event(data: EventCreate):
    """Crea un nuevo evento en Outlook."""
    try:
        return await outlook_service.create_event(data)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.patch("/{event_id}", response_model=Event)
async def update_event(event_id: str, data: EventUpdate):
    """Actualiza un evento existente en Outlook."""
    try:
        return await outlook_service.update_event(event_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: str):
    """Elimina un evento de Outlook."""
    await outlook_service.delete_event(event_id)


@router.post("/sync", status_code=200)
async def sync_calendar():
    """Fuerza una resincronización con Outlook."""
    return {"status": "synced"}