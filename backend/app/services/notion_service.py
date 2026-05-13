"""
Servicio de integración con Notion.
Gestiona tareas almacenadas en una base de datos de Notion.
Usa httpx directamente (notion-client v3.x cambió la API interna).
"""
from typing import Optional
from datetime import date, timedelta
import uuid
import httpx

from app.config import get_settings
from app.models.task import Task, TaskCreate, TaskUpdate, Period

settings = get_settings()

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION  = "2022-06-28"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _clean_database_id(raw_id: str) -> str:
    """Normaliza el ID de la base de datos de Notion.

    Acepta cualquiera de estos formatos:
      - "66d467c5845b46dc81f773fe44d098ce"           (sin guiones)
      - "66d467c5-845b-46dc-81f7-73fe44d098ce"       (UUID estándar)
      - "66d467c5845b46dc81f773fe44d098ce?v=..."     (con parámetro de vista)
    Devuelve siempre el UUID con guiones que requiere la API de Notion.
    """
    clean = raw_id.split("?")[0].strip().replace("-", "")
    if len(clean) == 32:
        return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"
    return raw_id.split("?")[0].strip()


def _parse_notion_task(page: dict) -> Task:
    """Convierte una página de Notion en un objeto Task.

    Soporta tanto bases de datos con propiedades personalizadas (Prioridad, Fecha…)
    como bases de datos básicas (solo Name + Status).
    """
    props = page.get("properties", {})

    def text(*names: str) -> str:
        for name in names:
            prop = props.get(name, {})
            if prop.get("type") == "title":
                items = prop.get("title", [])
                result = "".join(i.get("plain_text", "") for i in items)
                if result:
                    return result
            elif prop.get("type") == "rich_text":
                items = prop.get("rich_text", [])
                result = "".join(i.get("plain_text", "") for i in items)
                if result:
                    return result
        return ""

    def select(*names: str) -> str:
        for name in names:
            prop = props.get(name, {})
            sel = prop.get("select") or {}
            val = sel.get("name", "").lower()
            if val:
                return val
        return ""

    def status_val(*names: str) -> str:
        """Lee campos de tipo 'status' (diferente de 'select')."""
        for name in names:
            prop = props.get(name, {})
            if prop.get("type") == "status":
                st = prop.get("status") or {}
                return st.get("name", "").lower()
        return ""

    def multi_select(*names: str) -> list[str]:
        for name in names:
            prop = props.get(name, {})
            vals = [o.get("name", "") for o in prop.get("multi_select", [])]
            if vals:
                return vals
        return []

    def checkbox(*names: str) -> bool:
        for name in names:
            val = props.get(name, {}).get("checkbox")
            if val is not None:
                return bool(val)
        return False

    def date_str(*names: str) -> str:
        for name in names:
            prop = props.get(name, {})
            d = prop.get("date") or {}
            val = d.get("start", "")
            if val:
                return val
            # created_time como fallback
            if prop.get("type") == "created_time":
                ct = prop.get("created_time", "")
                return ct[:10] if ct else ""
        return ""

    # Prioridad: campo select o status
    priority_raw = select("Prioridad", "Priority") or status_val("Prioridad", "Priority") or "media"
    priority_map = {
        "alta": "alta", "media": "media", "baja": "baja",
        "high": "alta", "medium": "media", "low": "baja",
        "urgent": "alta", "normal": "media",
    }
    priority = priority_map.get(priority_raw, "media")

    # Done: checkbox o status con valor "done"/"completado"/"hecho"
    done_status = status_val("Status", "Estado")
    done = checkbox("Hecho", "Done", "Completado") or done_status in ("done", "completado", "hecho", "complete")

    return Task(
        id=page["id"],
        notion_id=page["id"],
        title=text("Nombre", "Name", "Title"),
        project=text("Proyecto", "Project") or select("Proyecto", "Project"),
        priority=priority,  # type: ignore[arg-type]
        deadline=date_str("Fecha", "Deadline", "Due", "Date Created"),
        tags=multi_select("Etiquetas", "Tags"),
        done=done,
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
        if ref.month == 12:
            end = ref.replace(day=31)
        else:
            end = ref.replace(month=ref.month + 1, day=1) - timedelta(days=1)
        return start, end
    # year
    return ref.replace(month=1, day=1), ref.replace(month=12, day=31)


async def _get_db_properties(db_id: str) -> set[str]:
    """Devuelve el conjunto de nombres de propiedades de la base de datos."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{NOTION_API_BASE}/databases/{db_id}",
            headers=_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            return set(resp.json().get("properties", {}).keys())
    return set()


async def get_tasks(
    period: Period = Period.day,
    date_ref: Optional[str] = None,
    priority: Optional[str] = None,
    project: Optional[str] = None,
) -> list[Task]:
    """Obtiene tareas de Notion filtradas por período y criterios opcionales.

    Los filtros de fecha/prioridad/proyecto solo se aplican si la propiedad
    correspondiente existe en la base de datos.
    """
    if not settings.notion_api_key or not settings.notion_tasks_database_id:
        return _mock_tasks()

    db_id = _clean_database_id(settings.notion_tasks_database_id)

    # Detecta qué propiedades existen para no filtrar por campos inexistentes
    db_props = await _get_db_properties(db_id)

    ref = date.fromisoformat(date_ref) if date_ref else date.today()
    start, end = _date_range(period, ref)

    filters: list[dict] = []

    # Filtro de fecha solo si existe la propiedad
    date_prop = next((p for p in ["Fecha", "Deadline", "Due"] if p in db_props), None)
    if date_prop:
        filters.append({"property": date_prop, "date": {"on_or_after": start.isoformat()}})
        filters.append({"property": date_prop, "date": {"on_or_before": end.isoformat()}})

    # Filtro de prioridad solo si existe
    if priority:
        prio_prop = next((p for p in ["Prioridad", "Priority"] if p in db_props), None)
        if prio_prop:
            filters.append({"property": prio_prop, "select": {"equals": priority.capitalize()}})

    # Filtro de proyecto solo si existe
    if project:
        proj_prop = next((p for p in ["Proyecto", "Project"] if p in db_props), None)
        if proj_prop:
            filters.append({"property": proj_prop, "rich_text": {"contains": project}})

    body: dict = {}
    if filters:
        body["filter"] = {"and": filters} if len(filters) > 1 else filters[0]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{NOTION_API_BASE}/databases/{db_id}/query",
            headers=_headers(),
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return [_parse_notion_task(p) for p in data.get("results", [])]


async def create_task(data: TaskCreate) -> Task:
    """Crea una nueva tarea en Notion.

    Detecta las propiedades disponibles en la BD y solo envía las que existen,
    usando los nombres reales (Name/Nombre, Status/Prioridad, etc.).
    """
    if not settings.notion_api_key:
        return Task(id=str(uuid.uuid4()), **data.model_dump())

    db_id = _clean_database_id(settings.notion_tasks_database_id)

    # Obtiene las propiedades reales de la BD
    db_props = await _get_db_properties(db_id)

    # Mapeo: nombre interno → posibles nombres en Notion
    title_prop  = next((p for p in ["Nombre", "Name", "Title"] if p in db_props), None)
    proj_prop   = next((p for p in ["Proyecto", "Project"] if p in db_props), None)
    prio_prop   = next((p for p in ["Prioridad", "Priority"] if p in db_props), None)
    tags_prop   = next((p for p in ["Etiquetas", "Tags"] if p in db_props), None)
    date_prop   = next((p for p in ["Fecha", "Deadline", "Due"] if p in db_props), None)
    done_prop   = next((p for p in ["Hecho", "Done", "Completado"] if p in db_props), None)

    if not title_prop:
        raise ValueError(f"La BD de Notion no tiene campo de título. Propiedades disponibles: {db_props}")

    properties: dict = {
        title_prop: {"title": [{"text": {"content": data.title}}]},
    }
    if proj_prop and data.project:
        properties[proj_prop] = {"rich_text": [{"text": {"content": data.project}}]}
    if prio_prop and data.priority:
        properties[prio_prop] = {"select": {"name": data.priority.capitalize()}}
    if tags_prop and data.tags:
        properties[tags_prop] = {"multi_select": [{"name": t} for t in data.tags]}
    if date_prop and data.deadline:
        properties[date_prop] = {"date": {"start": data.deadline}}
    if done_prop:
        properties[done_prop] = {"checkbox": False}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{NOTION_API_BASE}/pages",
            headers=_headers(),
            json={"parent": {"database_id": db_id}, "properties": properties},
            timeout=15,
        )
        if not resp.is_success:
            raise ValueError(f"Notion API error {resp.status_code}: {resp.text}")
        return _parse_notion_task(resp.json())


async def update_task(task_id: str, data: TaskUpdate) -> Task:
    """Actualiza una tarea en Notion."""
    if not settings.notion_api_key:
        raise ValueError("Notion no configurado")

    db_id = _clean_database_id(settings.notion_tasks_database_id)
    db_props = await _get_db_properties(db_id)

    props: dict = {}
    if data.title is not None:
        title_prop = next((p for p in ["Nombre", "Name", "Title"] if p in db_props), None)
        if title_prop:
            props[title_prop] = {"title": [{"text": {"content": data.title}}]}
    if data.priority is not None:
        prio_prop = next((p for p in ["Prioridad", "Priority"] if p in db_props), None)
        if prio_prop:
            props[prio_prop] = {"select": {"name": data.priority.capitalize()}}
    if data.deadline is not None:
        date_prop = next((p for p in ["Fecha", "Deadline", "Due"] if p in db_props), None)
        if date_prop:
            props[date_prop] = {"date": {"start": data.deadline}}
    if data.done is not None:
        done_prop = next((p for p in ["Hecho", "Done", "Completado"] if p in db_props), None)
        if done_prop:
            props[done_prop] = {"checkbox": data.done}

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{NOTION_API_BASE}/pages/{task_id}",
            headers=_headers(),
            json={"properties": props},
            timeout=15,
        )
        if not resp.is_success:
            raise ValueError(f"Notion API error {resp.status_code}: {resp.text}")
        return _parse_notion_task(resp.json())


async def delete_task(task_id: str) -> None:
    """Archiva (elimina) una tarea en Notion."""
    if not settings.notion_api_key:
        return
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{NOTION_API_BASE}/pages/{task_id}",
            headers=_headers(),
            json={"archived": True},
            timeout=15,
        )
        resp.raise_for_status()


def _mock_tasks() -> list[Task]:
    """Datos de ejemplo cuando Notion no está configurado."""
    return [
        Task(id="1", title="Revisar PR del módulo de autenticación", project="Backend API",
             priority="alta",  # type: ignore[arg-type]
             deadline=date.today().isoformat(),
             tags=["code", "review"], subtasks=["Leer diff completo", "Ejecutar tests"],
             comments=["LGTM en general, revisar el middleware"], done=False),
        Task(id="2", title="Preparar demo para el cliente", project="Producto",
             priority="alta",  # type: ignore[arg-type]
             deadline=date.today().isoformat(),
             tags=["cliente"], subtasks=["Slides resumen", "Grabar video backup"],
             comments=[], done=False),
        Task(id="3", title="Documentar endpoints REST", project="Backend API",
             priority="media",  # type: ignore[arg-type]
             deadline=date.today().isoformat(),
             tags=["docs"], subtasks=[], comments=["Usar Swagger"], done=False),
        Task(id="4", title="Refactor del componente Table", project="Frontend",
             priority="baja",  # type: ignore[arg-type]
             deadline=date.today().isoformat(),
             tags=["code"], subtasks=[], comments=[], done=True),
    ]