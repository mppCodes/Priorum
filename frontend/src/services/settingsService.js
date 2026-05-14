import api from "./api.js";

/**
 * Obtiene la URL de autorización de Microsoft para iniciar el flujo OAuth.
 * @returns {Promise<string>} URL de autorización
 */
export async function getOutlookAuthUrl() {
  const data = await api.get("/auth/outlook/login");
  return data.auth_url;
}

/**
 * Obtiene el estado actual de la conexión con Outlook.
 * @returns {Promise<{ connected: boolean, user_email: string|null, user_name: string|null, expires_at: string|null }>}
 */
export async function getOutlookStatus() {
  return api.get("/auth/outlook/status");
}

/**
 * Desconecta la cuenta de Outlook (elimina el token en memoria del backend).
 * @returns {Promise<void>}
 */
export async function disconnectOutlook() {
  return api.delete("/auth/outlook/logout");
}