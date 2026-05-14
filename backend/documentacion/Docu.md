# Documentación exhaustiva de Priorum

Priorum es una plataforma unificada para la gestión inteligente de tareas, eventos y agentes IA.
Incluye un **frontend** moderno (React + Vite) y un **backend** modular y extensible construido sobre FastAPI y Python 3.12, con integración de múltiples APIs externas y soporte para **Model Context Protocol (MCP)**.

---

## 1. Resumen funcional

El sistema permite:
- **Gestión de tareas**: sincronización bidireccional con Notion.
- **Gestión de calendario**: integración con Microsoft Outlook/Teams vía Microsoft Graph.
- **Agente IA**: asistencia, priorización automática y razonamiento sobre la agenda diaria.
- **Integración Jira**: creación y sincronización de issues con la API REST de Jira.
- **Persistencia**: almacenamiento en MongoDB, con capacidad demo offline.
- **Operaciones de agentes MCP**: ampliación de funcionalidades mediante herramientas diseñadas en MCP.

---

## 2. Backend

- **main.py**: inicializa FastAPI, middleware, routers y endpoints.
- **app/config.py**: parámetros de configuración con Pydantic Settings (.env).
- **app/models**: modelos Pydantic y ORM de tareas, eventos y agentes.
- **app/routers**: rutas REST para tareas (`/tasks`), calendario (`/calendar`), agente IA (`/agent`) y Jira (`/jira`).
- **app/services**: lógica de negocio e integración con APIs externas (Notion, Outlook, OpenAI, Jira).
- **logging_config.py**: configuración centralizada de logs.
- **mcp/**: definición de servidores MCP, por ejemplo `jira_task_server`.
- **docs/db_schema.md**: esquema relacional/documental de la base de datos.
- **agents/**: módulos de agentes IA especializados (chat_agent, calendar_agent).

---

## 3. Frontend

- **Priorum_mockup.jsx** y componentes React: interfaz con vistas para prioridades, tareas y calendario.
- Conexiones con el backend mediante servicios (`/services`) y hooks (`useTasks`, `useCalendar`, `useAgent`).
- Diseño estilizado con constantes de colores y patrones de disposición.
- Gestión visual de estados (modales, filtros, navegación lateral, barra superior).

---

## 4. Integraciones externas

- **Notion API**:
  - CRUD de tareas.
  - Detecta propiedades disponibles automáticamente.
- **Microsoft Graph API**:
  - CRUD de eventos de calendario.
- **OpenAI (Azure OpenAI)**:
  - Procesamiento de lenguaje natural para agentes IA.
- **Jira REST API**:
  - CRUD de issues.
- **MongoDB**:
  - Conexión asíncrona mediante `motor`.
- **MCP**:
  - Posibilidad de ampliar agentes mediante herramientas externas.

---

## 5. Agentes IA

### Chat Agent
- Capaz de interpretar lenguaje natural y ejecutar acciones:
  - Consultar/crear/actualizar/comentar tareas de Notion.
  - Consultar/crear eventos de Outlook.
  - Crear issues de Jira.
- Usa instrucciones claras en español y tono directo.
- Responde basándose en contexto de la UI (vista activa, resumen del día).

### Calendar Agent
- Analiza eventos de Outlook para calcular disponibilidad.
- Identifica slots libres, trabajo profundo y carga cognitiva.
- Devuelve siempre JSON estructurado con eventos, slots y resumen.

---

## 6. Demo completa

### Flujo típico
1. **Carga de prioridades**: agente IA analiza tareas/eventos.
2. **Vista de tareas**: CRUD con Notion, filtrando por prioridad/estado.
3. **Vista de calendario**: CRUD con Outlook y visualización por horas.
4. **Interacción con agente**: en tiempo real (MCP + OpenAI).

> El sistema puede operarse en modo demo sin credenciales, usando datos mock.

---

## 7. Próximos pasos sugeridos
- Expandir instrucciones de `jira_task_server`.
- Documentar todas las herramientas MCP disponibles.
- Mejorar esquemas visuales con diagramas de flujo y mapas de integraciones.
- Mantener esta documentación actualizada.

---

## 8. Anexo
Se incluye el archivo `codigo_completo.txt` con un volcado íntegro del código para referencia técnica.