# app/services/tasks_service.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

from app.config import get_settings
from app.models.task import Task, TaskCreate, TaskUpdate, Period
from app.services import notion_service
from app.services.mongo import (
    create_task as mongo_create_task,
    list_tasks_between as mongo_list_tasks_between,
    list_tasks_all as mongo_list_tasks_all,
    update_task_by_id as mongo_update_task_by_id,
    delete_task_by_id as mongo_delete_task_by_id,
    upsert_task_by_external_id,
    get_task_by_id as mongo_get_task_by_id,
)

settings = get_settings()


def _date_range(period: Period, ref: Optional[date] = None) -> Tuple[str, str]:
    """
    Devuelve (start_iso, end_iso) para filtrar por due_date guardado como 'YYYY-MM-DD'.
    """
    day = ref or date.today()
    if period == Period.day:
        start = day
        end = day
    elif period == Period.week:
        monday = day - timedelta(days=day.weekday())
        start = monday
        end = monday + timedelta(days=6)
    elif period == Period.month:
        start = date(day.year, day.month, 1)
        if day.month == 12:
            end = date(day.year, 12, 31)
        else:
            end = date(day.year, day.month + 1, 1) - timedelta(days=1)
    else:  # Period.year
        start = date(day.year, 1, 1)
        end = date(day.year, 12, 31)
    return (start.isoformat(), end.isoformat())


def _notion_enabled() -> bool:
    return bool(getattr(settings, "notion_api_key", "")) and bool(getattr(settings, "notion_tasks_database_id", ""))


async def _pull_from_notion(
    period: Period,
    date_ref: Optional[str],
    priority: Optional[str],
    project: Optional[str],
) -> None:
    """
    Hace pull de Notion y upsert en Mongo por external_id.
    Si falla, no interrumpe el flujo.
    """
    try:
        remote_tasks = await notion_service.get_tasks(
            period=period, date_ref=date_ref, priority=priority, project=project
        )
        for t in remote_tasks:
            ext_id = getattr(t, "external_id", None) or getattr(t, "id", None)
            if not ext_id:
                continue
            await upsert_task_by_external_id(ext_id, t)
    except Exception:
        # Evitar romper el listado por fallos del conector
        pass


async def get_tasks(
    period: Period = Period.day,
    date_ref: Optional[str] = None,
    priority: Optional[str] = None,
    project: Optional[str] = None,
) -> List[Task]:
    """
    - Si Notion está configurado: pull desde Notion (upsert en Mongo) y devolver desde Mongo.
    - Si NO hay parámetros (period por defecto, sin date/prioridad/proyecto): devuelve TODAS.
    - Si hay parámetros: devuelve filtrado por rango y criterios.
    """
    if _notion_enabled():
        await _pull_from_notion(period, date_ref, priority, project)

    if (date_ref is None) and (priority is None) and (project is None):
        docs = await mongo_list_tasks_all()
        return [Task.model_validate(d) for d in docs]

    ref = date.fromisoformat(date_ref) if date_ref else date.today()
    start_iso, end_iso = _date_range(period, ref)
    docs = await mongo_list_tasks_between(start_iso, end_iso, priority=priority, project=project)
    return [Task.model_validate(d) for d in docs]


async def create_task(data: TaskCreate) -> Task:
    """
    Crea la tarea en Mongo (memoria) y, si Notion está configurado, también en Notion.
    Guarda external_id en Mongo si Notion devuelve un id.
    """
    payload: Dict[str, Any] = data.model_dump(exclude_unset=True)
    # Normaliza due_date a 'YYYY-MM-DD'
    if payload.get("due_date"):
        payload["due_date"] = str(payload["due_date"])[:10]

    now = datetime.utcnow()
    payload.setdefault("source", "local")
    payload.setdefault("created_at", now)
    payload["updated_at"] = now

    created = await mongo_create_task(payload)
    created_task = Task.model_validate(created)

    if _notion_enabled():
        try:
            remote = await notion_service.create_task(data)
            ext_id = getattr(remote, "external_id", None) or getattr(remote, "id", None)
            if ext_id:
                await mongo_update_task_by_id(created_task.id, {
                    "external_id": ext_id,
                    "source": "notion",
                    "updated_at": datetime.utcnow(),
                })
                refreshed = await mongo_get_task_by_id(created_task.id)
                if refreshed:
                    return Task.model_validate(refreshed)
        except Exception:
            # Mantener la local aunque falle Notion
            pass

    return created_task


async def update_task(task_id: str, data: TaskUpdate) -> Task:
    """
    Actualiza en Mongo y, si está vinculada y Notion está configurado, actualiza en Notion.
    """
    fields: Dict[str, Any] = data.model_dump(exclude_unset=True)
    if fields.get("due_date"):
        fields["due_date"] = str(fields["due_date"])[:10]
    fields["updated_at"] = datetime.utcnow()

    updated = await mongo_update_task_by_id(task_id, fields)
    if not updated:
        raise ValueError("Task not found")

    if _notion_enabled():
        try:
            existing = await mongo_get_task_by_id(task_id)
            ext_id = existing.get("external_id") if existing else None
            if ext_id:
                await notion_service.update_task(ext_id, data)
                await mongo_update_task_by_id(task_id, {"updated_at": datetime.utcnow()})
                refreshed = await mongo_get_task_by_id(task_id)
                if refreshed:
                    return Task.model_validate(refreshed)
        except Exception:
            pass

    return Task.model_validate(updated)


async def delete_task(task_id: str) -> None:
    """
    Borra en Notion (si procede) y en Mongo.
    """
    existing = await mongo_get_task_by_id(task_id)
    if not existing:
        return None
    ext_id = existing.get("external_id")

    if _notion_enabled() and ext_id:
        try:
            await notion_service.delete_task(ext_id)
        except Exception:
            # Si falla Notion, priorizamos borrado local
            pass

    await mongo_delete_task_by_id(task_id)
    return None
