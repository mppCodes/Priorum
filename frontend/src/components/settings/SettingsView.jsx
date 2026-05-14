import { useState, useEffect, useCallback } from "react";
import { Mail, CheckCircle, XCircle, LogOut, RefreshCw, ExternalLink } from "lucide-react";
import { COLORS } from "../../constants/colors.js";
import {
  getOutlookAuthUrl,
  getOutlookStatus,
  disconnectOutlook,
} from "../../services/settingsService.js";

// ── Estilos inline ────────────────────────────────────────────────────────────
const s = {
  container: {
    padding: "32px 40px",
    maxWidth: 640,
  },
  title: {
    fontSize: 20,
    fontWeight: 600,
    color: COLORS.textPrimary,
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginBottom: 32,
  },
  card: {
    background: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 12,
    padding: "24px",
    marginBottom: 16,
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: 600,
    color: COLORS.textPrimary,
  },
  cardDesc: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: 2,
  },
  statusRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 14px",
    borderRadius: 8,
    marginBottom: 16,
    fontSize: 13,
  },
  statusConnected: {
    background: `${COLORS.green}15`,
    border: `1px solid ${COLORS.green}40`,
    color: COLORS.green,
  },
  statusDisconnected: {
    background: `${COLORS.red}15`,
    border: `1px solid ${COLORS.red}40`,
    color: COLORS.red,
  },
  statusLoading: {
    background: `${COLORS.textMuted}15`,
    border: `1px solid ${COLORS.border}`,
    color: COLORS.textSecondary,
  },
  userInfo: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginBottom: 16,
    paddingLeft: 2,
  },
  btnPrimary: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 18px",
    background: COLORS.accent,
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    transition: "background 0.15s",
  },
  btnDanger: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 18px",
    background: "transparent",
    color: COLORS.red,
    border: `1px solid ${COLORS.red}60`,
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    transition: "background 0.15s",
  },
  btnRow: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  notice: {
    fontSize: 11,
    color: COLORS.textMuted,
    marginTop: 14,
    lineHeight: 1.6,
  },
  divider: {
    height: 1,
    background: COLORS.border,
    margin: "16px 0",
  },
  expiresLabel: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
};

// ── Componente principal ──────────────────────────────────────────────────────
export default function SettingsView() {
  const [status, setStatus] = useState(null);   // null = cargando
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Leer estado de la URL (tras el callback OAuth)
  const urlParams = new URLSearchParams(window.location.search);
  const oauthResult = urlParams.get("outlook");

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getOutlookStatus();
      setStatus(data);
    } catch (err) {
      setStatus({ connected: false, user_email: null, user_name: null });
    }
  }, []);

  useEffect(() => {
    fetchStatus();

    // Limpiar el query param de la URL sin recargar la página
    if (oauthResult) {
      const url = new URL(window.location.href);
      url.searchParams.delete("outlook");
      url.searchParams.delete("reason");
      window.history.replaceState({}, "", url.toString());
    }
  }, [fetchStatus, oauthResult]);

  const handleConnect = async () => {
    setLoading(true);
    setError(null);
    try {
      const authUrl = await getOutlookAuthUrl();
      // Redirigir en la misma pestaña para que el callback vuelva aquí
      window.location.href = authUrl;
    } catch (err) {
      setError(err.message || "No se pudo obtener la URL de autorización.");
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    setError(null);
    try {
      await disconnectOutlook();
      setStatus({ connected: false, user_email: null, user_name: null });
    } catch (err) {
      setError(err.message || "Error al desconectar.");
    } finally {
      setLoading(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────
  const isConnected = status?.connected === true;
  const isLoading = status === null;

  return (
    <div style={s.container}>
      <div style={s.title}>Configuración</div>
      <div style={s.subtitle}>
        Gestiona las conexiones con servicios externos.
      </div>

      {/* Notificación tras callback OAuth */}
      {oauthResult === "connected" && (
        <div
          style={{
            ...s.statusRow,
            ...s.statusConnected,
            marginBottom: 24,
          }}
        >
          <CheckCircle size={14} />
          Cuenta de Outlook conectada correctamente.
        </div>
      )}
      {oauthResult === "error" && (
        <div
          style={{
            ...s.statusRow,
            ...s.statusDisconnected,
            marginBottom: 24,
          }}
        >
          <XCircle size={14} />
          Error al conectar con Outlook. Inténtalo de nuevo.
        </div>
      )}

      {/* ── Tarjeta Outlook ── */}
      <div style={s.card}>
        <div style={s.cardHeader}>
          <Mail size={18} color={COLORS.blue} />
          <div>
            <div style={s.cardTitle}>Microsoft Outlook</div>
            <div style={s.cardDesc}>
              Accede a tu calendario para ver y gestionar eventos.
            </div>
          </div>
        </div>

        {/* Estado de conexión */}
        {isLoading ? (
          <div style={{ ...s.statusRow, ...s.statusLoading }}>
            <RefreshCw size={13} style={{ animation: "spin 1s linear infinite" }} />
            Comprobando estado…
          </div>
        ) : isConnected ? (
          <div style={{ ...s.statusRow, ...s.statusConnected }}>
            <CheckCircle size={14} />
            Conectado
          </div>
        ) : (
          <div style={{ ...s.statusRow, ...s.statusDisconnected }}>
            <XCircle size={14} />
            No conectado
          </div>
        )}

        {/* Info del usuario conectado */}
        {isConnected && status?.user_name && (
          <div style={s.userInfo}>
            <strong style={{ color: COLORS.textPrimary }}>{status.user_name}</strong>
            {status.user_email && status.user_email !== status.user_name && (
              <span> · {status.user_email}</span>
            )}
            {status.expires_at && (
              <div style={s.expiresLabel}>
                Token válido hasta:{" "}
                {new Date(status.expires_at).toLocaleString("es-ES", {
                  dateStyle: "short",
                  timeStyle: "short",
                })}
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div
            style={{
              fontSize: 12,
              color: COLORS.red,
              marginBottom: 12,
              padding: "8px 12px",
              background: `${COLORS.red}10`,
              borderRadius: 6,
              border: `1px solid ${COLORS.red}30`,
            }}
          >
            {error}
          </div>
        )}

        <div style={s.divider} />

        {/* Botones de acción */}
        <div style={s.btnRow}>
          {!isConnected ? (
            <button
              style={s.btnPrimary}
              onClick={handleConnect}
              disabled={loading || isLoading}
            >
              <ExternalLink size={13} />
              {loading ? "Redirigiendo…" : "Conectar con Microsoft"}
            </button>
          ) : (
            <>
              <button
                style={s.btnPrimary}
                onClick={fetchStatus}
                disabled={loading}
              >
                <RefreshCw size={13} />
                Actualizar estado
              </button>
              <button
                style={s.btnDanger}
                onClick={handleDisconnect}
                disabled={loading}
              >
                <LogOut size={13} />
                {loading ? "Desconectando…" : "Desconectar"}
              </button>
            </>
          )}
        </div>

        <div style={s.notice}>
          Al conectar, serás redirigido a la página de inicio de sesión de Microsoft.
          El acceso se limita a la lectura y escritura de tu calendario.
          El token se almacena en memoria y se pierde al reiniciar el servidor.
        </div>
      </div>
    </div>
  );
}