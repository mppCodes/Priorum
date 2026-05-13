from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING

from app.config import get_settings

settings = get_settings()

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None

def _to_str_id(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return doc
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc

def _oid(id_str: str) -> ObjectId:
    return ObjectId(id_str)

async def init_db():
    global _client, _db
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
        _db = _client[settings.mongo_db_name]

        # Índices de colecciones operacionales
        await _db[settings.mongo_tasks_collection].create_index(
            [("external_id", ASCENDING)], unique=True, sparse=True
        )
        await _db[settings.mongo_tasks_collection].create_index([("due_date", ASCENDING)])
        await _db[settings.mongo_events_collection].create_index(
            [("external_id", ASCENDING)], unique=True, sparse=True
        )
        await _db[settings.mongo_events_collection].create_index([("start", ASCENDING)])
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

async def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        await init_db()
    return _db
