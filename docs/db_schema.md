# Esquema de datos – Priorum (MongoDB)

Este documento describe qué guardamos en MongoDB, por qué y cómo se gestionan índices y retención (TTL). MongoDB actúa como:
- Persistencia operativa (tareas/eventos enriquecidos en la app).
- Caché local de datos externos (Notion, Microsoft Graph).
- Registro de interacciones del agente (logs).

## Colecciones

1) tasks (operacional)
- Uso: almacenar tareas operativas de la app (p. ej., duplicadas/enriquecidas desde Notion o creadas en la app).
- Índices:
  - external_id (único, sparse) — si reflejan una página de Notion
  - due_date (ordenación)
- Documento (ejemplo):
  {
    "id": "ObjectId",
    "external_id": "notion_page_id",
    "title": "Preparar demo",
    "description": "Revisar checklist",
    "status": "pending",
    "priority": "high",
    "due_date": "2026-05-13T16:00:00Z",
    "tags": ["demo", "ventas"],
    "source": "notion",
    "created_at": "2026-05-13T10:00:00Z",
    "updated_at": "2026-05-13T10:10:00Z"
  }

2) events (operacional)
- Uso: almacenar eventos operativos (opcionalmente enriquecidos) de Outlook/Teams.
- Índices:
  - external_id (único, sparse)
  - start (ordenación)
- Documento (ejemplo):
  {
    "id": "ObjectId",
    "external_id": "graph_event_id",
    "title": "Daily standup",
    "description": "Sprint D14",
    "start": "2026-05-13T08:30:00Z",
    "end": "2026-05-13T08:45:00Z",
    "location": "Teams",
    "attendees": [{"email": "a@b.com", "name": "Alice"}],
    "source": "outlook",
    "created_at": "2026-05-13T07:00:00Z",
    "updated_at": "2026-05-13T07:00:00Z"
  }

3) tasks_cache (caché Notion)
- Uso: cachear tareas de Notion para evitar llamadas redundantes y permitir modo offline.
- Índices:
  - external_id (único)
  - cached_at
  - TTL opcional sobre cached_at si MONGO_CACHE_TTL_SECONDS > 0
- Documento (ejemplo):
  {
    "id": "ObjectId",
    "external_id": "notion_page_id",
    "title": "Preparar demo",
    "description": "Revisar checklist",
    "status": "in_progress",
    "priority": "medium",
    "due_date": "2026-05-13T16:00:00Z",
    "tags": ["demo"],
    "source": "notion",
    "raw": { ...documento completo de Notion... },
    "cached_at": "2026-05-13T09:59:10Z"
  }

4) events_cache (caché Outlook)
- Uso: cachear eventos de Microsoft Graph.
- Índices:
  - external_id (único)
  - cached_at
  - TTL opcional sobre cached_at si MONGO_CACHE_TTL_SECONDS > 0
- Documento (ejemplo):
  {
    "id": "ObjectId",
    "external_id": "graph_event_id",
    "title": "Revisión semanal",
    "description": "Equipo producto",
    "start": "2026-05-14T10:00:00Z",
    "end": "2026-05-14T11:00:00Z",
    "location": "Sala 2",
    "attendees": [{"email": "a@b.com", "name": "Alice"}],
    "source": "outlook",
    "raw": { ...evento original Graph... },
    "cached_at": "2026-05-13T09:50:00Z"
  }

5) agent_logs (logs del agente IA)
- Uso: trazabilidad de interacciones, herramientas usadas, latencia y errores.
- Índices:
  - (session_id, created_at)
  - created_at
  - TTL opcional sobre created_at si MONGO_AGENT_LOGS_TTL_SECONDS > 0
- Documento (ejemplo):
  {
    "id": "ObjectId",
    "session_id": "session-123",
    "role": "assistant",
    "content": "He priorizado tus tareas...",
    "tools": [{"name": "retriever", "args": {"k": 5}, "duration_ms": 42}],
    "metadata": {"priorities": [{"task_id": "...", "score": 0.87}]},
    "latency_ms": 230,
    "error": null,
    "created_at": "2026-05-13T10:05:00Z"
  }

## Retención (TTL)
- MONGO_CACHE_TTL_SECONDS controla la caducidad de tasks_cache y events_cache.
- MONGO_AGENT_LOGS_TTL_SECONDS controla la caducidad de agent_logs.
- Si el valor es 0 o no está definido, no se crea índice TTL.

## Flujo de sincronización recomendado
1. Notion -> tasks_cache (upsert por external_id).
2. Outlook -> events_cache (upsert por external_id).
3. Backend/Agente:
   - Lee cache primero si está fresca; si está caducada, refresca desde API externa y actualiza caché.
   - Puede crear/enriquecer tasks/events operacionales en las colecciones principales si hay edición desde la app.
4. Agente IA:
   - Registra interacciones en agent_logs para trazabilidad.
   - Puede indexar contenidos relevantes en el vector store (Qdrant) para RAG.

## Buenas prácticas
- Mantener external_id como referencia a la fuente externa.
- Usar raw para conservar el documento original completo cuando aporte valor.
- Establecer TTL de caché razonable (p. ej., 6 horas) para balancear frescura y llamadas API.
- Logs con TTL de 15-30 días suelen ser suficientes en entornos de demo/hackathon.
