import api from "./api.js";

/**
 * Obtiene eventos del calendario desde Outlook/Teams vía backend.
 * @param {Object} params - { period: "day"|"week"|"month"|"year", date: "YYYY-MM-DD" }
 */
export const getEvents = (params = {}) => api.get("/calendar", { params });

/**
 * Crea un nuevo evento en Outlook.
 * Transforms form fields (date, time, duration) into start/end ISO datetimes.
 * @param {Object} data - { title, date, time, duration, type, notes, attendees }
 */
export const createEvent = (data) => {
  // Transform form data to match EventCreate schema (start/end datetimes)
  if (data.date && data.time && !data.start) {
    const startDt = new Date(`${data.date}T${data.time}:00`);
    const endDt = new Date(startDt.getTime() + (data.duration || 30) * 60000);
    const payload = {
      title: data.title,
      start: startDt.toISOString(),
      end: endDt.toISOString(),
      description: data.notes || "",
      type: data.type || null,
      attendees: data.attendees || [],
    };
    return api.post("/calendar", payload);
  }
  return api.post("/calendar", data);
};

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