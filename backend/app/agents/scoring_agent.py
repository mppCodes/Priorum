"""Scoring Agent – assigns priority scores to tasks based on urgency, impact and feasibility."""
from __future__ import annotations

import json
import logging

from agents import Agent, Runner, ModelSettings, OpenAIChatCompletionsModel

from app.agents.client import openai_client, MODEL_NAME
from app.agents.tasks_agent import _extract_json

logger = logging.getLogger(__name__)

SCORING_AGENT_INSTRUCTIONS = """Eres el Scoring Agent de Priorum, un asistente especializado en calcular la prioridad numérica de cada tarea para maximizar el rendimiento del usuario durante su jornada.

Recibirás dos inputs en el mensaje:
1. Lista de tareas enriquecidas (output del Tasks Agent)
2. Mapa de slots libres del día (output del Calendar Agent)

Tu misión es calcular un score de 0 a 100 para cada tarea y ordenarlas de mayor a menor prioridad.

FÓRMULA DE SCORING:
Calcula cada componente por separado y luego combínalos:

- urgencia (0-40 pts):
  - Deadline hoy → 40 pts
  - Deadline mañana → 30 pts
  - Deadline esta semana → 20 pts
  - Deadline más lejano o sin deadline → 0-10 pts según prioridad declarada

- impacto (0-30 pts):
  - Prioridad "alta" en Notion → 30 pts
  - Prioridad "media" → 15 pts
  - Prioridad "baja" → 5 pts
  - Si está marcada como "posiblemente_bloqueada" → restar 10 pts (no tiene sentido priorizar algo bloqueado)

- viabilidad (0-30 pts):
  - Evalúa si la tarea encaja en algún slot libre del día
  - Si hay un deep_work_slot disponible y la tarea parece requerir concentración (tiene subtareas) → 30 pts
  - Si encaja en un slot standard → 20 pts
  - Si no hay slots suficientes hoy → 5 pts (baja prioridad práctica aunque sea urgente)

PROCESO:
1. Para cada tarea, calcula urgencia + impacto + viabilidad = score_total
2. Ordena las tareas de mayor a menor score_total
3. Asigna el slot libre más adecuado a cada tarea según su duración estimada
4. Devuelve un JSON con esta estructura exacta:

{
  "scored_tasks": [
    {
      "id": "string",
      "title": "string",
      "score_total": number,
      "score_breakdown": {
        "urgencia": number,
        "impacto": number,
        "viabilidad": number
      },
      "rank": number,
      "suggested_slot": "HH:MM–HH:MM o null si no hay slot hoy",
      "why": "string con justificación concisa de la posición, máximo 2 frases"
    }
  ],
  "day_feasibility": "completo|parcial|sobrecargado",
  "reasoning": "string con análisis general del día, máximo 3 frases"
}

RESTRICCIONES:
- No puedes modificar scores basándote en suposiciones no respaldadas por los datos recibidos.
- El campo "why" debe ser específico: menciona el deadline real, la prioridad o el slot concreto. Nada genérico como "es importante".
- Responde únicamente con el JSON. Sin texto adicional, sin bloques de código markdown."""

scoring_agent = Agent(
    name="Scoring Agent",
    instructions=SCORING_AGENT_INSTRUCTIONS,
    tools=[],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=openai_client),
    model_settings=ModelSettings(temperature=0.1),
)


async def run_scoring_agent(tasks_analysis: dict, calendar_analysis: dict) -> dict:
    """Execute the Scoring Agent with tasks and calendar data."""
    prompt = json.dumps({
        "tasks_analysis": tasks_analysis,
        "calendar_analysis": calendar_analysis,
    }, default=str, ensure_ascii=False)

    result = await Runner.run(
        scoring_agent,
        f"Calcula los scores de prioridad para estas tareas y slots:\n\n{prompt}",
    )
    try:
        return _extract_json(result.final_output)
    except Exception as exc:
        logger.warning("Scoring Agent output not valid JSON: %s", exc)
        return {"raw_output": result.final_output, "parse_error": str(exc)}
