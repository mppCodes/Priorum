"""Orchestrator – runs all specialized agents and produces the final prioritized plan."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, date

from agents import Agent, Runner, ModelSettings, OpenAIChatCompletionsModel

from app.agents.client import openai_client, MODEL_NAME
from app.agents.tasks_agent import run_tasks_agent, _extract_json
from app.agents.calendar_agent import run_calendar_agent
from app.agents.scoring_agent import run_scoring_agent
from app.agents.context_agent import run_context_agent

logger = logging.getLogger(__name__)

ORCHESTRATOR_INSTRUCTIONS = """Eres el orquestador principal de Priorum, el sistema de productividad personal del usuario.

Tu función es tomar los outputs de cuatro agentes especializados y generar la priorización definitiva del día, junto con el horario sugerido y el razonamiento completo.

INPUTS QUE RECIBIRÁS (todos en el mismo mensaje, en formato JSON):
- tasks_analysis: output del Tasks Agent
- calendar_analysis: output del Calendar Agent
- scoring_analysis: output del Scoring Agent
- context_analysis: output del Context Agent

PROCESO:
1. Lee los cuatro outputs y detecta contradicciones o tensiones entre ellos
   (ejemplo: una tarea con score alto pero sin slot disponible hoy)
2. Ajusta el ranking del Scoring Agent si el Context Agent detectó señales que lo justifican
   (ejemplo: carga cognitiva alta → bajar tareas que requieren concentración)
3. Genera la lista final de máximo 5 tareas priorizadas para hoy
4. Asigna cada tarea al slot más adecuado del calendario
5. Redacta el razonamiento general del día en lenguaje natural

DEVUELVE un JSON con esta estructura exacta:

{
  "date": "YYYY-MM-DD",
  "priorities": [
    {
      "rank": number,
      "task_id": "string",
      "title": "string",
      "priority_tag": "alta|media|baja",
      "suggested_slot": "HH:MM–HH:MM",
      "estimated_minutes": number,
      "why": "string con justificación final, máximo 2 frases. Debe ser específica: menciona el deadline, el slot o la señal contextual que motivó esta posición."
    }
  ],
  "schedule": [
    {
      "time": "HH:MM",
      "title": "string",
      "duration_minutes": number,
      "type": "task|event|break"
    }
  ],
  "reasoning": "string con análisis general del día en lenguaje natural, máximo 4 frases. Menciona la carga de reuniones, el tiempo libre real y cualquier alerta relevante.",
  "alerts": [
    {
      "type": "deadline|sin_slots|carga_alta|bloqueada",
      "message": "string con la alerta concreta, máximo 1 frase"
    }
  ]
}

