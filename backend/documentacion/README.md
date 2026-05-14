# Documentación del Backend de Priorum

Esta documentación explica paso a paso el código en la carpeta `backend` y ayudará a identificar puntos clave para futuras integraciones como bases de datos (BBDD) o un MCP (Model Context Protocol).

---

## 1. Estructura general

El backend está organizado con **FastAPI** y una estructura modular:
- `main.py` → punto de entrada, inicializa la app y registra middleware y routers.
- `app/config.py` → configuración de la aplicación mediante variables de entorno.
- `app/models` → definiciones de modelos de datos con **Pydantic** y adaptaciones ORM.
- `app/routers` → rutas agrupadas por dominio (Tareas, Calendario, Agente IA, Jira).
- `app/services` → lógica de negocio, comunicación con APIs externas (Notion, Outlook, OpenAI, Jira, BBDD).
- `logging_config.py` → configuración central de logs.
- `docs/db_schema.md` → esquema de la base de datos.
- `mcp/` → integración MCP para creación de tareas Jira.

---

## 2. main.py
- Crea instancia de `FastAPI` con título, versión y rutas de documentación.
- Añade middleware CORS configurable.
- Incluye routers (`tasks`, `calendar`, `agent`, `jira`) con prefijo común `settings.api_prefix`.
- Endpoint `/api/health` para verificar estado.
- Inicializa conexión global a la base de datos y sesión antes de incluir routers.
  
**Integración MCP**: Puede añadirse un router MCP para exponer herramientas a través de la API.

---

## 3. config.py
- Usa `BaseSettings` para cargar configuración desde `.env`.
- Variables para Notion, Microsoft Graph, OpenAI, Jira, CORS, nombre de app y credenciales de BBDD.
- `get_settings()` usa `lru_cache` para mantener una sola instancia.
- Credenciales MCP y configuración de entornos pueden añadirse aquí.

---

## 4. app/models
### agent.py
Modelos para interacción IA (`ChatMessage`, `ChatRequest`, `ChatResponse`).

### event.py
Enum `EventType`, modelos para eventos calendario.

### task.py
Enums `Priority`, `Period`; integración ORM para persistencia.

**Integración MCP**: Modelos para datos a enviar/recibir de un servidor MCP.

---

## 5. app/routers
### agent.py
Endpoints IA para chat, prioridades, horario e historial.

### calendar.py
Endpoints CRUD y sincronización, usa `outlook_service`.

### tasks.py
CRUD de tareas, sincronización y comentarios, usa `notion_service` y BBDD.

### jira.py
Endpoints CRUD de tareas en Jira, sincronización con BBDD.

---

## 6. app/services
### ai_agent_service.py
Conecta con OpenAI, funciones para chat y prioridades.

### notion_service.py
Conexión al cliente Notion, CRUD de tareas.

### outlook_service.py
Conexión Microsoft Graph, CRUD de eventos.

### jira_service.py
Conexión Jira REST API, CRUD y sincronización con BBDD.

---

## 7. logging_config.py
Formato y nivel de logs globales; clave para monitoreo e integración MCP.

---

## 8. docs/db_schema.md
Esquema de BBDD con tablas, campos y relaciones.

---

## 9. mcp/jira_task_server
Servidor MCP que expone herramienta `create_jira_task` usando `jira_service` con credenciales proporcionadas.

---

## 10. Comentarios sugeridos
Añadir comentarios en código para indicar puntos de interacción MCP y conexión BBDD.

---

## 11. Próximos pasos
1. Documentar detalladamente `mcp/jira_task_server`.
2. Ampliar descripción de integración BBDD.
3. Definir endpoints MCP futuros.
4. Mantener documentación sincronizada con cambios.