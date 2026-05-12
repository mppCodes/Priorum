"""
Servicio de integración con Notion.
Gestiona tareas almacenadas en una base de datos de Notion.
"""
from typing import Optional
from datetime import date, timedelta
import uuid

from app.config import get_settings
from app.models.task import Task, TaskCreate, TaskUpdate, Period

settings = get_settings()


def _get_client():
    """Devuelve el cliente de Notion. Importación lazy para evitar errores si no está instalado."""
    from notion_client import Client
    return Client(auth=settings.notion_api_key)


def _parse_notion_task(page: dict) -> Task:
    """Convierte una página de Notion en un objeto Task."""
    props = page.get("properties", {})

    def text(prop_name: str) -> str:
        prop = props.get(prop_name, {})
        if prop.get("type") == "title":
            items = prop.get("title", [])
        elif prop.get("type") == "rich_text":
            items = prop.get("rich_text", [])
        else:
            return ""
        return "".join(i.get("plain_text", "") for i in items)

    def select(prop_name: str) -> str:
        prop = props.get(prop_name, {})
        sel = prop.get("select") or {}
        return sel.get("name", "").lower()

    def multi_select(prop_name: str) -> list[str]:
        prop = props.get(prop_name, {})
        return [o.get("name", "") for o in prop.get("multi_select", [])]

    def checkbox(prop_name: str) -> bool:
        return props.get(prop_name, {}).get("checkbox", False)

    def date_str(prop_name: str) -> str:
        prop = props.get(prop_name, {})
        d = prop.get("date") or {}
        return d.get("start", "")

    return Task(
        id=page["id"],
        notion_id=page["id"],
        title=text("Nombre") or text("Name") or text("Title"),
        project=text("Proyecto") or text("Project") or select("Proyecto") or select("Project"),
        priority=select("Prioridad") or select("Priority") or "media",
        deadline=date_str("Fecha") or date_str("Deadline") or date_str("Due"),
        tags=multi_select("Etiquetas") or multi_select("Tags"),
        done=checkbox("Hecho") or checkbox("Done") or checkbox("Completado"),
        subtasks=[],
        comments=[],
    )


def _date_range(period: Period, reference: Optional[date] = None) -> tuple[date, date]:
    """Calcula el rango de fechas para el período dado."""
    ref = reference or date.today()
    if period == Period.day:
        return ref, ref
    if period == Period.week:
        start = ref - timedelta(days=ref.weekday())
        return start, start + timedelta(days=6)
    if period == Period.month:
        start = ref.replace(day=1)
        # último día del mes
        if ref.month == 12:
            end = ref.replace(day=31)
        else:
            end = ref.replace(month=ref.month + 1, day=1) - timedelta(days=1)
        return start, end
    # year
    return ref.replace(month=1, day=1), ref.replace(month=12, day=31)


async def get_tasks(
    period: Period = Period.day,
    date_ref: Optional[str] = None,
    priority: Optional[str] = None,
    project: Optional[str] = None,
) -> list[Task]:
    """Obtiene tareas de Notion filtradas por período y criterios opcionales."""
    if not settings.notion_api_key or not settings.notion_tasks_database_id:
        # Devuelve datos de ejemplo si no hay credenciales configuradas
        return _mock_tasks()

    client = _get_client()
    ref = date.fromisoformat(date_ref) if date_ref else date.today()
    start, end = _date_range(period, ref)

    filters: list[dict] = [
        {
            "property": "Fecha",
            "date": {"on_or_after": start.isoformat()},
        },
        {
            "property": "Fecha",
            "date": {"on_or_before": end.isoformat()},
        },
    ]

    if priority:
        filters.append({"property": "Prioridad", "select": {"equals": priority.capitalize()}})
    if project:
        filters.append({"property": "Proyecto", "rich_text": {"contains": project}})

    response = client.databases.query(
        database_id=settings.notion_tasks_database_id,
        filter={"and": filters} if len(filters) > 1 else filters[0],
        sorts=[{"property": "Fecha", "direction": "ascending"}],
    )

    return [_parse_notion_task(p) for p in response.get("results", [])]


async def create_task(data: TaskCreate) -> Task:
    """Crea una nueva tarea en Notion."""
    if not settings.notion_api_key:
        task = Task(id=str(uuid.uuid4()), **data.model_dump())
        return task

    client = _get_client()
    page = client.pages.create(
        parent={"database_id": settings.notion_tasks_database_id},
        properties={
            "Nombre": {"title": [{"text": {"content": data.title}}]},
            "Proyecto": {"rich_text": [{"text": {"content": data.project}}]},
            "Prioridad": {"select": {"name": data.priority.capitalize()}},
            "Fecha": {"date": {"start": data.deadline}} if data.deadline else {},
            "Etiquetas": {"multi_select": [{"name": t} for t in data.tags]},
        },
    )
    return _parse_notion_task(page)


async def update_task(task_id: str, data: TaskUpdate) -> Task:
    """Actualiza una tarea en Notion."""
    if not settings.notion_api_key:
        raise ValueError("Notion no configurado")

    client = _get_client()
    props: dict = {}
    if data.title is not None:
        props["Nombre"] = {"title": [{"text": {"content": data.title}}]}
    if data.priority is not None:
        props["Prioridad"] = {"select": {"name": data.priority.capitalize()}}
    if data.deadline is not None:
        props["Fecha"] = {"date": {"start": data.deadline}}
    if data.done is not None:
        props["Hecho"] = {"checkbox": data.done}

    page = client.pages.update(page_id=task_id, properties=props)
    return _parse_notion_task(page)


async def delete_task(task_id: str) -> None:
    """Archiva (elimina) una tarea en Notion."""
    if not settings.notion_api_key:
        return
    client = _get_client()
    client.pages.update(page_id=task_id, archived=True)


def _mock_tasks() -> list[Task]:
    """Datos de ejemplo cuando Notion no está configurado."""
    return [
        Task(id="1", title="Revisar PR del módulo de autenticación", project="Backend API",
             priority="alta", deadline=date.today().isoformat(),
             tags=["code", "review"], subtasks=["Leer diff completo", "Ejecutar tests"],
             comments=["LGTM en general, revisar el middleware"], done=False),
        Task(id="2", title="Preparar demo para el cliente", project="Producto",
             priority="alta", deadline=date.today().isoformat(),
             tags=["cliente"], subtasks=["Slides resumen", "Grabar video backup"],
             comments=[], done=False),
        Task(id="3", title="Documentar endpoints REST", project="Backend API",
             priority="media", deadline=date.today().isoformat(),
             tags=["docs"], subtasks=[], comments=["Usar Swagger"], done=False),
        Task(id="4", title="Refactor del componente Table", project="Frontend",
             priority="baja", deadline=date.today().isoformat(),
             tags=["code"], subtasks=[], comments=[], done=True),
    ]