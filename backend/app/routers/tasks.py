from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.models.task import Task, TaskCreate, TaskUpdate, Period
from app.services import notion_service

from app.services.jira_service import create_jira_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
async def list_tasks(
    period:   Period           = Query(Period.day, description="Período de filtrado"),
    date:     Optional[str]    = Query(None, description="Fecha de referencia YYYY-MM-DD"),
    priority: Optional[str]    = Query(None, description="Filtrar por prioridad: alta|media|baja"),
    project:  Optional[str]    = Query(None, description="Filtrar por nombre de proyecto"),
):
    """Devuelve las tareas de Notion filtradas por período y criterios opcionales."""
    return await notion_service.get_tasks(
        period=period,
        date_ref=date,
        priority=priority,
        project=project,
    )


@router.post("", response_model=Task, status_code=201)
async def create_task(data: TaskCreate):
    """Crea una nueva tarea en Notion."""
    return await notion_service.create_task(data)


@router.patch("/{task_id}", response_model=Task)
async def update_task(task_id: str, data: TaskUpdate):
    """Actualiza una tarea existente en Notion."""
    try:
        return await notion_service.update_task(task_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str):
    """Archiva (elimina) una tarea en Notion."""
    await notion_service.delete_task(task_id)


@router.post("/sync", status_code=200)
async def sync_tasks():
    """Fuerza una resincronización con Notion."""
    # En una implementación real, aquí se invalidaría la caché
    return {"status": "synced"}


@router.post("/{task_id}/comments", response_model=Task)
async def add_comment(task_id: str, body: dict):
    """Añade un comentario a una tarea."""
    comment = body.get("comment", "")
    if not comment:
        raise HTTPException(status_code=400, detail="El comentario no puede estar vacío")
    # En Notion los comentarios se gestionan como bloques; aquí se actualiza el campo
    return await notion_service.update_task(task_id, TaskUpdate(comments=[comment]))

@router.post("/jira", status_code=201)
async def create_task_in_jira(data: TaskCreate):
    """
    Crea una tarea directamente en Jira
    """
    return await create_jira_task(data)