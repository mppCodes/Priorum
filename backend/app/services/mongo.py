# app/services/mongo.py
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.config import get_settings

settings = get_settings()

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _get_db_name() -> str:
    """
    Obtiene el nombre de la BD desde settings con compatibilidad:
    - settings.mongo_db_name
    - settings.mongo_db
    - por defecto: 'priorum'
    """
    return (
        getattr(settings, "mongo_db_name", None)
        or getattr(settings, "mongo_db", None)
        or "priorum"
    )


def _to_str_id(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return doc
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def _oid(id_str: str) -> ObjectId:
    return ObjectId(id_str)


async def init_db() -> None:
    """
    Inicializa cliente y BD y crea índices necesarios (async).
    """
    global _client, _db
    if _client is not None and _db is not None:
        return

    _client = AsyncIOMotorClient(settings.mongo_uri)
    _db = _client[_get_db_name()]

    # Índices de colecciones operacionales
    await _db[settings.mongo_tasks_collection].create_index(
        [("external_id", ASCENDING)], unique=True, sparse=True
    )
    await _db[settings.mongo_tasks_collection].create_index([("due_date", ASCENDING)])

    await _db[settings.mongo_events_collection].create_index(
        [("external_id", ASCENDING)], unique=True, sparse=True
    )
    await _db[settings.mongo_events_collection].create_index([("start", ASCENDING)])
    await _db[settings.mongo_events_collection].create_index([("end", ASCENDING)])

    await _db[settings.mongo_agent_msgs_collection].create_index(
        [("session_id", ASCENDING), ("created_at", ASCENDING)]
    )

    # Índices de caché
    await _db[settings.mongo_tasks_cache_collection].create_index(
        [("external_id", ASCENDING)], unique=True
    )
    await _db[settings.mongo_tasks_cache_collection].create_index([("cached_at", ASCENDING)])

    await _db[settings.mongo_events_cache_collection].create_index(
        [("external_id", ASCENDING)], unique=True
    )
    await _db[settings.mongo_events_cache_collection].create_index([("cached_at", ASCENDING)])

    # TTL para caché si está habilitado
    if getattr(settings, "mongo_cache_ttl_seconds", 0) and settings.mongo_cache_ttl_seconds > 0:
        await _db[settings.mongo_tasks_cache_collection].create_index(
            [("cached_at", ASCENDING)], expireAfterSeconds=settings.mongo_cache_ttl_seconds
        )
        await _db[settings.mongo_events_cache_collection].create_index(
            [("cached_at", ASCENDING)], expireAfterSeconds=settings.mongo_cache_ttl_seconds
        )

    # Índices y TTL para logs del agente
    await _db[settings.mongo_agent_logs_collection].create_index(
        [("session_id", ASCENDING), ("created_at", ASCENDING)]
    )
    await _db[settings.mongo_agent_logs_collection].create_index([("created_at", ASCENDING)])
    if getattr(settings, "mongo_agent_logs_ttl_seconds", 0) and settings.mongo_agent_logs_ttl_seconds > 0:
        await _db[settings.mongo_agent_logs_collection].create_index(
            [("created_at", ASCENDING)], expireAfterSeconds=settings.mongo_agent_logs_ttl_seconds
        )


def close_db() -> None:
    """
    Cierra el cliente si existe.
    """
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


async def get_db() -> AsyncIOMotorDatabase:
    """
    Devuelve la BD; inicializa si es necesario.
    """
    if _db is None:
        await init_db()
    assert _db is not None
    return _db


# Eventos: utilidades de rango y sync
async def list_events_between(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    """
    Devuelve eventos que se solapan con [start, end].
    """
    db = await get_db()
    q = {
        "$and": [
            {"start": {"$lt": end}},
            {"end": {"$gt": start}},
        ]
    }
    cursor = db[settings.mongo_events_collection].find(q).sort("start", ASCENDING)
    return [_to_str_id(doc) async for doc in cursor]


async def create_event(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un evento y devuelve el documento insertado con id como string.
    """
    db = await get_db()
    payload = dict(doc)
    now = datetime.utcnow()
    payload.setdefault("created_at", now)
    payload["updated_at"] = now
    res = await db[settings.mongo_events_collection].insert_one(payload)
    created = await db[settings.mongo_events_collection].find_one({"_id": res.inserted_id})
    return _to_str_id(created)  # type: ignore


async def get_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    try:
        oid = _oid(event_id)
    except Exception:
        return None
    doc = await db[settings.mongo_events_collection].find_one({"_id": oid})
    return _to_str_id(doc) if doc else None


async def get_event_by_external_id(external_id: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    doc = await db[settings.mongo_events_collection].find_one({"external_id": external_id})
    return _to_str_id(doc) if doc else None


async def upsert_event_by_external_id(external_id: str, ev: Any) -> Dict[str, Any]:
    """
    Upsert de un evento proveniente de Outlook (u otra fuente) por external_id.
    ev puede ser pydantic Event o dict con las claves relevantes.
    """
    db = await get_db()
    data = ev.model_dump(exclude_unset=True) if hasattr(ev, "model_dump") else dict(ev)
    now = datetime.utcnow()
    data["external_id"] = external_id
    data.setdefault("source", "outlook")
    data.setdefault("created_at", now)
    data["updated_at"] = now

    await db[settings.mongo_events_collection].update_one(
        {"external_id": external_id},
        {"$set": data},
        upsert=True,
    )
    doc = await db[settings.mongo_events_collection].find_one({"external_id": external_id})
    return _to_str_id(doc)  # type: ignore


async def update_event_by_id(event_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = await get_db()
    try:
        oid = _oid(event_id)
    except Exception:
        return None
    await db[settings.mongo_events_collection].update_one({"_id": oid}, {"$set": fields})
    return await get_event_by_id(event_id)


async def delete_event_by_id(event_id: str) -> bool:
    db = await get_db()
    try:
        oid = _oid(event_id)
    except Exception:
        return False
    res = await db[settings.mongo_events_collection].delete_one({"_id": oid})
    return res.deleted_count == 1


# --- Tareas: CRUD y listados ---

async def create_task(doc: Dict[str, Any]) -> Dict[str, Any]:
    db = await get_db()
    payload = dict(doc)
    # Normaliza due_date a 'YYYY-MM-DD' si viene con hora
    if "due_date" in payload and payload["due_date"]:
        payload["due_date"] = str(payload["due_date"])[:10]
    res = await db[settings.mongo_tasks_collection].insert_one(payload)
    created = await db[settings.mongo_tasks_collection].find_one({"_id": res.inserted_id})
    return _to_str_id(created)  # type: ignore


async def list_tasks_between(
    start_iso: str,
    end_iso: str,
    priority: Optional[str] = None,
    project: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Lista tareas cuyo due_date (string 'YYYY-MM-DD') esté entre [start_iso, end_iso].
    Aplica filtros opcionales por priority y project.
    """
    db = await get_db()
    q: Dict[str, Any] = {"due_date": {"$gte": start_iso, "$lte": end_iso}}
    if priority:
        q["priority"] = priority.lower()
    if project:
        q["project"] = project

    cursor = db[settings.mongo_tasks_collection].find(q).sort("due_date", ASCENDING)
    return [_to_str_id(doc) async for doc in cursor]


async def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    try:
        oid = _oid(task_id)
    except Exception:
        return None
    doc = await db[settings.mongo_tasks_collection].find_one({"_id": oid})
    return _to_str_id(doc) if doc else None


async def update_task_by_id(task_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = await get_db()
    try:
        oid = _oid(task_id)
    except Exception:
        return None
    if "due_date" in fields and fields["due_date"]:
        fields["due_date"] = str(fields["due_date"])[:10]
    await db[settings.mongo_tasks_collection].update_one({"_id": oid}, {"$set": fields})
    return await get_task_by_id(task_id)


async def delete_task_by_id(task_id: str) -> bool:
    db = await get_db()
    try:
        oid = _oid(task_id)
    except Exception:
        return False
    res = await db[settings.mongo_tasks_collection].delete_one({"_id": oid})
    return res.deleted_count == 1

# --- Tareas: CRUD y listados ---

async def create_task(doc: Dict[str, Any]) -> Dict[str, Any]:
    db = await get_db()
    payload = dict(doc)
    if "due_date" in payload and payload["due_date"]:
        payload["due_date"] = str(payload["due_date"])[:10]
    res = await db[settings.mongo_tasks_collection].insert_one(payload)
    created = await db[settings.mongo_tasks_collection].find_one({"_id": res.inserted_id})
    return _to_str_id(created)  # type: ignore

async def list_tasks_between(
    start_iso: str,
    end_iso: str,
    priority: Optional[str] = None,
    project: Optional[str] = None,
) -> List[Dict[str, Any]]:
    db = await get_db()
    q: Dict[str, Any] = {"due_date": {"$gte": start_iso, "$lte": end_iso}}
    if priority:
        q["priority"] = priority.lower()
    if project:
        q["project"] = project
    cursor = db[settings.mongo_tasks_collection].find(q).sort("due_date", ASCENDING)
    return [_to_str_id(doc) async for doc in cursor]

async def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    try:
        oid = _oid(task_id)
    except Exception:
        return None
    doc = await db[settings.mongo_tasks_collection].find_one({"_id": oid})
    return _to_str_id(doc) if doc else None

async def update_task_by_id(task_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = await get_db()
    try:
        oid = _oid(task_id)
    except Exception:
        return None
    if "due_date" in fields and fields["due_date"]:
        fields["due_date"] = str(fields["due_date"])[:10]
    await db[settings.mongo_tasks_collection].update_one({"_id": oid}, {"$set": fields})
    return await get_task_by_id(task_id)

async def delete_task_by_id(task_id: str) -> bool:
    db = await get_db()
    try:
        oid = _oid(task_id)
    except Exception:
        return False
    res = await db[settings.mongo_tasks_collection].delete_one({"_id": oid})
    return res.deleted_count == 1

# --- Tareas: listado sin rango ---

async def list_tasks_all(
    priority: Optional[str] = None,
    project: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Lista TODAS las tareas (sin filtro de fecha). Aplica filtros opcionales.
    Ordena por due_date asc (nulas al final) y created_at desc como secundario.
    """
    db = await get_db()
    q: Dict[str, Any] = {}
    if priority:
        q["priority"] = priority.lower()
    if project:
        q["project"] = project

    # Orden: due_date asc, luego created_at desc (si existen)
    sort_spec = [("due_date", ASCENDING), ("created_at", DESCENDING)]
    cursor = db[settings.mongo_tasks_collection].find(q).sort(sort_spec)
    return [_to_str_id(doc) async for doc in cursor]

async def create_event(doc: Dict[str, Any]) -> Dict[str, Any]:
    db = await get_db()
    payload = dict(doc)
    now = datetime.utcnow()
    payload.setdefault("source", "local")
    payload.setdefault("created_at", now)
    payload["updated_at"] = now
    res = await db[settings.mongo_events_collection].insert_one(payload)
    created = await db[settings.mongo_events_collection].find_one({"_id": res.inserted_id})
    return _to_str_id(created)  # type: ignore

from typing import Any  # si no lo tienes ya importado

async def upsert_task_by_external_id(external_id: str, task: Any) -> Dict[str, Any]:
    """
    Upsert de una tarea proveniente de Notion por external_id.
    'task' puede ser un modelo Pydantic (con .model_dump) o un dict.
    """
    db = await get_db()
    data = task.model_dump(exclude_unset=True) if hasattr(task, "model_dump") else dict(task)
    now = datetime.utcnow()
    data["external_id"] = external_id
    data.setdefault("source", "notion")
    data.setdefault("created_at", now)
    data["updated_at"] = now

    await db[settings.mongo_tasks_collection].update_one(
        {"external_id": external_id},
        {"$set": data},
        upsert=True,
    )
    doc = await db[settings.mongo_tasks_collection].find_one({"external_id": external_id})
    return _to_str_id(doc)  # type: ignore
