import api from "./api.js";

/**
 * Obtiene eventos del calendario desde Outlook/Teams vía backend.
 * @param {Object} params - { period: "day"|"week"|"month"|"year", date: "YYYY-MM-DD" }
 */
export const getEvents = (params = {}) => api.get("/calendar", { params });

/**
 * Crea un nuevo evento en Outlook.
 * @param {Object} data - { title, date, time, duration, type, notes, attendees }
 */
export const createEvent = (data) => api.post("/calendar", data);

/**
 * Actualiza un evento existente.
 * @param {string} eventId
 * @param {Object} data
 */
export const updateEvent = (eventId, data) =>
  api.patch(`/calendar/${eventId}`, data);

/**
 * Elimina un evento.
 * @param {string} eventId
 */
export const deleteEvent = (eventId) => api.delete(`/calendar/${eventId}`);

/**
 * Sincroniza el calendario con Outlook (fuerza refresco).
 */
export const syncCalendar = () => api.post("/calendar/sync");