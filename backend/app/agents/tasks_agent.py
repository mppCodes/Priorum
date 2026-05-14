"""Tasks Agent – analyzes and enriches Notion tasks."""
from __future__ import annotations

import json
import logging

from agents import Agent, Runner, ModelSettings, OpenAIChatCompletionsModel

from app.agents.client import openai_client, MODEL_NAME
from app.agents.tools.notion_tools import add_comment, get_tasks, update_task

logger = logging.getLogger(__name__)

TASKS_AGENT_INSTRUCTIONS = """Eres el Tasks Agent de Priorum, un asistente especializado en analizar y enriquecer tareas de Notion.

Tu misión es leer todas las tareas pendientes del usuario y devolver un análisis estructurado listo para que el orquestador lo use. No te limites a listar las tareas: razona sobre ellas.

PROCESO:
1. Llama a get_tasks para obtener todas las tareas pendientes de hoy y esta semana.
2. Para cada tarea, determina:
   - Si lleva más de 3 días sin actualizarse → márcarla como "posiblemente bloqueada"
   - Si tiene subtareas sin completar que impiden el avance → indícalo
   - Si su deadline es hoy o mañana → marcala como "urgente"
   - Si pertenece a un proyecto con varias tareas activas → agrúpalas
3. Devuelve un JSON con esta estructura exacta:

{
  "tasks": [
    {
      "id": "string",
      "title": "string",
      "project": "string",
      "priority": "alta|media|baja",
      "deadline": "YYYY-MM-DD",
      "tags": ["string"],
      "subtasks_pending": number,
      "comments_count": number,
      "status_analysis": "activa|posiblemente_bloqueada|urgente",
      "notes": "string con observaciones relevantes, máximo 1 frase"
    }
  ],
  "summary": {
    "total_pending": number,
    "urgent": number,
    "possibly_blocked": number,
    "by_project": {"project_name": number}
  }
}

RESTRICCIONES:
- No modifiques ni actualices ninguna tarea a menos que el orquestador te lo indique explícitamente.
- No inventes información que no esté en Notion.
- Si una tarea no tiene deadline, ponlo como null.
- El campo "notes" debe ser concreto y útil, no genérico.
- Responde únicamente con el JSON. Sin texto adicional, sin bloques de código markdown."""

tasks_agent = Agent(
    name="Tasks Agent",
    instructions=TASKS_AGENT_INSTRUCTIONS,
    tools=[get_tasks, update_task, add_comment],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=openai_client),
    model_settings=ModelSettings(temperature=0.1),
)


def _extract_json(text: str) -> dict:
    """Extract the first valid JSON object from a string that may contain extra text."""
    if not text:
        return {}
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()
    # Use raw_decode to parse only the first JSON object, ignoring trailing content
    try:
        obj, _ = json.JSONDecoder().raw_decode(text)
        return obj if isinstance(obj, dict) else {}
    except (json.JSONDecodeError, ValueError):
        # Last resort: find the outermost { } block
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"raw_output": text}


async def run_tasks_agent() -> dict:
    """Execute the Tasks Agent and return parsed JSON output."""
    result = await Runner.run(tasks_agent, "Analiza todas mis tareas pendientes de hoy y esta semana.")
    try:
        return _extract_json(result.final_output)
    except Exception as exc:
        logger.warning("Tasks Agent output not valid JSON: %s", exc)
        return {"raw_output": result.final_output, "parse_error": str(exc)}
