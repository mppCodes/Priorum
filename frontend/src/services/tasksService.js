import api from "./api.js";

/**
 * Obtiene tareas desde Notion vía backend.
 * @param {Object} params - { period: "day"|"week"|"month"|"year", date: "YYYY-MM-DD", priority, project }
 */
export const getTasks = (params = {}) => api.get("/tasks", { params });

/**
 * Crea una nueva tarea en Notion.
 * @param {Object} data - { title, project, priority, deadline, tags }
 */
export const createTask = (data) => api.post("/tasks", data);

/**
 * Actualiza una tarea existente.
 * @param {string} taskId
 * @param {Object} data
 */
export const updateTask = (taskId, data) => api.patch(`/tasks/${taskId}`, data);

/**
 * Elimina una tarea.
 * @param {string} taskId
 */
export const deleteTask = (taskId) => api.delete(`/tasks/${taskId}`);

/**
 * Añade un comentario a una tarea.
 * @param {string} taskId
 * @param {string} comment
 */
export const addComment = (taskId, comment) =>
  api.post(`/tasks/${taskId}/comments`, { comment });

/**
 * Sincroniza tareas con Notion (fuerza refresco).
 */
export const syncTasks = () => api.post("/tasks/sync");