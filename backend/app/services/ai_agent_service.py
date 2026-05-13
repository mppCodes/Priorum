"""
Servicio del agente IA.
Usa OpenAI (GPT-4o) para priorizar tareas, sugerir horarios y responder preguntas.
"""
from typing import Any
from datetime import datetime
import json

from app.config import get_settings
from app.models.agent import (
    ChatMessage, ChatResponse,
    PrioritiesRequest, PrioritiesResponse, PriorityItem,
    ScheduleRequest, ScheduleResponse,
)

settings = get_settings()

# Historial de conversación en memoria (por sesión de servidor)
_chat_history: list[ChatMessage] = []

SYSTEM_PROMPT = """Eres Priorum, un asistente de productividad personal inteligente.
Tu objetivo es ayudar al usuario a gestionar su día de trabajo de forma eficiente.

Tienes acceso al contexto del usuario:
- Sus tareas pendientes (de Notion) con prioridad, deadline y proyecto
- Sus eventos del calendario (de Outlook/Teams) con hora y duración
- Los slots libres del día

Cuando respondas:
- Sé conciso y directo (máximo 3-4 frases)
- Usa el contexto proporcionado para dar respuestas personalizadas
- Si no tienes suficiente contexto, indícalo brevemente
- Responde siempre en español
"""

PRIORITIES_PROMPT = """Analiza las tareas y eventos del usuario y devuelve una lista priorizada.

Contexto:
{context}

Devuelve ÚNICAMENTE un JSON válido con este formato exacto:
{{
  "priorities": [
    {{
      "rank": 1,
      "title": "título de la tarea",
      "why": "razón breve de por qué es prioritaria (1-2 frases)",
      "time": "tiempo estimado (ej: 45 min)",
      "tag": "alta|media|baja"
    }}
  ],
  "reasoning": "explicación general de la distribución del día (2-3 frases)"
}}

Ordena por urgencia + impacto. Máximo 5 tareas.
"""

SCHEDULE_PROMPT = """Sugiere cómo distribuir las tareas en los slots libres del día.

Contexto:
{context}

Devuelve ÚNICAMENTE un JSON válido con este formato:
{{
  "schedule": [
    {{
      "time": "HH:MM",
      "task": "título de la tarea o actividad",
      "duration": 45,
      "type": "task|break|event"
    }}
  ],
  "reasoning": "explicación de la distribución propuesta (2-3 frases)"
}}
"""


def _get_openai_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.openai_api_key)


def _build_context(data: dict[str, Any]) -> str:
    """Construye un resumen de contexto legible para el LLM."""
    lines = []

    tasks = data.get("tasks", [])
    if tasks:
        lines.append(f"TAREAS PENDIENTES ({len(tasks)}):")
        for t in tasks[:10]:  # máximo 10
            lines.append(
                f"  - [{t.get('priority', '?').upper()}] {t.get('title', '')} "
                f"(Proyecto: {t.get('project', '-')}, Deadline: {t.get('deadline', '-')})"
            )

    events = data.get("events", [])
    if events:
        lines.append(f"\nEVENTOS HOY ({len(events)}):")
        for e in events[:10]:
            lines.append(
                f"  - {e.get('time', '?')} {e.get('title', '')} "
                f"({e.get('duration', 30)} min)"
            )

    free_slots = data.get("free_slots", [])
    if free_slots:
        lines.append("\nSLOTS LIBRES:")
        for slot in free_slots:
            lines.append(f"  - {slot.get('from', '?')} – {slot.get('to', '?')}")

    date_str = data.get("date", datetime.now().isoformat())
    lines.insert(0, f"FECHA: {date_str[:10]}\n")

    return "\n".join(lines)


async def chat(message: str, context: dict[str, Any]) -> ChatResponse:
    """Responde a un mensaje del usuario usando el historial y el contexto."""
    if not settings.openai_api_key:
        return _mock_chat(message)

    client = _get_openai_client()
    context_str = _build_context(context)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Contexto actual del usuario:\n{context_str}"},
    ]

    # Añade historial reciente (últimos 10 mensajes)
    for msg in _chat_history[-10:]:
        messages.append({
            "role": "user" if msg.role == "user" else "assistant",
            "content": msg.content,
        })

    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=settings.openai_temperature,
        max_tokens=512,
    )

    reply = response.choices[0].message.content or ""

    # Guarda en historial
    now = datetime.utcnow()
    _chat_history.append(ChatMessage(role="user",  content=message, timestamp=now))
    _chat_history.append(ChatMessage(role="agent", content=reply,   timestamp=now))

    return ChatResponse(message=reply, timestamp=now)


async def get_priorities(req: PrioritiesRequest) -> PrioritiesResponse:
    """Genera la lista de prioridades del día usando el LLM."""
    if not settings.openai_api_key:
        return _mock_priorities(req)

    client = _get_openai_client()
    context_str = _build_context({
        "tasks":  [t for t in req.tasks],
        "events": [e for e in req.events],
        "date":   req.date,
    })

    prompt = PRIORITIES_PROMPT.format(context=context_str)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "Eres un asistente de productividad. Responde SOLO con JSON válido."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    return PrioritiesResponse(
        priorities=[PriorityItem(**p) for p in data.get("priorities", [])],
        reasoning=data.get("reasoning", ""),
    )


async def get_schedule(req: ScheduleRequest) -> ScheduleResponse:
    """Genera una sugerencia de horario para el día."""
    if not settings.openai_api_key:
        return ScheduleResponse(reasoning="Configura OPENAI_API_KEY para obtener sugerencias de horario.")

    client = _get_openai_client()
    context_str = _build_context({
        "tasks":      req.tasks,
        "events":     req.events,
        "free_slots": req.free_slots,
        "date":       req.date,
    })

    prompt = SCHEDULE_PROMPT.format(context=context_str)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "Eres un asistente de productividad. Responde SOLO con JSON válido."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    return ScheduleResponse(
        schedule=data.get("schedule", []),
        reasoning=data.get("reasoning", ""),
    )


def get_history() -> list[ChatMessage]:
    return list(_chat_history)


def clear_history() -> None:
    _chat_history.clear()


# ── Mocks para desarrollo sin API key ──────────────────────────────────────────

def _mock_chat(message: str) -> ChatResponse:
    reply = (
        "Soy Priorum, tu asistente de productividad. "
        "Para activar el agente IA, configura OPENAI_API_KEY en el archivo .env. "
        f'Recibí tu mensaje: "{message}"'
    )
    now = datetime.now(datetime.timezone.utc)
    _chat_history.append(ChatMessage(role="user",  content=message, timestamp=now))
    _chat_history.append(ChatMessage(role="agent", content=reply,   timestamp=now))
    return ChatResponse(message=reply, timestamp=now)


def _mock_priorities(req: PrioritiesRequest) -> PrioritiesResponse:
    tasks = req.tasks[:3]
    priorities = [
        PriorityItem(
            rank=i + 1,
            title=t.get("title", f"Tarea {i+1}"),
            why="Prioridad calculada en modo demo (sin API key).",
            time="30 min",
            tag=t.get("priority", "media"),
        )
        for i, t in enumerate(tasks)
    ]
    return PrioritiesResponse(
        priorities=priorities,
        reasoning="Modo demo activo. Configura OPENAI_API_KEY para obtener prioridades reales.",
    )