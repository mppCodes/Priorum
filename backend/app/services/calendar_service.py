from __future__ import annotations
from app.services.mongo import create_event as mongo_create_event
from app.services import outlook_service
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict, Any

from app.config import get_settings
from app.models.event import Event, EventCreate, EventUpdate
from app.services import outlook_service
from app.services.mongo import (
    list_events_between,
    upsert_event_by_external_id,
    get_event_by_id,
    create_event as mongo_create_event,
    update_event_by_id as mongo_update_event_by_id,
    delete_event_by_id as mongo_delete_event_by_id,
)

settings = get_settings()


def _date_range(period: str, reference: Optional[date] = None) -> Tuple[datetime, datetime]:
    ref = reference or date.today()
    if period == "day":
        start = datetime(ref.year, ref.month, ref.day, 0, 0, 0)
        end = datetime(ref.year, ref.month, ref.day, 23, 59, 59)
    elif period == "week":
        monday = ref - timedelta(days=ref.weekday())
        start = datetime(monday.year, monday.month, monday.day, 0, 0, 0)
        end = start + timedelta(days=7) - timedelta(seconds=1)
    elif period == "month":
        start = datetime(ref.year, ref.month, 1, 0, 0, 0)
        if ref.month == 12:
            end = datetime(ref.year, 12, 31, 23, 59, 59)
        else:
            end = datetime(ref.year, ref.month + 1, 1) - timedelta(seconds=1)
    else:  # "year"
        start = datetime(ref.year, 1, 1, 0, 0, 0)
        end = datetime(ref.year, 12, 31, 23, 59, 59)
    return start, end


def _ms_enabled() -> bool:
    return all([
        bool(getattr(settings, "ms_tenant_id", "")),
        bool(getattr(settings, "ms_client_id", "")),
        bool(getattr(settings, "ms_client_secret", "")),
        bool(getattr(settings, "ms_user_email", "")),
    ])


async def list_events(period: str = "day", date_ref: Optional[str] = None) -> List[Event]:
    """
    1) Si MS Graph está configurado, hace pull y upsert en Mongo por external_id.
    2) Devuelve SIEMPRE los eventos desde Mongo en el rango solicitado (memoria persistente).
    """
    if _ms_enabled():
        try:
            # Pull desde Outlook para mantener Mongo actualizado (upsert por external_id).
            remote_events = await outlook_service.get_events(period=period, date_ref=date_ref)
            for ev in remote_events:
                # Solo upsert si hay external_id o id remoto
                ext_id = getattr(ev, "outlook_id", None) or getattr(ev, "external_id", None) or getattr(ev, "id", None)
                if ext_id:
                    await upsert_event_by_external_id(ext_id, ev)
        except Exception:
            # No bloquea el listado si falla el pull
            pass

    ref = date.fromisoformat(date_ref) if date_ref else date.today()
    start, end = _date_range(period, ref)
    docs = await list_events_between(start, end)
    return [Event.model_validate(d) for d in docs]


async def create_event(data: EventCreate) -> Event:
    """
    Crea evento en Mongo y, si hay MS Graph, también en Outlook.
    Guarda external_id en Mongo para mantener el vínculo.
    """
    # Crear en Mongo primero (garantiza memoria)
    base_doc = data.model_dump(exclude_unset=True)
    # Normaliza estructura a la forma persistida: start/end siempre presentes
    if "start" not in base_doc or "end" not in base_doc:
        # Si tu EventCreate admite date/time/duration, el outlook_service los convertirá.
        # Aquí dejamos que mongo guarde lo que venga; outlook_service devolverá start/end reales si se usa MS.
        pass
    base_doc.setdefault("source", "local")
    base_doc.setdefault("created_at", datetime.utcnow())
    base_doc["updated_at"] = datetime.utcnow()

    created_doc = await mongo_create_event(base_doc)
    created = Event.model_validate(created_doc)

    # Intentar crear en Outlook (si está configurado)
    if _ms_enabled():
        try:
            remote = await outlook_service.create_event(data)
            # external_id puede ser outlook_id o id según lo que devuelva el servicio
            ext_id = getattr(remote, "outlook_id", None) or getattr(remote, "external_id", None) or getattr(remote, "id", None)
            # Actualizar en Mongo con external_id y source "outlook"
            await mongo_update_event_by_id(created.id, {
                "external_id": ext_id,
                "source": "outlook",
                "updated_at": datetime.utcnow(),
            })
            final = await get_event_by_id(created.id)
            if final:
                return Event.model_validate(final)
        except Exception:
            # Si Outlook falla, mantenemos el local
            pass

    return created


async def update_event(event_id: str, data: EventUpdate) -> Event:
    """
    Actualiza evento en Mongo y, si está vinculado y MS Graph está configurado, actualiza en Outlook.
    """
    payload = data.model_dump(exclude_unset=True)
    payload["updated_at"] = datetime.utcnow()

    updated_doc = await mongo_update_event_by_id(event_id, payload)
    if not updated_doc:
        raise ValueError("Event not found")

    if _ms_enabled():
        try:
            existing = await get_event_by_id(event_id)
            ext_id = existing.get("external_id") if existing else None
            if ext_id:
                await outlook_service.update_event(ext_id, data)
                await mongo_update_event_by_id(event_id, {"updated_at": datetime.utcnow()})
                final = await get_event_by_id(event_id)
                if final:
                    return Event.model_validate(final)
        except Exception:
            pass

    return Event.model_validate(updated_doc)


async def delete_event(event_id: str) -> None:
    """
    Borra en Outlook (si procede) y en Mongo.
    """
    existing = await get_event_by_id(event_id)
    if not existing:
        return None
    ext_id = existing.get("external_id")

    if _ms_enabled() and ext_id:
        try:
            await outlook_service.delete_event(ext_id)
        except Exception:
            # Si falla Outlook, continuamos con borrado local
            pass

    await mongo_delete_event_by_id(event_id)
    return None


async def sync_from_outlook() -> int:
    """
    Pull de eventos desde Outlook (si hay MS Graph) y upsert en Mongo por external_id.
    Devuelve número de items procesados (aproximado).
    """
    if not _ms_enabled():
        return 0
    try:
        # Por defecto intenta el día actual; puedes ampliar con period/date_ref si quieres
        remote_events = await outlook_service.get_events(period="day", date_ref=None)
        count = 0
        for ev in remote_events:
            ext_id = getattr(ev, "outlook_id", None) or getattr(ev, "external_id", None) or getattr(ev, "id", None)
            if ext_id:
                await upsert_event_by_external_id(ext_id, ev)
                count += 1
        return count
    except Exception:
        return 0

async def seed_mock_events(period: str = "day", date_ref: Optional[str] = None) -> int:
    """
    Inserta en Mongo los eventos que devuelve outlook_service.get_events.
    Con Graph no configurado, eso serán los mocks.
    """
    evs = await outlook_service.get_events(period=period, date_ref=date_ref)
    count = 0
    for ev in evs:
        doc = ev.model_dump(exclude_unset=True)
        # Fuente y timestamps
        doc.setdefault("source", "mock")
        now = datetime.utcnow()
        doc.setdefault("created_at", now)
        doc["updated_at"] = now
        await mongo_create_event(doc)
        count += 1
    return count
