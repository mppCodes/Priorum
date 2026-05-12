"""
Servicio de integración con Microsoft Graph API (Outlook / Teams).
Gestiona eventos del calendario del usuario.
"""
from typing import Optional
from datetime import date, datetime, timedelta
import uuid

from app.config import get_settings
from app.models.event import Event, EventCreate, EventUpdate, EventType

settings = get_settings()

# Cache simple del token de acceso
_token_cache: dict = {}


def _get_access_token() -> str:
    """Obtiene un token de acceso para Microsoft Graph usando MSAL."""
    import msal

    app = msal.ConfidentialClientApplication(
        client_id=settings.ms_client_id,
        client_credential=settings.ms_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.ms_tenant_id}",
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        raise RuntimeError(f"Error obteniendo token MS Graph: {result.get('error_description')}")
    return result["access_token"]


def _graph_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


def _parse_graph_event(ev: dict) -> Event:
    """Convierte un evento de Graph API en un objeto Event."""
    start_dt = ev.get("start", {}).get("dateTime", "")
    end_dt   = ev.get("end",   {}).get("dateTime", "")

    # Calcula duración en minutos
    duration = 30
    if start_dt and end_dt:
        try:
            s = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
            e = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
            duration = int((e - s).total_seconds() / 60)
        except Exception:
            pass

    # Determina tipo
    categories = [c.lower() for c in ev.get("categories", [])]
    if "personal" in categories:
        ev_type = EventType.personal
    elif "bloqueo" in categories or "block" in categories:
        ev_type = EventType.bloqueo
    else:
        ev_type = EventType.reunion

    attendees = [
        a.get("emailAddress", {}).get("name", "")
        for a in ev.get("attendees", [])
        if a.get("emailAddress", {}).get("name")
    ]

    time_str = ""
    date_str = ""
    if start_dt:
        try:
            dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M")
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    return Event(
        id=ev.get("id", str(uuid.uuid4())),
        outlook_id=ev.get("id"),
        title=ev.get("subject", "Sin título"),
        date=date_str,
        time=time_str,
        duration=duration,
        type=ev_type,
        notes=ev.get("bodyPreview", ""),
        attendees=attendees,
        teams_url=ev.get("onlineMeeting", {}).get("joinUrl"),
    )


def _date_range(period: str, reference: Optional[date] = None) -> tuple[datetime, datetime]:
    ref = reference or date.today()
    if period == "day":
        start = datetime(ref.year, ref.month, ref.day, 0, 0, 0)
        end   = datetime(ref.year, ref.month, ref.day, 23, 59, 59)
    elif period == "week":
        monday = ref - timedelta(days=ref.weekday())
        start  = datetime(monday.year, monday.month, monday.day, 0, 0, 0)
        end    = start + timedelta(days=7) - timedelta(seconds=1)
    elif period == "month":
        start = datetime(ref.year, ref.month, 1, 0, 0, 0)
        if ref.month == 12:
            end = datetime(ref.year, 12, 31, 23, 59, 59)
        else:
            end = datetime(ref.year, ref.month + 1, 1) - timedelta(seconds=1)
    else:  # year
        start = datetime(ref.year, 1, 1, 0, 0, 0)
        end   = datetime(ref.year, 12, 31, 23, 59, 59)
    return start, end


async def get_events(
    period: str = "day",
    date_ref: Optional[str] = None,
) -> list[Event]:
    """Obtiene eventos del calendario de Outlook."""
    if not settings.ms_client_id or not settings.ms_tenant_id:
        return _mock_events()

    import httpx

    ref = date.fromisoformat(date_ref) if date_ref else date.today()
    start, end = _date_range(period, ref)

    url = (
        f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}"
        f"/calendarView"
        f"?startDateTime={start.isoformat()}Z"
        f"&endDateTime={end.isoformat()}Z"
        f"&$orderby=start/dateTime"
        f"&$top=50"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_graph_headers())
        resp.raise_for_status()
        data = resp.json()

    return [_parse_graph_event(ev) for ev in data.get("value", [])]


async def create_event(data: EventCreate) -> Event:
    """Crea un evento en Outlook."""
    if not settings.ms_client_id:
        return Event(id=str(uuid.uuid4()), **data.model_dump())

    import httpx

    start_iso = f"{data.date}T{data.time}:00"
    end_dt    = datetime.fromisoformat(start_iso) + timedelta(minutes=data.duration)

    body = {
        "subject": data.title,
        "start":   {"dateTime": start_iso, "timeZone": "Europe/Madrid"},
        "end":     {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Madrid"},
        "body":    {"contentType": "text", "content": data.notes},
        "attendees": [
            {"emailAddress": {"address": a}, "type": "required"}
            for a in data.attendees
        ],
    }

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=body, headers=_graph_headers())
        resp.raise_for_status()
        return _parse_graph_event(resp.json())


async def update_event(event_id: str, data: EventUpdate) -> Event:
    """Actualiza un evento en Outlook."""
    if not settings.ms_client_id:
        raise ValueError("Microsoft Graph no configurado")

    import httpx

    body: dict = {}
    if data.title    is not None: body["subject"] = data.title
    if data.notes    is not None: body["body"] = {"contentType": "text", "content": data.notes}
    if data.date and data.time:
        body["start"] = {"dateTime": f"{data.date}T{data.time}:00", "timeZone": "Europe/Madrid"}

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events/{event_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.patch(url, json=body, headers=_graph_headers())
        resp.raise_for_status()
        return _parse_graph_event(resp.json())


async def delete_event(event_id: str) -> None:
    """Elimina un evento de Outlook."""
    if not settings.ms_client_id:
        return

    import httpx

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events/{event_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.delete(url, headers=_graph_headers())
        resp.raise_for_status()


def _mock_events() -> list[Event]:
    """Datos de ejemplo cuando Outlook no está configurado."""
    today = date.today().isoformat()
    return [
        Event(id="e1", title="Daily standup",    date=today, time="09:00", duration=15,
              type="reunion",  attendees=["Ana", "Paco", "Marta"]),
        Event(id="e2", title="Revisión sprint",  date=today, time="11:00", duration=60,
              type="reunion",  attendees=["Todo el equipo"]),
        Event(id="e3", title="Cita médica",      date=today, time="13:30", duration=30,
              type="personal", attendees=[]),
        Event(id="e4", title="1:1 con producto", date=today, time="16:00", duration=30,
              type="reunion",  attendees=["Laura"]),
    ]