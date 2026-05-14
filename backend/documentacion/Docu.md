# Documentación de Priorum

Priorum es un sistema de gestión inteligente de tareas, eventos y agentes IA, diseñado para integrarse con múltiples servicios externos y proporcionar un flujo de trabajo automatizado y centralizado. El proyecto consta de un **backend** desarrollado con **FastAPI** y un **frontend** web moderno, acompañado de documentación técnica y esquemas que detallan su funcionamiento.

---

## 1. Descripción general

El backend está construido en **Python** usando **FastAPI** y una arquitectura modular, permitiendo añadir fácilmente nuevas integraciones como bases de datos, APIs externas o servidores MCP (Model Context Protocol). El frontend se ejecuta sobre tecnologías web estándar y frameworks modernos para ofrecer una interfaz gráfica intuitiva.

### Principales funcionalidades:
- Gestión de tareas con sincronización Notion y base de datos.
- Gestión de eventos de calendario con integración Microsoft Outlook.
- Servicio de agente IA para interacción, priorización y asistencia.
- Integración con Jira para creación y sincronización de tareas.
- Documentación y esquemas para integración de BBDD y MCP.

---

## 2. Estructura del backend

- `main.py` → Punto de entrada, inicializa la app, middleware y routers.
- `app/config.py` → Configuración mediante `.env` para credenciales y parámetros.
- `app/models` → Modelos de datos Pydantic y adaptaciones ORM para persistencia.
- `app/routers` → Endpoints para tareas, calendario, agente IA y Jira.
- `app/services` → Lógica de negocio e integración con APIs externas (Notion, Outlook, OpenAI, Jira).
- `logging_config.py` → Configuración centralizada de logs.
- `docs/db_schema.md` → Esquema de base de datos.
- `mcp/jira_task_server` → Integración MCP para tareas Jira.

---

## 3. Integraciones externas

- **Notion**: CRUD de tareas con sincronización bidireccional.
- **Microsoft Graph / Outlook**: CRUD y sincronización de eventos de calendario.
- **OpenAI**: Procesamiento de lenguaje natural para agente IA.
- **Jira REST API**: CRUD y sincronización de tareas Jira.
- **Base de datos**: Persistencia de tareas y eventos.
- **MCP**: Creación de tareas Jira desde un servidor MCP.

---

## 4. Funcionamiento del agente IA

El agente IA de Priorum permite:
- Chat interactivo para consultas.
- Priorización automática de tareas.
- Asistente para organización de calendario.
- Historial de interacción.

Estas capacidades pueden ampliarse con nuevas herramientas MCP y servicios externos.

---

## 5. Documentación y esquemas

Además de la presente documentación, el proyecto incluye:
- **`docs/db_schema.md`**: Definición de tablas, campos y relaciones.
- **`docs/agent_flow.html`**: Flujo del agente IA visual.
- Comentarios sugeridos en código sobre puntos de interacción MCP y conexión BBDD.

---

## 6. Próximos pasos sugeridos

1. Detallar el funcionamiento completo del servidor MCP `jira_task_server`.
2. Ampliar descripción de las integraciones de base de datos.
3. Definir endpoints futuros para nuevas herramientas MCP.
4. Mantener esta documentación actualizada con cada cambio significativo.

---

## 7. Resumen

Priorum integra múltiples servicios y agentes inteligentes en una plataforma unificada para gestión de tareas y eventos. Su arquitectura modular facilita futuras ampliaciones y su documentación proporciona la guía necesaria para comprender y desarrollar sobre la base existente.