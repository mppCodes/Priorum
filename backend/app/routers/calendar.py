from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List

from app.models.event import Event, EventCreate, EventUpdate
from app.services import calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=List[Event])
async def list_events(
    period: str = Query("day", description="Período: day|week|month|year"),
    date: Optional[str] = Query(None, description="Fecha de referencia YYYY-MM-DD"),
):
    """
    Devuelve los eventos persistidos en Mongo filtrados por período.
    Si MS Graph está configurado, hace un pull previo para upsert (memoria + sincronización).
    """
    try:
        return await calendar_service.list_events(period=period, date_ref=date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=Event, status_code=201)
async def create_event(data: EventCreate):
    """
    Crea un evento en Mongo y, si MS Graph está configurado, también en Outlook (guardando external_id).
    """
    try:
        return await calendar_service.create_event(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{event_id}", response_model=Event)
async def update_event(event_id: str, data: EventUpdate):
    """
    Actualiza un evento en Mongo y, si tiene external_id y MS Graph está configurado, lo sincroniza en Outlook.
    """
    try:
        return await calendar_service.update_event(event_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: str):
    """
    Borra el evento en Mongo y, si tiene external_id y MS Graph está configurado, también en Outlook.
    """
    try:
        await calendar_service.delete_event(event_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", status_code=200)
async def sync_calendar():
    """
    Fuerza una resincronización desde Outlook (si está configurado): pull + upserts en Mongo.
    """
    try:
        count = await calendar_service.sync_from_outlook()
        return {"status": "synced", "imported_or_updated": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/seed-mocks", status_code=201)
async def seed_mocks(
    period: str = Query("day"),
    date: Optional[str] = Query(None),
):
    """
    Inserta en Mongo los eventos mock (o los de Outlook si estuviera configurado).
    Útil para crear datos persistentes de prueba.
    """
    try:
        n = await calendar_service.seed_mock_events(period=period, date_ref=date)
        return {"inserted": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
