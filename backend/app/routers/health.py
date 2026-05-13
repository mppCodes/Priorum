from fastapi import APIRouter, Query
from typing import Any, Dict, List, Optional
from app.config import get_settings
from app.services.mongo import get_db

router = APIRouter(prefix="/health", tags=["health"])

def _format_index(idx: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "name": idx.get("name"),
        "keys": idx.get("key"),
    }
    # TTL si existe
    if "expireAfterSeconds" in idx:
        out["expireAfterSeconds"] = idx["expireAfterSeconds"]
    return out

@router.get("")
async def health(deep: bool = Query(default=False)):
    """
    - deep=false: ping a Mongo y lista de colecciones/índices principales
    - deep=true: además intenta comprobar Qdrant (si qdrant_url está configurado)
    """
    settings = get_settings()
    db = await get_db()

    # Ping a Mongo
    mongo_ok: bool = False
    mongo_error: Optional[str] = None
    try:
        res = await db.command("ping")
        mongo_ok = bool(res.get("ok") == 1.0)
    except Exception as e:
        mongo_error = str(e)

    # Colecciones esperadas
    colls = {
        "tasks": settings.mongo_tasks_collection,
        "events": settings.mongo_events_collection,
        "tasks_cache": settings.mongo_tasks_cache_collection,
        "events_cache": settings.mongo_events_cache_collection,
        "agent_logs": settings.mongo_agent_logs_collection,
        "agent_msgs": settings.mongo_agent_msgs_collection,
    }
    collections_info: Dict[str, Any] = {}

    try:
        for label, col_name in colls.items():
            # list_indexes puede fallar si la colección no existe aún; lo capturamos
            try:
                indexes = []
                async for idx in db[col_name].list_indexes():
                    indexes.append(_format_index(idx.document))
                collections_info[label] = {
                    "collection": col_name,
                    "indexes": indexes,
                }
            except Exception:
                collections_info[label] = {
                    "collection": col_name,
                    "indexes": [],
                    "note": "sin índices o colección aún no creada",
                }
    except Exception as e:
        # Si hay un fallo general, lo anotamos
        collections_info["error"] = str(e)

    qdrant_status: Dict[str, Any] = {
        "enabled": False,
        "ok": None,
        "collections": None,
        "error": None,
    }

    if deep:
        # Qdrant (opcional)
        from app.config import get_settings
        s = get_settings()
        if s.qdrant_url:
            qdrant_status["enabled"] = True
            try:
                from qdrant_client import QdrantClient
                client = QdrantClient(url=s.qdrant_url)
                colls = client.get_collections().collections
                qdrant_status["ok"] = True
                qdrant_status["collections"] = [c.name for c in colls]
            except Exception as e:
                qdrant_status["ok"] = False
                qdrant_status["error"] = str(e)

    return {
        "app": {
            "name": settings.app_name,
            "debug": settings.debug,
            "api_prefix": settings.api_prefix,
        },
        "mongo": {
            "uri": settings.mongo_uri,  # no contiene credenciales en tu caso
            "db": settings.mongo_db_name,
            "ok": mongo_ok,
            "error": mongo_error,
            "collections": collections_info,
        },
        "qdrant": qdrant_status,
    }
