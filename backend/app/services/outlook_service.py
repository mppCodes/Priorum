"""
Servicio de integración con Microsoft Graph API (Outlook / Teams).
Gestiona eventos del calendario del usuario.

Estrategia de autenticación (por orden de prioridad):
  1. Token OAuth del usuario (flujo Authorization Code) — oauth_service
  2. Fallback: Client Credentials app-only (ms_client_id + ms_client_secret)
"""
from typing import Optional
from datetime import date, datetime, timedelta
import uuid

from app.config import get_settings
from app.models.event import Event, EventCreate, EventUpdate, EventType

settings = get_settings()


def _looks_like_uuid(value: str) -> bool:
    """Detecta si un valor parece un UUID (Secret ID en lugar de Secret Value)."""
    import re
    return bool(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value, re.I))


def _get_access_token() -> str:
    """
    Obtiene un token de acceso para Microsoft Graph.
    Prioridad:
      1. Token OAuth del usuario (oauth_service) si está disponible.
      2. Client Credentials (app-only) como fallback.
    """
    import re

    # 1. Intentar token OAuth del usuario
    try:
        from app.services import oauth_service
        oauth_token = oauth_service.get_valid_token()
        if oauth_token:
            return oauth_token
    except Exception:
        pass  # Si oauth_service falla, continuar con client credentials

    # 2. Fallback: Client Credentials
    import msal

    if not settings.ms_client_id or not settings.ms_tenant_id:
        raise RuntimeError("No hay token OAuth activo ni credenciales de aplicación configuradas.")

    # Validación preventiva: el Secret Value nunca es un UUID puro
    if settings.ms_client_secret and bool(re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        settings.ms_client_secret, re.I
    )):
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
        if "AADSTS7000215" in error_desc:
            raise RuntimeError(
                "AADSTS7000215 – MS_CLIENT_SECRET contiene el Secret ID, no el Secret Value. "
                "Ve a Azure Portal → App Registrations → tu app → Certificates & Secrets "
                "y copia el campo 'Value' (la cadena larga, no el UUID)."
            )
        raise RuntimeError(f"Error obteniendo token MS Graph: {error_desc}")
    return result["access_token"]


def _get_user_email() -> str:
    """
    Devuelve el email del usuario para las llamadas a Graph API.
    Si hay token OAuth activo, usa el email del token; si no, usa ms_user_email del .env.
    """
    try:
        from app.services import oauth_service
        status = oauth_service.get_connection_status()
        if status.get("connected") and status.get("user_email"):
            return status["user_email"]
    except Exception:
        pass
    return settings.ms_user_email


def _graph_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


def _parse_graph_event(ev: dict) -> Event:
    """Convierte un evento de Graph API en un objeto Event."""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("Parseando evento Graph: id=%s subject=%s", ev.get("id"), ev.get("subject"))

    # Usar "or {}" para manejar campos presentes pero con valor null
    start_dt = (ev.get("start") or {}).get("dateTime", "")
    end_dt   = (ev.get("end")   or {}).get("dateTime", "")

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
        teams_url=(ev.get("onlineMeeting") or {}).get("joinUrl"),
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
    """Obtiene eventos del calendario de Outlook.

    Si las credenciales no están configuradas o son inválidas, devuelve datos de ejemplo.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Permitir acceso si hay token OAuth activo, aunque ms_client_id no esté en .env
    from app.services import oauth_service as _oauth
    has_oauth = bool(_oauth.get_valid_token())
    if not has_oauth and (not settings.ms_client_id or not settings.ms_tenant_id):
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

    user_email = _get_user_email()
    if not user_email:
        logger.warning("No hay email de usuario configurado para Graph API.")
        return _mock_events()

    url = (
        f"https://graph.microsoft.com/v1.0/users/{user_email}"
        f"/calendarView"
        f"?startDateTime={start.isoformat()}Z"
        f"&endDateTime={end.isoformat()}Z"
        f"&$orderby=start/dateTime"
        f"&$top=50"
        f"&$select=id,subject,start,end,categories,attendees,bodyPreview,onlineMeeting,showAs"
    )

    try:
        async with httpx.AsyncClient() as client:
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

    # Si no hay credenciales completas ni token OAuth, devolver evento local
    from app.services import oauth_service as _oauth
    has_oauth = bool(_oauth.get_valid_token())
    user_email = _get_user_email()
    if not has_oauth and (not settings.ms_client_id or not settings.ms_tenant_id or not user_email):
        logger.warning(
            "create_event: credenciales incompletas y sin token OAuth. El evento se crea solo en local."
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
        data.title, start_iso, user_email,
    )

    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/events"
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
    """Actualiza un evento en Outlook."""
    if not settings.ms_client_id:
        raise ValueError("Microsoft Graph no configurado")

    import httpx

    body: dict = {}
    if data.title    is not None: body["subject"] = data.title
    if data.notes    is not None: body["body"] = {"contentType": "text", "content": data.notes}
    if data.date and data.time:
        body["start"] = {"dateTime": f"{data.date}T{data.time}:00", "timeZone": "Europe/Madrid"}

    url = f"https://graph.microsoft.com/v1.0/users/{_get_user_email()}/events/{event_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.patch(url, json=body, headers=_graph_headers())
        resp.raise_for_status()
        return _parse_graph_event(resp.json())


async def delete_event(event_id: str) -> None:
    """Elimina un evento de Outlook."""
    if not settings.ms_client_id:
        return

    import httpx

    url = f"https://graph.microsoft.com/v1.0/users/{_get_user_email()}/events/{event_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.delete(url, headers=_graph_headers())
        resp.raise_for_status()


def _mock_events() -> list[Event]:
    """Datos de ejemplo cuando Outlook no está configurado."""
    today = date.today().isoformat()
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
