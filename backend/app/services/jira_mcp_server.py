from fastmcp import FastMCP
from app.models.task import TaskCreate
from app.services.jira_service import create_jira_task

mcp = FastMCP("JiraManager")

@mcp.tool()
async def crear_tarjeta_jira(
    titulo: str,
    prioridad: str = "media",
    proyecto: str = "",
    fecha_limite: str = "",
    etiquetas: list[str] = None
) -> dict:
    """
    Crea una tarjeta (issue) en Jira.
    Args:
        titulo: título de la tarea
        prioridad: alta, media, baja
        proyecto: nombre del proyecto
        fecha_limite: fecha límite 'YYYY-MM-DD'
        etiquetas: lista de etiquetas
    """
    task_data = TaskCreate(
        title=titulo,
        priority=prioridad,
        project=proyecto,
        deadline=fecha_limite,
        tags=etiquetas or []
    )
    result = await create_jira_task(task_data)
    return {"mensaje": "Tarjeta creada en Jira", "resultado": result}

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8001)