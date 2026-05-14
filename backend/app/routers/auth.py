"""
Router OAuth 2.0 para autenticación con Microsoft (Outlook).
Endpoints:
  GET  /api/auth/outlook/login      → devuelve la URL de autorización
  GET  /api/auth/outlook/callback   → recibe el código de Microsoft y obtiene el token
  GET  /api/auth/outlook/status     → estado de la conexión
  DELETE /api/auth/outlook/logout   → elimina el token en memoria
"""
import logging
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse

from app.services import oauth_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/outlook/login")
async def outlook_login():
    """
    Devuelve la URL de autorización de Microsoft.
    El frontend debe redirigir al usuario a esta URL.
    """
    try:
        auth_url = oauth_service.get_auth_url()
        # Incluir redirect_uri para facilitar diagnóstico de configuración en Azure
        return {
            "auth_url": auth_url,
            "redirect_uri": settings.ms_redirect_uri,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/outlook/debug")
async def outlook_debug():
    """
    Diagnóstico: muestra la configuración OAuth activa (sin secretos).
    Útil para verificar que el redirect_uri coincide con el registrado en Azure Portal.
    """
    return {
        "ms_client_id": settings.ms_client_id[:8] + "..." if settings.ms_client_id else "(vacío)",
        "ms_tenant_id": settings.ms_tenant_id[:8] + "..." if settings.ms_tenant_id else "(vacío)",
        "ms_redirect_uri": settings.ms_redirect_uri,
        "ms_scopes": settings.ms_scopes,
        "frontend_url": settings.frontend_url,
    }


@router.get("/outlook/callback")
async def outlook_callback(
    code: str = Query(None, description="Código de autorización devuelto por Microsoft"),
    error: str = Query(None, description="Error devuelto por Microsoft"),
    error_description: str = Query(None, description="Descripción del error"),
):
    """
    Callback OAuth. Microsoft redirige aquí tras la autenticación del usuario.
    Intercambia el código por tokens y redirige al frontend.
    """
    # Si Microsoft devolvió un error
    if error:
        logger.error("Error en callback OAuth: %s – %s", error, error_description)
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?outlook=error&reason={error}"
        )

    if not code:
        logger.error("Callback OAuth sin código ni error.")
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?outlook=error&reason=missing_code"
        )

    try:
        user_info = oauth_service.exchange_code_for_token(code)
        logger.info(
            "Autenticación OAuth completada para: %s", user_info.get("user_email")
        )
    except RuntimeError as e:
        logger.error("Error intercambiando código: %s", e)
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?outlook=error&reason=token_exchange_failed"
        )

    # Redirigir al frontend con éxito
    return RedirectResponse(
        url=f"{settings.frontend_url}/settings?outlook=connected"
    )


@router.get("/outlook/status")
async def outlook_status():
    """
    Devuelve el estado actual de la conexión OAuth con Outlook.
    """
    return oauth_service.get_connection_status()


@router.delete("/outlook/logout", status_code=204)
async def outlook_logout():
    """
    Elimina el token OAuth de la memoria. El usuario deberá volver a autenticarse.
    """
    oauth_service.revoke_token()