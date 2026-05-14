"""Calendar Agent – analyzes Outlook calendar and computes availability."""
from __future__ import annotations

import json
import logging
from datetime import date

from agents import Agent, Runner, ModelSettings, OpenAIChatCompletionsModel

from app.agents.client import openai_client, MODEL_NAME
from app.agents.tasks_agent import _extract_json
from app.agents.tools.outlook_tools import get_events, create_event, update_event, delete_event

logger = logging.getLogger(__name__)

CALENDAR_AGENT_INSTRUCTIONS = """Eres el Calendar Agent de Priorum, un asistente especializado en analizar el calendario de Outlook del usuario y calcular su disponibilidad real para trabajar.

Tu misión es leer los eventos del día, entender cómo afectan al tiempo disponible y devolver un mapa temporal preciso para que el orquestador pueda planificar tareas de forma realista.

PROCESO:
1. Llama a get_events para obtener todos los eventos del día actual.
2. Analiza los eventos y calcula:
   - Slots libres entre las 08:00 y las 18:00, descontando los eventos
   - Descarta slots de menos de 20 minutos (no son útiles para trabajo profundo)
   - Identifica bloques de más de 90 minutos consecutivos → "deep work slots"
   - Detecta rachas de reuniones seguidas (3 o más) → indica "carga cognitiva alta post-reuniones"
3. Devuelve un JSON con esta estructura exacta:

{
  "events": [
    {
      "id": "string",
      "title": "string",
      "time": "HH:MM",
      "duration_minutes": number,
      "type": "reunion|personal|bloqueo",
      "attendees_count": number
    }
  ],
  "free_slots": [
    {
      "from": "HH:MM",
      "to": "HH:MM",
      "duration_minutes": number,
      "quality": "deep_work|standard|short"
    }
  ],
  "summary": {
    "total_events": number,
    "total_busy_minutes": number,
    "total_free_minutes": number,
    "deep_work_slots": number,
    "cognitive_load": "baja|media|alta",
    "notes": "string con una observación relevante del día, máximo 1 frase"
  }
}

CUANDO CREAR EVENTOS:
- Solo crea o modifica eventos si el orquestador o el usuario lo solicitan explícitamente.
- Al crear un evento, confirma siempre el título, fecha, hora y duración antes de llamar a create_event.

RESTRICCIONES:
- El horario de trabajo es 08:00–18:00. Ignora eventos fuera de ese rango para el cálculo de slots.
- Si hay dos eventos solapados en Outlook, trátalos como un único bloque ocupado.
- Responde únicamente con el JSON. Sin texto adicional, sin bloques de código markdown."""

calendar_agent = Agent(
    name="Calendar Agent",
    instructions=CALENDAR_AGENT_INSTRUCTIONS,
    tools=[get_events, create_event, update_event, delete_event],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=openai_client),
    model_settings=ModelSettings(temperature=0.1),
)


async def run_calendar_agent(target_date: str | None = None) -> dict:
    """Execute the Calendar Agent and return parsed JSON output."""
    d = target_date or date.today().isoformat()
    result = await Runner.run(
        calendar_agent,
        f"Analiza mi calendario del día {d} y calcula mi disponibilidad.",
    )
    try:
        return _extract_json(result.final_output)
    except Exception as exc:
        logger.warning("Calendar Agent output not valid JSON: %s", exc)
        return {"raw_output": result.final_output, "parse_error": str(exc)}
