"""Chat Agent – handles natural language conversation with the user."""
from __future__ import annotations

import json
import logging
from typing import Any

from agents import Agent, Runner, ModelSettings, OpenAIChatCompletionsModel

from app.agents.client import openai_client, MODEL_NAME
from app.agents.tools.notion_tools import get_tasks, create_task, update_task, add_comment, delete_task
from app.agents.tools.outlook_tools import get_events, create_event
from app.agents.tools.mcp_tools import MCP_TOOLS

logger = logging.getLogger(__name__)

CHAT_AGENT_INSTRUCTIONS = """Eres el asistente personal del usuario en Priorum, una app de productividad conectada a Notion, Outlook y Jira.

Tu nombre es Priorum. Hablas en español, en tono directo y sin florituras. Eres útil y concreto: cuando el usuario te pide algo que puedes hacer, lo haces. No preguntas si quieres que lo hagas, simplemente lo haces y confirmas.

CAPACIDADES:
- Puedes consultar, crear, actualizar y comentar tareas de Notion
- Puedes consultar y crear eventos en Outlook
- Puedes crear tarjetas (issues) en Jira con título, prioridad, proyecto, fecha límite y etiquetas
- Puedes responder preguntas sobre la agenda del día, tareas pendientes o prioridades
- Puedes razonar sobre qué debería hacer el usuario a continuación

CONTEXTO QUE RECIBIRÁS:
Cada mensaje del usuario llegará con un bloque de contexto que incluye:
- Vista activa en la UI (priority | tasks | calendar | agent)
- Resumen del día: tareas pendientes, eventos de hoy, prioridades generadas
Este contexto está en el system message y debes usarlo para dar respuestas situadas.

COMPORTAMIENTO:
- Si el usuario dice "crea una tarea para revisar el PR mañana" → llama a create_task con los datos extraídos, confirma con una línea.
- Si el usuario dice "crea una tarjeta en Jira para el bug de login" → llama a crear_tarjeta_jira con los datos extraídos, confirma con una línea.
- Si el usuario dice "añade una cita médica el jueves a las 13:00" → llama a create_event, confirma con una línea.
- Si el usuario pregunta "¿qué debería hacer ahora?" → razona con el contexto del día y da una respuesta directa de máximo 3 puntos.
- Si el usuario pregunta algo que no está en tus datos → dilo claramente y ofrece consultar Notion u Outlook si aplica.
- Si la acción que el usuario pide podría tener consecuencias importantes (eliminar tareas o eventos) → SIEMPRE pide confirmación explícita antes de ejecutar. Nunca borres nada sin que el usuario confirme con un "sí", "confirma" o similar en el mismo hilo de conversación.
- Si el usuario pide borrar "todas las tareas" → primero llama a get_tasks para listarlas, muéstraselas al usuario y pide confirmación antes de borrar cada una.

FORMATO DE RESPUESTAS:
- Respuestas cortas por defecto: máximo 3-4 frases o una lista de máximo 5 puntos.
- Usa listas con guión cuando enumeres tareas o eventos.
- No uses markdown pesado (sin headers, sin negritas innecesarias).
- Cuando hayas ejecutado una acción (crear tarea, crear evento), confirma con una sola frase: "Hecho. [descripción breve de lo que se creó]."

RESTRICCIONES:
- No inventes datos de tareas o eventos. Si no tienes la información, consulta Notion u Outlook.
- No respondas sobre temas ajenos a la productividad, agenda o tareas del usuario.
- Nunca muestres IDs internos de Notion o Outlook al usuario.
- Si el usuario escribe en inglés, respóndele en inglés. En cualquier otro caso, responde en español."""

chat_agent = Agent(
    name="Chat Agent",
    instructions=CHAT_AGENT_INSTRUCTIONS,
    tools=[get_tasks, create_task, update_task, add_comment, delete_task, get_events, create_event, *MCP_TOOLS],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=openai_client),
    model_settings=ModelSettings(temperature=0.5),
)


async def run_chat_agent(
    message: str,
    context: dict | None = None,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Execute the Chat Agent with user message, optional context and conversation history.

    Args:
        message: The user's current message.
        context: Optional dict with UI context (active view, day summary, etc.).
        history: List of previous messages as dicts with 'role' and 'content' keys.
                 Roles: 'user' or 'assistant'.

    Returns:
        The agent's text response.
    """
    # Build input as a list of messages for the Runner
    input_messages: list[dict[str, Any]] = []

    # Add context as a system-level message if available
    if context:
        context_block = json.dumps(context, default=str, ensure_ascii=False)
        input_messages.append({
            "role": "user",
            "content": f"[CONTEXTO ACTUAL DEL USUARIO - no respondas a esto, solo úsalo como referencia]\n{context_block}",
        })
        input_messages.append({
            "role": "assistant",
            "content": "Entendido, tengo el contexto del usuario.",
        })

    # Add conversation history
    if history:
        for msg in history:
            role = msg.get("role", "user")
            # Map 'agent' role to 'assistant' for OpenAI compatibility
            if role == "agent":
                role = "assistant"
            input_messages.append({
                "role": role,
                "content": msg.get("content", ""),
            })

    # Add current user message
    input_messages.append({
        "role": "user",
        "content": message,
    })

    result = await Runner.run(chat_agent, input_messages)  # type: ignore[arg-type]
    return result.final_output