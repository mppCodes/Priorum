# Documentación del Backend de Priorum

Esta documentación explica paso a paso el código en la carpeta `backend` y ayudará a identificar puntos clave para futuras integraciones como bases de datos (BBDD) o un MCP (Model Context Protocol).

---

## 1. Estructura general

El backend está organizado con **FastAPI** y una estructura modular:
- `main.py` → punto de entrada, inicializa la app y registra middleware y routers.
- `app/config.py` → configuración de la aplicación mediante variables de entorno.
- `app/models` → definiciones de modelos de datos con **Pydantic**.
- `app/routers` → rutas agrupadas por dominio (Tareas, Calendario, Agente IA).
- `app/services` → lógica de negocio, comunicación con APIs externas (Notion, Outlook, OpenAI).

---

## 2. main.py
- Crea una instancia de `FastAPI` con título, versión y rutas de documentación `/api/docs`.
- Añade middleware CORS configurable.
- Incluye routers (`tasks`, `calendar`, `agent`) con prefijo común `settings.api_prefix`.
- Define endpoint `/api/health` para verificar estado.
  
**Posible integración BBDD**: Aquí se podría registrar la conexión global antes de incluir routers.  
**Posible integración MCP**: Se podría añadir un router o endpoint específico para herramientas MCP.

---

## 3. config.py
- Usa `BaseSettings` (pydantic_settings) para cargar configuración desde `.env`.
- Variables para Notion, Microsoft Graph, OpenAI, CORS y nombre de aplicación.
- `get_settings()` con **lru_cache** para que sea singleton.
  
**Punto clave BBDD**: Añadir credenciales y configuración de la base de datos aquí.  
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

**Posible integración BBDD**: Los modelos Pydantic se mapearían a modelos ORM (SQLAlchemy, etc.) para persistencia.  
**Posible integración MCP**: Podría añadirse un modelo específico para datos de MCP.

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
- Usa `notion_service`.

**Posible integración BBDD**: Estos endpoints podrían llamar servicios que consulten la base de datos además de APIs externas.  
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

**Posible integración BBDD**: Lógica de estos servicios podría registrar resultados en la base de datos o obtener datos desde ella.  
**Posible integración MCP**: Añadir servicio que llame a MCP y procese resultados.

---

## 7. Comentarios sugeridos en el código
En puntos clave (conexiones externas, estructuras de datos, configuración), se deberían añadir comentarios para indicar lugares donde se integrará BBDD o MCP.

---

## 8. Próximos pasos
1. Añadir comentarios en código para marcar integraciones futuras.
2. Documentar dependencias e interacciones entre servicios.
3. Diseñar esquema de BBDD y planificar migraciones.
4. Planificar endpoints MCP y definir modelos asociados.
5. Actualizar esta documentación conforme se implementen cambios.