# Documentación del Backend de Priorum

Esta documentación explica paso a paso el código en la carpeta `backend` y ayudará a identificar puntos clave para futuras integraciones como bases de datos (BBDD) o un MCP (Model Context Protocol).

---

## 1. Estructura general

El backend está organizado con **FastAPI** y una estructura modular:
- `main.py` → punto de entrada, inicializa la app y registra middleware y routers.
- `app/config.py` → configuración de la aplicación mediante variables de entorno.
- `app/models` → definiciones de modelos de datos con **Pydantic**.
- `app/routers` → rutas agrupadas por dominio (Tareas, Calendario, Agente IA).
- `app/services` → lógica de negocio, comunicación con APIs externas (Notion, Outlook, OpenAI, Jira).
- `logging_config.py` → configuración central de logs.
- `docs/db_schema.md` → esquema de la base de datos.

---

## 2. main.py
- Crea una instancia de `FastAPI` con título, versión y rutas de documentación `/api/docs`.
- Añade middleware CORS configurable.
- Incluye routers (`tasks`, `calendar`, `agent`, otros nuevos como Jira si aplica) con prefijo común `settings.api_prefix`.
- Define endpoint `/api/health` para verificar estado.
- **Nueva integración BBDD**: Inicializa conexión global a la base de datos y sesión antes de incluir routers.

**Posible integración MCP**: Se podría añadir un router o endpoint específico para herramientas MCP.

---

## 3. config.py
- Usa `BaseSettings` (pydantic_settings) para cargar configuración desde `.env`.
- Variables para Notion, Microsoft Graph, OpenAI, Jira, CORS, nombre de aplicación y ahora credenciales de base de datos (host, puerto, usuario, contraseña, nombre).
- `get_settings()` con **lru_cache** para que sea singleton.

**Punto clave MCP**: Añadir configuración de endpoints MCP y tokens.

---

## 4. app/models

### agent.py
- Modelos para interacción con el agente IA (`ChatMessage`, `ChatRequest`, `ChatResponse`).
- Entidades para prioridades y calendario.

### event.py
- Enum `EventType` y modelos para eventos calendario.

### task.py
- Enums `Priority`, `Period` y modelos para tareas.
- Integración con BBDD: adaptados para ORM (SQLAlchemy) manteniendo validación Pydantic.

**Posible integración MCP**: Añadir modelos específicos para datos recibidos o enviados a MCP.

---

## 5. app/routers

### agent.py
- Endpoints para chat IA, prioridades, horarios, historial y limpieza de historial.
- Usa servicios del agente IA.

### calendar.py
- Endpoints CRUD para eventos calendario y sincronización.
- Usa `outlook_service`.

### tasks.py
- Endpoints CRUD para tareas, sincronización y comentarios.
- Usa `notion_service` y ahora también interacción con la base de datos.

### jira_service.py (en routers o servicios)
- Endpoints para integrar y sincronizar tareas/eventos con Jira.
- Usa `jira_service` para la lógica.

**Posible integración MCP**: Añadir endpoints que interactúen con MCP.

---

## 6. app/services

### ai_agent_service.py
- Conecta con OpenAI (`_get_openai_client`).
- Funciones para chat, prioridades, horario, historial.
- Mock para pruebas.

### notion_service.py
- Conexión cliente Notion.
- CRUD de tareas.
- Mock para pruebas.

### outlook_service.py
- Conexión Microsoft Graph.
- CRUD de eventos.
- Mock para pruebas.

### jira_service.py
- Conexión cliente Jira usando API REST.
- CRUD de incidencias/tareas.
- Sincronización con BBDD.

**Integración BBDD**: Servicios consultan y actualizan información en la base de datos.

**Posible integración MCP**: Añadir servicio que llame a MCP y procese resultados.

---

## 7. logging_config.py
- Establece formato y nivel de logs para toda la aplicación.
- Útil para depuración e integración de MCP (monitorizar requests/responses).

---

## 8. docs/db_schema.md
- Describe las tablas, campos y relaciones de la base de datos.
- Documentación clave para adaptar servicios y routers a persistencia.

---

## 9. Comentarios sugeridos en el código
En puntos clave (conexiones externas, estructuras de datos, configuración), añadir comentarios para indicar dónde se integrará MCP y cómo interactúa con la base de datos.

---

## 10. Próximos pasos
1. Revisar y comentar la inicialización de la BBDD en `main.py`.
2. Documentar dependencias e interacciones entre servicios y la base de datos.
3. Diseñar endpoints MCP y definir modelos asociados.
4. Actualizar esta documentación conforme se implementen cambios.