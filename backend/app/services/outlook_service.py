"""
Servicio de integración con Microsoft Graph API (Outlook / Teams).
Gestiona eventos del calendario del usuario.
"""
from __future__ import annotations

from typing import Optional, List, Any, Dict
from datetime import date, datetime, timedelta, timezone
import uuid
import logging

from app.config import get_settings
from app.models.event import Event, EventCreate, EventUpdate, EventType

settings = get_settings()
logger = logging.getLogger(__name__)

# Cache simple del token (reservado si quisieras extenderlo)
_token_cache: dict = {}


def _looks_like_uuid(value: str) -> bool:
    """Detecta si un valor parece un UUID (Secret ID en lugar de Secret Value)."""
    import re
    return bool(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value, re.I))


def _get_access_token() -> str:
    """Obtiene un token de acceso para Microsoft Graph usando MSAL."""
    import msal

    if settings.ms_client_secret and _looks_like_uuid(settings.ms_client_secret):
        raise RuntimeError(
            "MS_CLIENT_SECRET parece un Secret ID (UUID), no un Secret Value. "
            "En Azure Portal → App Registrations → Certificates & Secrets, "
            "copia el campo 'Value' (no el 'Secret ID') y actualiza MS_CLIENT_SECRET en .env"
        )

    app = msal.ConfidentialClientApplication(
        client_id=settings.ms_client_id,
        client_credential=settings.ms_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.ms_tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        error_desc = result.get("error_description", "")
        if "AADSTS7000215" in error_desc:
            raise RuntimeError(
                "AADSTS7000215 – MS_CLIENT_SECRET contiene el Secret ID, no el Secret Value. "
                "Ve a Azure Portal → App Registrations → tu app → Certificates & Secrets "
                "y copia el campo 'Value' (la cadena larga, no el UUID)."
            )
        raise RuntimeError(f"Error obteniendo token MS Graph: {error_desc}")
    return result["access_token"]


def _graph_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


def _pick_event_type(categories: List[str]) -> EventType:
    """
    Selecciona un EventType válido según categorías de Graph.
    Tolera enums con nombres distintos y hace fallback al primer miembro si no encuentra coincidencia.
    """
    cats = [c.lower() for c in (categories or [])]

    candidates = []
    if "personal" in cats:
        candidates.append("personal")
    if "bloqueo" in cats or "block" in cats or "busy" in cats:
        candidates.append("bloqueo")
    # reuniones comunes
    candidates += ["reunion", "meeting"]

    for name in candidates:
        if hasattr(EventType, name):
            return getattr(EventType, name)

    # Fallback: primer miembro del enum
    return next(iter(EventType))


def _normalize_attendees_for_model(att: Optional[List[Any]]) -> List[Dict[str, str]]:
    """
    Convierte asistentes a dicts {"name":..., "email":...} para que Pydantic cree Attendee.
    Acepta strings (emails), dicts o objetos con atributos name/email.
    """
    out: List[Dict[str, str]] = []
    for a in att or []:
        name = ""
        email = ""
        if isinstance(a, str):
            email = a
            name = a.split("@")[0].title() if "@" in a else a
        elif isinstance(a, dict):
            name = str(a.get("name") or "")
            email = str(a.get("email") or a.get("address") or "")
        else:
            email = str(getattr(a, "email", "") or "")
            name = str(getattr(a, "name", "") or "")
        out.append({"name": name, "email": email})
    return out


def _normalize_attendees_for_graph(att: Optional[List[Any]]) -> List[Dict[str, Any]]:
    """
    Convierte asistentes a la forma de Graph:
    [{"emailAddress": {"address": email, "name": name}, "type": "required"}, ...]
    """
    out: List[Dict[str, Any]] = []
    for a in att or []:
        name = None
        email = None
        if isinstance(a, str):
            email = a
            name = a.split("@")[0].title() if "@" in a else a
        elif isinstance(a, dict):
            name = a.get("name")
            email = a.get("email") or a.get("address")
        else:
            email = getattr(a, "email", None)
            name = getattr(a, "name", None)
        if email or name:
            out.append({"emailAddress": {"address": email or "", "name": name or (email or "")}, "type": "required"})
    return out


def _to_utc(dt: datetime) -> datetime:
    """Devuelve dt en UTC. Si es naive, asume UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _extract_start_end_from_create(data: Any) -> tuple[datetime, datetime]:
    """
    Extrae start/end de EventCreate soportando:
    - Esquema A: data.start y data.end (datetime)
    - Esquema B: data.date (YYYY-MM-DD), data.time (HH:MM) y data.duration (minutos)
    """
    # Esquema A
    if hasattr(data, "start") and hasattr(data, "end") and getattr(data, "start") and getattr(data, "end"):
        start_dt = _to_utc(getattr(data, "start"))
        end_dt = _to_utc(getattr(data, "end"))
        return start_dt, end_dt

    # Esquema B
    date_val = getattr(data, "date", None)
    time_val = getattr(data, "time", None)
    duration_val = getattr(data, "duration", None)
    if date_val and time_val and (duration_val is not None):
        start_iso = f"{date_val}T{time_val}:00"
        start_dt = _to_utc(datetime.fromisoformat(start_iso))
        end_dt = start_dt + timedelta(minutes=int(duration_val))
        return start_dt, end_dt

    raise ValueError("EventCreate debe incluir start/end o bien date/time/duration")


def _parse_graph_event(ev: dict) -> Event:
    """Convierte un evento de Graph API en un objeto Event (start/end y attendees normalizados)."""
    start_iso = (ev.get("start") or {}).get("dateTime")
    end_iso = (ev.get("end") or {}).get("dateTime")

    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None

    if start_iso:
        try:
            start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        except Exception:
            start_dt = datetime.fromisoformat(start_iso).replace(tzinfo=timezone.utc)
    if end_iso:
        try:
            end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        except Exception:
            end_dt = datetime.fromisoformat(end_iso).replace(tzinfo=timezone.utc)

    ev_type = _pick_event_type(ev.get("categories", []) or [])

    attendees = []
    for a in ev.get("attendees", []) or []:
        email_obj = a.get("emailAddress") or {}
        name = email_obj.get("name")
        email = email_obj.get("address")
        if email or name:
            attendees.append({"name": name or "", "email": email or ""})

    return Event(
        id=ev.get("id", str(uuid.uuid4())),
        outlook_id=ev.get("id"),
        title=ev.get("subject", "Sin título"),
        start=start_dt,
        end=end_dt,
        type=ev_type,
        notes=ev.get("bodyPreview", ""),
        attendees=attendees,
        teams_url=(ev.get("onlineMeeting") or {}).get("joinUrl"),
    )


def _date_range(period: str, reference: Optional[date] = None) -> tuple[datetime, datetime]:
    ref = reference or date.today()
    if period == "day":
        start = datetime(ref.year, ref.month, ref.day, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(ref.year, ref.month, ref.day, 23, 59, 59, tzinfo=timezone.utc)
    elif period == "week":
        monday = ref - timedelta(days=ref.weekday())
        start = datetime(monday.year, monday.month, monday.day, 0, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(days=7) - timedelta(seconds=1)
    elif period == "month":
        start = datetime(ref.year, ref.month, 1, 0, 0, 0, tzinfo=timezone.utc)
        if ref.month == 12:
            end = datetime(ref.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        else:
            end = datetime(ref.year, ref.month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    else:  # year
        start = datetime(ref.year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(ref.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


async def get_events(
    period: str = "day",
    date_ref: Optional[str] = None,
) -> List[Event]:
    """Obtiene eventos del calendario de Outlook; si no hay credenciales, devuelve mocks válidos."""
    # Fallback si faltan credenciales mínimas
    if not settings.ms_client_id or not settings.ms_tenant_id or not settings.ms_user_email:
        return _mock_events()

    import httpx

    try:
        headers = _graph_headers()
    except RuntimeError as exc:
        logger.warning("Outlook no disponible (credenciales inválidas): %s", exc)
        return _mock_events()

    ref = date.fromisoformat(date_ref) if date_ref else date.today()
    start, end = _date_range(period, ref)

    url = (
        f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}"
        f"/calendarView"
        f"?startDateTime={start.isoformat()}"
        f"&endDateTime={end.isoformat()}"
        f"&$orderby=start/dateTime"
        f"&$top=50"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return [_parse_graph_event(ev) for ev in data.get("value", [])]
    except Exception as exc:
        logger.warning("Error obteniendo eventos de Outlook, usando mock: %s", exc)
        return _mock_events()


async def create_event(data: EventCreate) -> Event:
    """
    Crea un evento en Outlook si hay credenciales; si no, devuelve uno simulado local.
    Acepta EventCreate con start/end o con date/time/duration.
    """
    start_dt, end_dt = _extract_start_end_from_create(data)

    # Sin Graph → Event local consistente
    if not settings.ms_client_id or not settings.ms_tenant_id or not settings.ms_user_email:
        attendees_norm = _normalize_attendees_for_model(getattr(data, "attendees", None))
        return Event(
            id=str(uuid.uuid4()),
            title=getattr(data, "title", "Sin título"),
            start=start_dt,
            end=end_dt,
            type=_pick_event_type(["meeting"]),
            notes=getattr(data, "notes", "") or "",
            attendees=attendees_norm,
        )

    import httpx

    body = {
        "subject": getattr(data, "title", "Sin título"),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        "body": {"contentType": "text", "content": getattr(data, "notes", "") or ""},
        "attendees": _normalize_attendees_for_graph(getattr(data, "attendees", None)),
    }

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=body, headers=_graph_headers())
        resp.raise_for_status()
        return _parse_graph_event(resp.json())


async def update_event(event_id: str, data: EventUpdate) -> Event:
    """
    Actualiza un evento en Outlook. Acepta start/end o date/time/duration.
    Si no hay Graph, lanza ValueError (puedes implementar update local si lo necesitas).
    """
    if not settings.ms_client_id or not settings.ms_tenant_id or not settings.ms_user_email:
        raise ValueError("Microsoft Graph no configurado correctamente")

    import httpx

    body: Dict[str, Any] = {}

    # Título y notas
    if getattr(data, "title", None) is not None:
        body["subject"] = data.title
    if getattr(data, "notes", None) is not None:
        body["body"] = {"contentType": "text", "content": data.notes}

    # Rango temporal: puede venir como start/end o como date/time/duration
    start_dt = None
    end_dt = None
    if getattr(data, "start", None) and getattr(data, "end", None):
        start_dt = _to_utc(data.start)
        end_dt = _to_utc(data.end)
    else:
        if getattr(data, "date", None) and getattr(data, "time", None) and getattr(data, "duration", None):
            base = datetime.fromisoformat(f"{data.date}T{data.time}:00")
            start_dt = _to_utc(base)
            end_dt = start_dt + timedelta(minutes=int(data.duration))

    if start_dt and end_dt:
        body["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "UTC"}
        body["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "UTC"}

    # Attendees opcional en update
    if getattr(data, "attendees", None):
        body["attendees"] = _normalize_attendees_for_graph(data.attendees)

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events/{event_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(url, json=body, headers=_graph_headers())
        resp.raise_for_status()
        return _parse_graph_event(resp.json())


async def delete_event(event_id: str) -> None:
    """Elimina un evento en Outlook; no hace nada si Graph no está configurado."""
    if not settings.ms_client_id or not settings.ms_tenant_id or not settings.ms_user_email:
        return

    import httpx

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events/{event_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(url, headers=_graph_headers())
        resp.raise_for_status()


def _mock_events() -> List[Event]:
    """
    Datos de ejemplo cuando Outlook no está configurado. Cumple el esquema: start/end y attendees normalizados.
    """
    def mk(start_time: str, minutes: int, title: str, people: List[str], etype_hint: str = "meeting") -> Event:
        today = date.today()
        hour, minute = map(int, start_time.split(":"))
        start_dt = datetime(today.year, today.month, today.day, hour, minute, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(minutes=minutes)
        attendees = [{"name": p, "email": f"{p.lower()}@example.com"} for p in people]
        ev_type = _pick_event_type([etype_hint])
        return Event(
            id=str(uuid.uuid4()),
            title=title,
            start=start_dt,
            end=end_dt,
            type=ev_type,
            notes="",
            attendees=attendees,
        )

    return [
        mk("09:00", 15, "Daily standup", ["Ana", "Paco", "Marta"], "meeting"),
        mk("11:00", 60, "Revisión sprint", ["Equipo"], "meeting"),
        mk("13:30", 30, "Cita médica", [], "personal"),
        mk("16:00", 30, "1:1 con producto", ["Laura"], "meeting"),
    ]
