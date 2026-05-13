from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, Optional, List
from datetime import datetime

from app.config import get_settings
from app.services.mongo import get_db

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

def _format_index(idx: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "name": idx.get("name"),
        "keys": idx.get("key"),
    }
    if "expireAfterSeconds" in idx:
        out["expireAfterSeconds"] = idx["expireAfterSeconds"]
    return out

@router.get("/healthz")
async def healthz(deep: bool = Query(default=False)):
    settings = get_settings()
    db = await get_db()

    mongo_ok: bool = False
    mongo_error: Optional[str] = None
    try:
        res = await db.command("ping")
        mongo_ok = bool(res.get("ok") == 1.0)
    except Exception as e:
        mongo_error = str(e)

    colls = {
        "tasks": settings.mongo_tasks_collection,
        "events": settings.mongo_events_collection,
        "tasks_cache": settings.mongo_tasks_cache_collection,
        "events_cache": settings.mongo_events_cache_collection,
        "agent_logs": settings.mongo_agent_logs_collection,
        "agent_msgs": settings.mongo_agent_msgs_collection,
    }
    collections_info: Dict[str, Any] = {}
    for label, col_name in colls.items():
        try:
            indexes: List[Dict[str, Any]] = []
            async for idx in db[col_name].list_indexes():
                doc = getattr(idx, "document", idx)
                indexes.append(_format_index(doc))
            collections_info[label] = {"collection": col_name, "indexes": indexes}
        except Exception:
            collections_info[label] = {
                "collection": col_name,
                "indexes": [],
                "note": "colección sin índices o aún no creada",
            }

    qdrant_status: Dict[str, Any] = {
        "enabled": False,
        "ok": None,
        "collections": None,
        "error": None,
    }

    if deep and getattr(settings, "qdrant_url", None):
        qdrant_status["enabled"] = True
        try:
            try:
                from qdrant_client import QdrantClient  # type: ignore
            except ImportError as ie:
                qdrant_status["ok"] = False
                qdrant_status["error"] = f"qdrant-client no instalado: {ie}"
            else:
                client = QdrantClient(url=settings.qdrant_url)
                colls = client.get_collections().collections
                qdrant_status["ok"] = True
                qdrant_status["collections"] = [c.name for c in colls]
        except Exception as e:
            qdrant_status["ok"] = False
            qdrant_status["error"] = str(e)

    return {
        "status": "ok" if mongo_ok else "degraded",
        "app": {"name": settings.app_name, "debug": settings.debug, "prefix": settings.api_prefix},
        "mongo": {
            "uri": settings.mongo_uri,
            "db": settings.mongo_db_name,
            "ok": mongo_ok,
            "error": mongo_error,
            "collections": collections_info,
        },
        "qdrant": qdrant_status,
    }

@router.post("/db-selftest")
async def db_selftest():
    db = await get_db()
    coll = db["diagnostics"]
    now = datetime.utcnow()
    payload = {"type": "selftest", "ts": now, "note": "diagnostics insert/read/delete"}
    try:
        res = await coll.insert_one(payload)
        _id = res.inserted_id
        read_doc = await coll.find_one({"_id": _id})
        deleted = await coll.delete_one({"_id": _id})
        return {
            "ok": True,
            "inserted_id": str(_id),
            "read_back": {"_id": str(read_doc["_id"]), "type": read_doc.get("type"), "ts": read_doc.get("ts")},
            "deleted_count": deleted.deleted_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB selftest error: {e}")

@router.post("/qdrant-smoke")
async def qdrant_smoke():
    from time import time
    settings = get_settings()
    if not getattr(settings, "qdrant_url", None):
        raise HTTPException(status_code=400, detail="qdrant_url no está configurado en settings/env")
    try:
        from qdrant_client import QdrantClient  # type: ignore
        from qdrant_client.http.models import Distance, VectorParams, PointStruct
    except ImportError as ie:
        raise HTTPException(status_code=503, detail=f"qdrant-client no instalado: {ie}")

    coll = "priorum_smoke"
    try:
        client = QdrantClient(url=settings.qdrant_url)
        client.recreate_collection(
            collection_name=coll,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )
        points = [
            PointStruct(id=1, vector=[0.1, 0.1, 0.1, 0.1], payload={"text": "hola mundo"}),
            PointStruct(id=2, vector=[0.9, 0.9, 0.9, 0.9], payload={"text": "reunión de planning"}),
        ]
        client.upsert(collection_name=coll, points=points)

        t0 = time()
        result = client.search(
            collection_name=coll,
            query_vector=[0.85, 0.85, 0.85, 0.85],
            limit=2,
        )
        dt_ms = int((time() - t0) * 1000)
        hits = [{"id": p.id, "score": p.score, "payload": p.payload} for p in result]
        return {"ok": True, "collection": coll, "latency_ms": dt_ms, "results": hits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant smoke error: {e}")
