import api from "./api.js";

/**
 * Solicita al agente IA que genere las prioridades del día.
 * @param {Object} context - { tasks, events, date }
 */
export const getDailyPriorities = (context) =>
  api.post("/agent/priorities", context);

/**
 * Envía un mensaje al agente y obtiene respuesta.
 * @param {string} message - Pregunta o instrucción del usuario
 * @param {Object} context - Contexto actual (tareas, eventos)
 */
export const chat = (message, context = {}) =>
  api.post("/agent/chat", { message, context });

/**
 * Solicita al agente que sugiera una distribución del horario.
 * @param {Object} context - { tasks, events, date, freeSlots }
 */
export const getScheduleSuggestion = (context) =>
  api.post("/agent/schedule", context);

/**
 * Obtiene el historial de conversación con el agente.
 */
export const getChatHistory = () => api.get("/agent/history");

/**
 * Limpia el historial de conversación.
 */
export const clearChatHistory = () => api.delete("/agent/history");