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
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if result is None:
        raise RuntimeError(
            "MSAL devolvió None al solicitar el token. "
            "Verifica que MS_CLIENT_ID, MS_TENANT_ID y MS_CLIENT_SECRET sean correctos."
        )
    if "access_token" not in result:
        error_desc = result.get("error_description", "Sin descripción de error")
        # Error específico: Secret ID en lugar de Secret Value
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
    """Convierte un evento de Graph API en un objeto Event."""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("Parseando evento Graph: id=%s subject=%s", ev.get("id"), ev.get("subject"))

    # Usar "or {}" para manejar campos presentes pero con valor null
    start_dt = (ev.get("start") or {}).get("dateTime", "")
    end_dt   = (ev.get("end")   or {}).get("dateTime", "")

    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None

    if start_iso:
        try:
            start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        except Exception:
            pass

    # Determina tipo
    categories = [c.lower() for c in (ev.get("categories") or [])]
    if "personal" in categories:
        ev_type = EventType.personal
    elif "bloqueo" in categories or "block" in categories:
        ev_type = EventType.bloqueo
    else:
        ev_type = EventType.reunion

    attendees = [
        (a.get("emailAddress") or {}).get("name", "")
        for a in (ev.get("attendees") or [])
        if (a.get("emailAddress") or {}).get("name")
    ]

    time_str = ""
    date_str = ""
    if start_dt:
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
        # Solicitar tiempos en zona horaria de Madrid para evitar conversiones manuales
        headers["Prefer"] = 'outlook.timezone="Europe/Madrid"'
    except Exception as exc:
        import traceback
        logger.warning(
            "Outlook no disponible (error obteniendo token): %s\n%s",
            exc,
            traceback.format_exc(),
        )
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
        f"&$select=id,subject,start,end,categories,attendees,bodyPreview,onlineMeeting,showAs"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            logger.info("Graph API status: %s", resp.status_code)
            resp.raise_for_status()
            data = resp.json()
            logger.info("Graph API response keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))
            events_raw = data.get("value", []) if isinstance(data, dict) else []
            logger.info("Número de eventos recibidos: %d", len(events_raw))
            parsed = []
            for i, ev in enumerate(events_raw):
                try:
                    parsed.append(_parse_graph_event(ev))
                except Exception as parse_exc:
                    import traceback
                    logger.error(
                        "Error parseando evento[%d] id=%s subject=%s: %s\n%s",
                        i,
                        ev.get("id", "?") if isinstance(ev, dict) else "?",
                        ev.get("subject", "?") if isinstance(ev, dict) else "?",
                        parse_exc,
                        traceback.format_exc(),
                    )
            return parsed
    except Exception as exc:
        import traceback
        logger.warning(
            "Error obteniendo eventos de Outlook, usando mock: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return _mock_events()


async def create_event(data: EventCreate) -> Event:
    """Crea un evento en Outlook."""
    import logging
    import traceback
    logger = logging.getLogger(__name__)

    # Si no hay credenciales completas, devolver evento local (sin Outlook)
    if not settings.ms_client_id or not settings.ms_tenant_id or not settings.ms_user_email:
        logger.warning(
            "create_event: credenciales incompletas → ms_client_id=%s, ms_tenant_id=%s, ms_user_email=%s. "
            "El evento se crea solo en local.",
            "OK" if settings.ms_client_id else "VACÍO",
            "OK" if settings.ms_tenant_id else "VACÍO",
            "OK" if settings.ms_user_email else "VACÍO",
        )
        return Event(id=str(uuid.uuid4()), **data.model_dump())

    import httpx

    # Obtener token
    try:
        headers = _graph_headers()
        logger.info("create_event: token de Outlook obtenido correctamente")
    except Exception as exc:
        logger.error(
            "create_event: error obteniendo token: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        raise RuntimeError(f"No se pudo autenticar con Outlook: {exc}") from exc

    start_iso = f"{data.date}T{data.time}:00"
    end_dt    = datetime.fromisoformat(start_iso) + timedelta(minutes=data.duration)

    # Mapear el tipo de evento a categorías de Outlook
    # _parse_graph_event usa estas categorías para determinar el tipo al leer
    _type_to_category: dict[str, list[str]] = {
        "personal": ["Personal"],
        "bloqueo":  ["Bloqueo"],
        "reunion":  [],
    }
    categories = _type_to_category.get(str(data.type.value if hasattr(data.type, "value") else data.type), [])

    body: dict = {
        "subject": data.title,
        "start":   {"dateTime": start_iso, "timeZone": "Europe/Madrid"},
        "end":     {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Madrid"},
        "body":    {"contentType": "text", "content": data.notes or ""},
        "attendees": [
            {"emailAddress": {"address": a}, "type": "required"}
            for a in (data.attendees or [])
        ],
    }
    if categories:
        body["categories"] = categories

    logger.info(
        "create_event: POST Graph API → subject=%r start=%s user=%s",
        data.title, start_iso, settings.ms_user_email,
    )

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, headers=headers)
            logger.info("create_event: Graph API status=%s", resp.status_code)
            if not resp.is_success:
                logger.error(
                    "create_event: error de Graph API status=%s body=%s",
                    resp.status_code,
                    resp.text,
                )
            resp.raise_for_status()
            created = resp.json()
            logger.info("create_event: evento creado en Outlook id=%s", created.get("id"))
            return _parse_graph_event(created)
    except Exception as exc:
        logger.error(
            "create_event: excepción llamando a Graph API: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        raise


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
        Event(id="e1", title="Daily standup",    date=today, time="09:00", duration=15,
              type=EventType.reunion,  attendees=["Ana", "Paco", "Marta"]),
        Event(id="e2", title="Revisión sprint",  date=today, time="11:00", duration=60,
              type=EventType.reunion,  attendees=["Todo el equipo"]),
        Event(id="e3", title="Cita médica",      date=today, time="13:30", duration=30,
              type=EventType.personal, attendees=[]),
        Event(id="e4", title="1:1 con producto", date=today, time="16:00", duration=30,
              type=EventType.reunion,  attendees=["Laura"]),
    ]
