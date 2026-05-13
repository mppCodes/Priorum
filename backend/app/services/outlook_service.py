"""
Servicio de integración con Microsoft Graph API (Outlook / Teams).
Gestiona eventos del calendario del usuario.

Adaptado al modelo Event con:
- start/end: datetime
- attendees: List[Attendee {email, name}]
- type: EventType (opcional)
- title, description, location, source, created_at, updated_at
"""
from __future__ import annotations

from datetime import datetime, date, time as dtime, timedelta
from typing import List, Optional, Tuple

from app.config import get_settings
from app.models.event import Event, EventCreate, EventUpdate, Attendee, EventType

settings = get_settings()

# ---------------------------
# Credenciales y headers
# ---------------------------

def _has_ms_credentials() -> bool:
    return all(
        [
            bool(getattr(settings, "ms_tenant_id", "")),
            bool(getattr(settings, "ms_client_id", "")),
            bool(getattr(settings, "ms_client_secret", "")),
            bool(getattr(settings, "ms_user_email", "")),
        ]
    )


def _get_access_token() -> str:
    """
    Obtiene un token de acceso para Microsoft Graph usando MSAL (client credentials).
    Si no está MSAL instalado o hay error, lanza excepción.
    """
    try:
        import msal
    except ImportError as e:
        raise RuntimeError("msal no está instalado, instala 'msal' o usa modo mock") from e

    app = msal.ConfidentialClientApplication(
        client_id=settings.ms_client_id,
        client_credential=settings.ms_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.ms_tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(f"Error obteniendo token MS Graph: {result.get('error_description')}")
    return result["access_token"]


def _graph_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


# ---------------------------
# Utilidades de parseo
# ---------------------------

def _parse_iso(dt: str) -> datetime:
    """
    Convierte string ISO (posiblemente con 'Z') a datetime con tzinfo.
    """
    return datetime.fromisoformat(dt.replace("Z", "+00:00"))


def _event_type_from_categories(categories: List[str]) -> Optional[EventType]:
    cats = [c.lower() for c in categories or []]
    if "focus" in cats or "bloqueo" in cats or "block" in cats:
        return EventType.focus
    if "out_of_office" in cats or "ooo" in cats or "vacation" in cats:
        return EventType.out_of_office
    if "reminder" in cats:
        return EventType.reminder
    # Por defecto, asumimos reunión si hay asistentes
    return None


def _attendees_from_graph(attendees: List[dict]) -> List[Attendee]:
    out: List[Attendee] = []
    for a in attendees or []:
        email_obj = a.get("emailAddress", {})
        addr = email_obj.get("address")
        name = email_obj.get("name")
        if addr or name:
            out.append(Attendee(email=addr or f"{(name or '').lower().replace(' ','.')}@example.com", name=name))
    return out


def _parse_graph_event(ev: dict) -> Event:
    """
    Convierte un evento de Graph API a Event (modelo local).
    """
    start_iso = ev.get("start", {}).get("dateTime")
    end_iso = ev.get("end", {}).get("dateTime")
    start_dt = _parse_iso(start_iso) if start_iso else datetime.utcnow()
    end_dt = _parse_iso(end_iso) if end_iso else (start_dt + timedelta(minutes=30))

    title = ev.get("subject", "Sin título")
    description = ev.get("bodyPreview") or None
    location = (ev.get("location") or {}).get("displayName") or None
    attendees = _attendees_from_graph(ev.get("attendees", []))
    ev_type = _event_type_from_categories(ev.get("categories", []))

    now = datetime.utcnow()
    return Event(
        id=ev.get("id"),                 # id de Graph si existe
        external_id=ev.get("id"),
        title=title,
        description=description,
        start=start_dt,
        end=end_dt,
        location=location,
        attendees=attendees,
        source="outlook",
        created_at=now,
        updated_at=now,
        # type es opcional en el modelo; si lo quieres persistir, añade el campo en Event y descomenta:
        # type=ev_type,
    )


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
    else:  # year
        start = datetime(ref.year, 1, 1, 0, 0, 0)
        end = datetime(ref.year, 12, 31, 23, 59, 59)
    return start, end


# ---------------------------
# API pública (usada por router calendar)
# ---------------------------

async def get_events(period: str = "day", date_ref: Optional[str] = None) -> List[Event]:
    """
    Obtiene eventos del calendario de Outlook. Sin credenciales → mock.
    """
    if not _has_ms_credentials():
        return _mock_events(date_ref=date_ref)

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
    """
    Crea un evento en Outlook. Sin credenciales → devuelve mock del payload.
    EventCreate contiene start/end y attendees estructurados.
    """
    if not _has_ms_credentials():
        now = datetime.utcnow()
        return Event(
            id="mock-" + now.strftime("%Y%m%d%H%M%S"),
            external_id=None,
            title=data.title,
            description=data.description,
            start=data.start,
            end=data.end,
            location=data.location,
            attendees=data.attendees or [],
            source="outlook",
            created_at=now,
            updated_at=now,
        )

    import httpx

    # Construcción del cuerpo según Graph
    body = {
        "subject": data.title,
        "start": {"dateTime": data.start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": data.end.isoformat(), "timeZone": "UTC"},
        "body": {"contentType": "text", "content": data.description or ""},
        "location": {"displayName": data.location} if data.location else None,
        "attendees": [
            {
                "emailAddress": {"address": a.email, "name": a.name or a.email},
                "type": "required",
            }
            for a in (data.attendees or [])
        ],
    }
    # Limpia claves None
    body = {k: v for k, v in body.items() if v is not None}

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=body, headers=_graph_headers())
        resp.raise_for_status()
        return _parse_graph_event(resp.json())


async def update_event(event_id: str, data: EventUpdate) -> Event:
    """
    Actualiza un evento en Outlook. Sin credenciales → devuelve un mock.
    """
    if not _has_ms_credentials():
        now = datetime.utcnow()
        base_start = data.start or now
        base_end = data.end or (base_start + timedelta(minutes=30))
        return Event(
            id=event_id,
            external_id=None,
            title=data.title or "Evento (mock) actualizado",
            description=data.description,
            start=base_start,
            end=base_end,
            location=data.location,
            attendees=data.attendees or [],
            source="outlook",
            created_at=now,
            updated_at=now,
        )

    import httpx

    body: dict = {}
    if data.title is not None:
        body["subject"] = data.title
    if data.description is not None:
        body["body"] = {"contentType": "text", "content": data.description}
    if data.start is not None:
        body.setdefault("start", {})["dateTime"] = data.start.isoformat()
        body.setdefault("start", {})["timeZone"] = "UTC"
    if data.end is not None:
        body.setdefault("end", {})["dateTime"] = data.end.isoformat()
        body.setdefault("end", {})["timeZone"] = "UTC"
    if data.location is not None:
        body["location"] = {"displayName": data.location or ""}
    if data.attendees is not None:
        body["attendees"] = [
            {
                "emailAddress": {"address": a.email, "name": a.name or a.email},
                "type": "required",
            }
            for a in data.attendees
        ]

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events/{event_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.patch(url, json=body, headers=_graph_headers())
        resp.raise_for_status()
        # Algunas operaciones PATCH devuelven 204; si no hay cuerpo, hay que GET:
        if resp.status_code == 204 or not resp.content:
            ev_resp = await client.get(url, headers=_graph_headers())
            ev_resp.raise_for_status()
            return _parse_graph_event(ev_resp.json())
        return _parse_graph_event(resp.json())


async def delete_event(event_id: str) -> None:
    """
    Elimina un evento en Outlook. Sin credenciales → no hace nada.
    """
    if not _has_ms_credentials():
        return None

    import httpx

    url = f"https://graph.microsoft.com/v1.0/users/{settings.ms_user_email}/events/{event_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.delete(url, headers=_graph_headers())
        resp.raise_for_status()
        return None


# ---------------------------
# MOCK para desarrollo (sin credenciales)
# ---------------------------

def _mock_events(date_ref: Optional[str] = None) -> List[Event]:
    """
    Genera eventos de ejemplo en la fecha indicada (YYYY-MM-DD) o hoy.
    Cumple el esquema de Event (start/end y Attendee estructurado).
    """
    base_date = _parse_date(date_ref) if date_ref else date.today()

    def make_event(
        eid: str,
        title: str,
        start_hhmm: str,
        duration_min: int,
        attendees_names: Optional[List[str]] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        etype: Optional[EventType] = None,
    ) -> Event:
        start_dt = _combine_datetime(base_date, start_hhmm)
        end_dt = start_dt + timedelta(minutes=duration_min)
        attendees_objs = _attendees_from_names(attendees_names or [])
        now = datetime.utcnow()
        return Event(
            id=eid,
            external_id=None,
            title=title,
            description=description,
            start=start_dt,
            end=end_dt,
            location=location,
            attendees=attendees_objs,
            source="outlook",
            created_at=now,
            updated_at=now,
            # type es opcional; si quieres persistirlo añade el campo en Event y descomenta:
            # type=etype,
        )

    return [
        make_event(
            eid="e1",
            title="Daily standup",
            start_hhmm="09:00",
            duration_min=15,
            attendees_names=["Ana", "Paco", "Marta"],
            description="Daily del equipo",
            location="Teams",
            etype=EventType.meeting,
        ),
        make_event(
            eid="e2",
            title="Bloque de foco",
            start_hhmm="10:00",
            duration_min=60,
            attendees_names=[],
            description="Trabajo profundo",
            location="Oficina",
            etype=EventType.focus,
        ),
        make_event(
            eid="e3",
            title="Revisión sprint",
            start_hhmm="16:30",
            duration_min=45,
            attendees_names=["Ana", "Marta"],
            description="Revisión con stakeholders",
            location="Sala 2",
            etype=EventType.meeting,
        ),
    ]


def _attendees_from_names(names: List[str]) -> List[Attendee]:
    out: List[Attendee] = []
    for n in names:
        slug = (
            n.lower()
            .replace(" ", ".")
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ñ", "n")
        )
        out.append(Attendee(email=f"{slug}@example.com", name=n))
    return out


def _parse_date(s: str) -> date:
    # Espera YYYY-MM-DD
    return datetime.strptime(s, "%Y-%m-%d").date()


def _combine_datetime(d: date, hhmm: str) -> datetime:
    hh, mm = hhmm.split(":")
    t = dtime(hour=int(hh), minute=int(mm))
    return datetime.combine(d, t)