RESTRICCIONES:
- No incluyas más de 5 tareas en priorities. Si hay más, descarta las de menor score.
- El schedule debe ser coherente con los eventos reales del Calendar Agent: no solapas tareas con reuniones.
- Si una tarea urgente no tiene slot hoy, inclúyela en alerts con tipo "sin_slots", no en priorities.
- El campo "why" de cada tarea debe ser diferente entre sí. No repitas la misma justificación.
- Responde únicamente con el JSON. Sin texto adicional, sin bloques de código markdown."""

orchestrator_agent = Agent(
    name="Orchestrator",
    instructions=ORCHESTRATOR_INSTRUCTIONS,
    tools=[],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=openai_client),
    model_settings=ModelSettings(temperature=0.2),
)


def _tasks_from_list(tasks: list[dict]) -> dict:
    """Builds a tasks_analysis dict from a plain list of task dicts (frontend format)."""
    today_str = date.today().isoformat()
    pending = [t for t in tasks if not t.get("done", False)]
    return {
        "tasks": [
            {
                "id": t.get("id", str(i)),
                "title": t.get("title", ""),
                "project": t.get("project", ""),
                "priority": t.get("priority", "media"),
                "deadline": t.get("deadline", ""),
                "tags": t.get("tags", []),
                "subtasks_pending": len(t.get("subtasks", [])),
                "comments_count": len(t.get("comments", [])),
                "status_analysis": "urgente" if t.get("deadline") == today_str else "activa",
                "notes": "",
            }
            for i, t in enumerate(pending)
        ],
        "summary": {
            "total_pending": len(pending),
            "urgent": sum(1 for t in pending if t.get("deadline") == today_str),
            "possibly_blocked": 0,
            "by_project": {},
        },
    }


def _calendar_from_list(events: list[dict]) -> dict:
    """Builds a calendar_analysis dict from a plain list of event dicts (frontend format)."""
    parsed = []
    for i, e in enumerate(events):
        duration = 30
        start_str = e.get("time", "09:00")
        try:
            start_raw = e.get("start")
            end_raw = e.get("end")
            if start_raw and end_raw:
                from datetime import datetime as _dt
                s = _dt.fromisoformat(str(start_raw).replace("Z", "+00:00"))
                en = _dt.fromisoformat(str(end_raw).replace("Z", "+00:00"))
                duration = max(1, int((en - s).total_seconds() / 60))
                start_str = s.strftime("%H:%M")
        except Exception:
            pass
        parsed.append({
            "id": e.get("id", str(i)),
            "title": e.get("title", ""),
            "time": start_str,
            "duration_minutes": duration,
            "type": e.get("type", "reunion"),
            "attendees_count": len(e.get("attendees") or []),
        })
    total_busy = sum(ev["duration_minutes"] for ev in parsed)
    return {
        "events": parsed,
        "free_slots": [],
        "summary": {
            "total_events": len(parsed),
            "total_busy_minutes": total_busy,
            "total_free_minutes": max(0, 480 - total_busy),
            "deep_work_slots": 0,
            "cognitive_load": "alta" if len(parsed) >= 3 else "media" if len(parsed) >= 1 else "baja",
            "notes": f"{len(parsed)} eventos en el calendario hoy.",
        },
    }


async def run_orchestrator(
    target_date: str | None = None,
    fallback_tasks: list | None = None,
    fallback_events: list | None = None,
) -> dict:
    """Run the full orchestration pipeline: Tasks + Calendar in parallel,
    then Scoring + Context, then final orchestration.

    If the agents return empty results, fallback_tasks / fallback_events
    (provided by the frontend from its own Notion/Outlook cache) are used instead.
    """
    today = target_date or date.today().isoformat()
    now = datetime.now()

    # Phase 1: Tasks and Calendar in parallel
    tasks_result, calendar_result = await asyncio.gather(
        run_tasks_agent(),
        run_calendar_agent(target_date=today),
    )

    # Fallback: if agents returned no data, use what the frontend already loaded
    if not tasks_result.get("tasks") and fallback_tasks:
        logger.info(
            "Tasks Agent returned no tasks; using %d fallback tasks from request",
            len(fallback_tasks),
        )
        tasks_result = _tasks_from_list(fallback_tasks)

    if not calendar_result.get("events") and fallback_events:
        logger.info(
            "Calendar Agent returned no events; using %d fallback events from request",
            len(fallback_events),
        )
        calendar_result = _calendar_from_list(fallback_events)

    # Phase 2: Scoring and Context in parallel (they depend on phase 1)
    scoring_result, context_result = await asyncio.gather(
        run_scoring_agent(tasks_analysis=tasks_result, calendar_analysis=calendar_result),
        run_context_agent(tasks_analysis=tasks_result, calendar_analysis=calendar_result, now=now),
    )

    # Phase 3: Final orchestration
    combined = json.dumps({
        "tasks_analysis": tasks_result,
        "calendar_analysis": calendar_result,
        "scoring_analysis": scoring_result,
        "context_analysis": context_result,
    }, default=str, ensure_ascii=False)

    result = await Runner.run(
        orchestrator_agent,
        f"Genera la priorización definitiva del día {today} con estos datos:\n\n{combined}",
    )

    try:
        return _extract_json(result.final_output)
    except Exception as exc:
        logger.warning("Orchestrator output not valid JSON: %s", exc)
        return {"raw_output": result.final_output, "parse_error": str(exc)}
