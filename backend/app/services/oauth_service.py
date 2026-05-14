"""
Servicio OAuth 2.0 Authorization Code Flow para Microsoft Graph (Outlook).
El token se almacena en memoria (se pierde al reiniciar el servidor).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Almacén en memoria ────────────────────────────────────────────────────────
# Estructura: {
#   "access_token": str,
#   "refresh_token": str | None,
#   "expires_at": datetime,
#   "user_email": str,
#   "user_name": str,
# }
_token_store: dict = {}


# ── Helpers MSAL ─────────────────────────────────────────────────────────────

def _build_msal_app():
    """Construye una instancia de ConfidentialClientApplication."""
    import msal
    return msal.ConfidentialClientApplication(
        client_id=settings.ms_client_id,
        client_credential=settings.ms_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.ms_tenant_id}",
    )


# ── API pública ───────────────────────────────────────────────────────────────

def get_auth_url() -> str:
    """
    Genera la URL de autorización de Microsoft para iniciar el flujo OAuth.
    El usuario debe ser redirigido a esta URL.
    """
    if not settings.ms_client_id or not settings.ms_tenant_id:
        raise RuntimeError(
            "MS_CLIENT_ID y MS_TENANT_ID deben estar configurados en .env "
            "para usar el flujo OAuth."
        )

    msal_app = _build_msal_app()
    auth_url = msal_app.get_authorization_request_url(
        scopes=settings.ms_scopes,
        redirect_uri=settings.ms_redirect_uri,
    )
    logger.info("URL de autorización generada: %s", auth_url[:80] + "...")
    return auth_url


def exchange_code_for_token(code: str) -> dict:
    """
    Intercambia el código de autorización por tokens de acceso y refresco.
    Guarda el resultado en el almacén en memoria.
    Devuelve un dict con { user_email, user_name }.
    """
    msal_app = _build_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code=code,
        scopes=settings.ms_scopes,
        redirect_uri=settings.ms_redirect_uri,
    )

    if "access_token" not in result:
        error_desc = result.get("error_description", result.get("error", "Error desconocido"))
        logger.error("Error intercambiando código por token: %s", error_desc)
        raise RuntimeError(f"Error obteniendo token de Outlook: {error_desc}")

    # Extraer info del usuario desde los claims del id_token
    id_token_claims = result.get("id_token_claims", {})
    user_email = (
        id_token_claims.get("preferred_username")
        or id_token_claims.get("upn")
        or id_token_claims.get("email")
        or ""
    )
    user_name = (
        id_token_claims.get("name")
        or id_token_claims.get("given_name")
        or user_email
    )

    # Calcular expiración
    expires_in = result.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc).timestamp() + expires_in

    _token_store.clear()
    _token_store.update({
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token"),
        "expires_at": expires_at,
        "user_email": user_email,
        "user_name": user_name,
    })

    logger.info("Token OAuth almacenado para usuario: %s", user_email)
    return {"user_email": user_email, "user_name": user_name}


def get_valid_token() -> Optional[str]:
    """
    Devuelve un access_token válido.
    Si ha expirado, intenta refrescarlo con el refresh_token.
    Devuelve None si no hay token almacenado.
    """
    if not _token_store:
        return None

    now = datetime.now(timezone.utc).timestamp()
    # Refrescar si expira en menos de 60 segundos
    if _token_store.get("expires_at", 0) - now < 60:
        refresh_token = _token_store.get("refresh_token")
        if not refresh_token:
            logger.warning("Token expirado y sin refresh_token disponible.")
            _token_store.clear()
            return None

        logger.info("Refrescando token de Outlook...")
        msal_app = _build_msal_app()
        # Filtrar scopes reservados que MSAL gestiona internamente
        _reserved = {"offline_access", "openid", "profile"}
        scopes = [s for s in settings.ms_scopes if s not in _reserved]
        result = msal_app.acquire_token_by_refresh_token(
            refresh_token=refresh_token,
            scopes=scopes,
        )
        if "access_token" not in result:
            error_desc = result.get("error_description", "Error desconocido")
            logger.error("Error refrescando token: %s", error_desc)
            _token_store.clear()
            return None

        expires_in = result.get("expires_in", 3600)
        _token_store["access_token"] = result["access_token"]
        _token_store["expires_at"] = now + expires_in
        if result.get("refresh_token"):
            _token_store["refresh_token"] = result["refresh_token"]
        logger.info("Token refrescado correctamente.")

    return _token_store.get("access_token")


def get_connection_status() -> dict:
    """
    Devuelve el estado de la conexión OAuth.
    """
    if not _token_store:
        return {"connected": False, "user_email": None, "user_name": None}

    now = datetime.now(timezone.utc).timestamp()
    expires_at = _token_store.get("expires_at", 0)
    is_expired = expires_at - now < 60 and not _token_store.get("refresh_token")

    return {
        "connected": not is_expired,
        "user_email": _token_store.get("user_email"),
        "user_name": _token_store.get("user_name"),
        "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat() if expires_at else None,
    }


def revoke_token() -> None:
    """Elimina el token del almacén en memoria."""
    _token_store.clear()
    logger.info("Token OAuth eliminado.")